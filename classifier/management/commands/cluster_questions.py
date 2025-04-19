from django.core.management.base import BaseCommand
from classifier.models import Question, ClusteredQuestion

from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from tqdm import tqdm  # optional, for nice progress bars
import numpy as np

class Command(BaseCommand):
    help = 'Embed and cluster questions within each paper and module using SBERT + KMeans. Logs metrics.'

    def handle(self, *args, **kwargs):
        print("📌 Loading SBERT model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')

        papers = Question.objects.values_list('paper', flat=True).distinct()
        total_papers = len(papers)
        print(f"📚 Found {total_papers} distinct papers.\n")

        for idx, paper in enumerate(papers, 1):
            print(f"\n📄 ({idx}/{total_papers}) Processing Paper: {paper}")
            modules = Question.objects.filter(paper=paper).values_list('module', flat=True).distinct()

            for module in modules:
                print(f"\n   📑 Module: {module}")

                # Get questions for the current paper and module
                questions = Question.objects.filter(paper=paper, module=module)
                texts = [q.text for q in questions]

                if not texts:
                    print(f"❌ No questions found for paper {paper}, module {module}. Skipping...\n")
                    continue

                print(f"🧠 Encoding {len(texts)} questions...")
                embeddings = model.encode(texts)

                print("🌀 Clustering into 3 groups...")
                kmeans = KMeans(n_clusters=3, random_state=42)
                labels = kmeans.fit_predict(embeddings)

                # Metrics
                inertia = kmeans.inertia_
                print(f"📉 Inertia: {inertia:.2f}")
                print("📊 Cluster sizes:")
                for i in range(3):
                    count = np.sum(labels == i)
                    print(f"  🔹 Cluster {i}: {count} questions")

                print("💾 Saving clustered questions...")
                ClusteredQuestion.objects.filter(paper=paper, module=module).delete()  # optional: clear old ones
                for i, q in enumerate(tqdm(questions, desc=f"   ⬇️ Saving Module {module}")):
                    ClusteredQuestion.objects.create(
                        paper=q.paper,
                        text=q.text,
                        module=q.module,
                        cluster_label=labels[i],  # Cluster label for module-specific clustering
                        embedding=embeddings[i].tolist()  # Convert numpy array to list before saving
                    )
        clustered_questions = ClusteredQuestion.objects.exclude(embedding__isnull=True)
        print(f"Number of questions with embeddings saved: {clustered_questions.count()}")

        print("\n✅ All clustering done and saved! 🎉")
