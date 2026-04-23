from django.db import models
from django.contrib.auth.models import User


class Topic(models.Model):
    """A topic the user is learning about"""
    text = models.CharField(max_length=200)
    date_added = models.DateTimeField(auto_now_add=True)
    order = models.IntegerField(default=0)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        ordering = ['order', 'date_added']

    def __str__(self):
        """Return a string representation of the topic"""
        return self.text


class Entry(models.Model):
    """Specific entry within a topic"""
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    text = models.TextField()
    date_added = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = 'entries'

    def __str__(self):
        """Return a string representation of the model"""
        return f"{self.text[:50]}..."


class Book(models.Model):
    """PDF book in library"""
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    genre = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    pdf_filename = models.CharField(max_length=255)
    img_filename = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        return self.title
    
    def get_pdf_url(self):
        return f"learning_logs/pdfs/{self.pdf_filename}"
    
    def get_img_url(self):
        return f"learning_logs/img/{self.img_filename}"