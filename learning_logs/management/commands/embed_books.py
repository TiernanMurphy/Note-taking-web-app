from django.core.management.base import BaseCommand
from learning_logs.models import Book, DocumentChunk
from sentence_transformers import SentenceTransformer
import pypdf
import os

class Command(BaseCommand):
    help = 'Extract text from PDFs and generate embeddings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--titles',
            nargs='+',
            type=str,
            help='Partial book titles to embed (e.g. --titles "atomic" "deep work")'
        )

    def handle(self, *args, **options):
        model = SentenceTransformer('all-MiniLM-L6-v2')
        pdf_dir = os.path.join('learning_logs', 'static', 'learning_logs', 'pdfs')

        titles = options.get('titles')
        if titles:
            books = []
            for title in titles:
                matches = Book.objects.filter(title__icontains=title)
                books.extend(matches)
        else:
            books = Book.objects.all()

        for book in books:
            pdf_path = os.path.join(pdf_dir, book.pdf_filename)

            if not os.path.exists(pdf_path):
                self.stdout.write(f"Skipping {book.title} - file not found")
                continue

            if DocumentChunk.objects.filter(book=book).exists():
                self.stdout.write(f"Skipping {book.title} - already embedded")
                continue

            self.stdout.write(f"Processing {book.title}...")

            try:
                reader = pypdf.PdfReader(pdf_path)
                all_chunks = []
                chunk_metas = []

                for page_num, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if not text or len(text.strip()) < 50:
                        continue

                    # Overlapping chunks
                    chunk_size = 2000
                    overlap = 200
                    start = 0
                    while start < len(text):
                        all_chunks.append(text[start:start + chunk_size])
                        chunk_metas.append(page_num + 1)
                        start += chunk_size - overlap

                # Batch encode all chunks at once
                self.stdout.write(f"  Encoding {len(all_chunks)} chunks...")
                embeddings = model.encode(all_chunks, batch_size=32, show_progress_bar=True)

                # Bulk create
                DocumentChunk.objects.bulk_create([
                    DocumentChunk(
                        book=book,
                        text=all_chunks[i],
                        embedding=embeddings[i].tolist(),
                        page_number=chunk_metas[i]
                    )
                    for i in range(len(all_chunks))
                ])

                self.stdout.write(self.style.SUCCESS(f"Done: {book.title}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error on {book.title}: {e}"))

        self.stdout.write(self.style.SUCCESS('\nAll done!'))