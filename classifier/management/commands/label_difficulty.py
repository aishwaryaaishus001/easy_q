from django.core.management.base import BaseCommand
from classifier.models import ClusteredQuestion

# Define mapping from cluster_label to difficulty
CLUSTER_TO_DIFFICULTY = {
    0: 'easy',
    1: 'medium',
    2: 'hard',
}

class Command(BaseCommand):
    help = "Label difficulty based on cluster label"

    def handle(self, *args, **kwargs):
        updated_count = 0
        questions = ClusteredQuestion.objects.all()

        for question in questions:
            cluster = question.cluster_label
            difficulty = CLUSTER_TO_DIFFICULTY.get(cluster)

            if difficulty:
                question.difficulty = difficulty
                question.save()
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Labeled {updated_count} questions with difficulty."))
