"""Defines URL patterns for learning_logs"""

from django.urls import path

from . import views

app_name = 'learning_logs'
urlpatterns = [
    # Home page
    path('', views.index, name='index'),
    # Page that shows all topics
    path('topics/', views.topics, name='topics'),
    # Detail page for a single topic
    path('topics/<int:topic_id>/', views.topic, name='topic'),
    # Page for adding a new topic
    path('new_topic/', views.new_topic, name='new_topic'),
    # Page for adding a new entry
    path('new_entry/<int:topic_id>/', views.new_entry, name='new_entry'),
    # Page for editing an entry
    path('edit_entry/<int:entry_id>/', views.edit_entry, name='edit_entry'),
    # Page to delete topic
    path('delete_topic/<int:topic_id>/', views.delete_topic, name='delete_topic'),
    # Edit an existing topic
    path('edit_topic/<int:topic_id>/', views.edit_topic, name='edit_topic'),
    # Reorder topics
    path('reorder_topics/', views.reorder_topics, name='reorder_topics'),
    path('books/<int:book_id>/', views.book_viewer, name='book_viewer'),
    path('books/<int:book_id>/save_progress/', views.save_progress, name='save_progress'),
    # Anthropic
    path('chatbot/', views.chatbot, name='chatbot'),
    path('chatbot/message/', views.chat_message, name='chat_message'),
    # clear chat history
    path('chatbot/clear/', views.clear_chat, name='clear_chat'),
]
