from django.db import models

# Create your models here.
class Question(models.Model):
    paper = models.CharField(max_length=100)
    text = models.TextField()
    module = models.IntegerField()

    class Meta:
        indexes = [
            models.Index(fields=['paper']),   # Index for the paper field
            models.Index(fields=['module']),  # Index for the module field
            models.Index(fields=['text']),    # Index for the text field
        ]
        unique_together = ('paper', 'text')  # Ensures no duplicate questions for the same paper


    def __str__(self):
        return f"Paper: {self.paper}, Q: {self.text}... | Module: {self.module}"
