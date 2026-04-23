import os
from django.core.management.base import BaseCommand
from learning_logs.models import Book

class Command(BaseCommand):
    help = 'Load books from the pdfs static folder into the database'

    def handle(self, *args, **options):
        pdf_dir = os.path.join('learning_logs', 'static', 'learning_logs', 'pdfs')

        loaded = 0
        for filename in os.listdir(pdf_dir):
            if filename.endswith('.pdf'):
                _, created = Book.objects.get_or_create(
                    pdf_filename=filename,
                    defaults={
                        'title': filename.replace('_', ' ').replace('.pdf', '').title(),
                        'author': 'Unknown',
                    }
                )
                if created:
                    self.stdout.write(f"Added: {filename}")
                    loaded += 1
                else:
                    self.stdout.write(f"Skipped (already exists): {filename}")

        self.stdout.write(self.style.SUCCESS(f'\nDone! {loaded} books added.'))