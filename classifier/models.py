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
    
class ClusteredQuestion(models.Model):
    paper = models.CharField(max_length=100)
    text = models.TextField()
    module = models.IntegerField()
    cluster_label = models.IntegerField()
    difficulty = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return self.text
    
