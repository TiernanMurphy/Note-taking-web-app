from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from .models import Topic, Entry, Book, ReadingProgress, ChatMessage
from .forms import TopicForm, EntryForm
from django.db.models import Max, Q
import anthropic
import os
from sentence_transformers import SentenceTransformer
from pgvector.django import L2Distance
from .models import DocumentChunk


embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def index(request):
    """The home page for Learning Log."""
    genre_order = [
        'Python Programming',
        'C and Linux',
        'Business & Entrepreneurship',
        'Investing & Personal Finance',
        'Productivity & Self Development',
        'Textbooks',
    ]

    grouped_books = []
    for genre in genre_order:
        genre_books = Book.objects.filter(genre=genre)
        if genre_books.exists():
            grouped_books.append({'genre': genre, 'books': genre_books})

    context = {'grouped_books': grouped_books}
    return render(request, 'learning_logs/index.html', context)


@login_required
def topics(request):
    """Show all topics"""
    topics = Topic.objects.filter(owner=request.user).order_by('order')
    context = {'topics': topics}
    return render(request, 'learning_logs/topics.html', context)


@login_required
def delete_topic(request, topic_id):
    """Delete a topic with confirmation"""
    topic = get_object_or_404(Topic, id=topic_id)

    # Ensure topic belongs to current user
    if topic.owner != request.user:
        raise Http404

    if request.method == 'POST':
        topic_text = topic.text
        topic.delete()
        messages.success(request, f"deleted {topic_text}")
        return redirect('learning_logs:topics')

    # GET request shows confirmation page
    context = {'topic': topic}
    return render(request, 'learning_logs/delete_topic.html', context)


@login_required
def edit_topic(request, topic_id):
    """Edit an existing topic"""
    topic = get_object_or_404(Topic, id=topic_id)

    if request.method != 'POST':
        # Initial request; pre-fill form with the current template
        form = TopicForm(instance=topic)
    else:
        # POST data submitted; process data
        form = TopicForm(instance=topic, data=request.POST)
        if form.is_valid():
            form.save()
            return redirect('learning_logs:topics')

    # Display a blank or invalid form
    context = {'topic': topic, 'form': form}
    return render(request, 'learning_logs/edit_topic.html', context)


@login_required
def topic(request, topic_id):
    """Show a single topic and all its entries"""
    topic = Topic.objects.get(id=topic_id)
    # Make sure the topic belongs to the current user
    if topic.owner != request.user:
        raise Http404

    entries = topic.entry_set.order_by('-date_added')
    context = {'topic': topic, 'entries': entries}
    return render(request, 'learning_logs/topic.html', context)


@login_required
def new_topic(request):
    """Add a new topic"""
    if request.method != 'POST':
        # No data submitted; create a blank form
        form = TopicForm()
    else:
        # POST data submitted; process data
        form = TopicForm(data=request.POST)
        if form.is_valid():
            new_topic = form.save(commit=False)
            new_topic.owner = request.user
            last_order = Topic.objects.filter(owner=request.user).aggregate(Max('order'))['order__max']
            new_topic.order = (last_order or 0) + 1
            new_topic.save()
            return redirect('learning_logs:topics')

    # Display a blank or invalid form
    context = {'form': form}
    return render(request, 'learning_logs/new_topic.html', context)


@login_required
def new_entry(request, topic_id):
    """Add a new entry for a particular topic"""
    topic = Topic.objects.get(id=topic_id)

    if request.method != 'POST':
        # No data submitted; create a blank form
        form = EntryForm()
    else:
        # POST data submitted; process data
        form = EntryForm(data=request.POST)
        if form.is_valid():
            new_entry = form.save(commit=False)
            new_entry.topic = topic
            new_entry.owner = request.user
            new_entry.save()
            return redirect('learning_logs:topic', topic_id=topic_id)

    # Display a blank or invalid form
    context = {'topic': topic, 'form': form}
    return render(request, 'learning_logs/new_entry.html', context)


@login_required
def edit_entry(request, entry_id):
    """Edit an existing entry"""
    entry = Entry.objects.get(id=entry_id)
    topic = entry.topic
    if topic.owner != request.user:
        raise Http404

    if request.method != 'POST':
        # Initial request; pre-fill form with the current entry
        form = EntryForm(instance=entry)
    else:
        # POST data submitted; process data
        form = EntryForm(instance=entry, data=request.POST)
        if form.is_valid():
            form.save()
            return redirect('learning_logs:topic', topic_id=topic.id)

    context = {'entry': entry, 'topic': topic, 'form': form}
    return render(request, 'learning_logs/edit_entry.html', context)


@csrf_exempt
@require_POST
@login_required
def reorder_topics(request):
    """Handle drag and drop reordering of topics"""
    try:
        data = json.loads(request.body)
        topic_ids = data.get('topic_ids', [])

        # Update order field for each topic
        for index, topic_id in enumerate(topic_ids):
            Topic.objects.filter(id=topic_id).update(order=index)

        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
    

def book_viewer(request, book_id):
    try:
        book = get_object_or_404(Book, id=book_id)
        current_page = 1
        if request.user.is_authenticated:
            progress = ReadingProgress.objects.filter(
                user=request.user, book=book
            ).first()
            if progress:
                current_page = progress.current_page
        context = {'book': book, 'current_page': current_page}
        return render(request, 'learning_logs/book_viewer.html', context)
    except Exception as e:
        from django.http import HttpResponse
        return HttpResponse(f"Error: {str(e)}", status=500)


@login_required
@require_POST
def save_progress(request, book_id):
    """Save reading progress for a book."""
    book = get_object_or_404(Book, id=book_id)
    data = json.loads(request.body)
    page = data.get('page', 1)

    ReadingProgress.objects.update_or_create(
        user=request.user,
        book=book,
        defaults={'current_page': page}
    )
    return JsonResponse({'status': 'success'})


def chatbot(request):
    """Chatbot page."""
    return render(request, 'learning_logs/chatbot.html')


@login_required
@require_POST
def chat_message(request):
    data = json.loads(request.body)
    user_message = data.get('message', '').strip()
    history = data.get('history', [])
    image_base64 = data.get('image')
    image_type = data.get('image_type', 'image/jpeg')
    print(f"Image received: {bool(image_base64)}, type: {image_type}")

    if not user_message and not image_base64:
        return JsonResponse({'error': 'No message provided'}, status=400)

    question_embedding = embedding_model.encode(user_message or "describe this image").tolist()

    chunks = DocumentChunk.objects.order_by(
        L2Distance('embedding', question_embedding)
    )[:15]

    context = "\n\n".join([
        f"From '{chunk.book.title}' (page {chunk.page_number}):\n{chunk.text}"
        for chunk in chunks
    ])

    system_prompt = f"""You are a knowledgeable and conversational assistant for a digital library. 
You have access to text extracted from the full contents of books in this library.
For each question, you are given the most relevant passages retrieved from those books.
Answer naturally and conversationally, as if you've read these books yourself.
Be direct and confident. If a question isn't covered by the passages, say so honestly.
When relevant, mention which book your answer comes from.

Relevant passages:
{context}"""

    # Build current user message content
    # Build messages with history
    messages = []
    # Include last 6 exchanges for context without getting too long
    for msg in history[:-1][-6:]:
        messages.append({'role': msg['role'], 'content': msg['content']})
    
    # build current message
    if image_base64:
        current_content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image_type,
                    "data": image_base64
                }
            },
            {
                "type": "text",
                "text": user_message or "Please describe and explain this image."
            }
        ]
    else:
        current_content = user_message

    # Add current question
    messages.append({'role': 'user', 'content': current_content})

    client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        system=system_prompt,
        messages=messages
    )

    answer = response.content[0].text
    
    # save to database
    ChatMessage.objects.create(user=request.user, role='user', content=user_message)
    ChatMessage.objects.create(user=request.user, role='assistant', content=answer)
    
    return JsonResponse({'answer': answer})

@login_required
def clear_chat(request):
    ChatMessage.objects.filter(user=request.user).delete()
    return redirect('learning_logs:chatbot')


def chatbot(request):
    """Chatbot page."""
    chat_history = []
    if request.user.is_authenticated:
        chat_history = ChatMessage.objects.filter(user=request.user).values('role', 'content')
    context = {'chat_history': list(chat_history)}
    return render(request, 'learning_logs/chatbot.html', context)