from django.core.management.base import BaseCommand
from classifier.models import Question, ClusteredQuestion

from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from tqdm import tqdm  # optional, for nice progress bars

import numpy as np

class Command(BaseCommand):
    help = 'Embed and cluster questions within each paper using SBERT + KMeans. Logs metrics.'

    def handle(self, *args, **kwargs):
        print("📌 Loading SBERT model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')

        papers = Question.objects.values_list('paper', flat=True).distinct()
        total_papers = len(papers)
        print(f"📚 Found {total_papers} distinct papers.\n")

        for idx, paper in enumerate(papers, 1):
            print(f"\n📄 ({idx}/{total_papers}) Processing Paper: {paper}")
            questions = Question.objects.filter(paper=paper)
            texts = [q.text for q in questions]

            if not texts:
                print(f"❌ No questions found for paper {paper}. Skipping...\n")
                continue

            print(f"🧠 Encoding {len(texts)} questions...")
            embeddings = model.encode(texts)

            print("🌀 Clustering into 3 groups...")
            kmeans = KMeans(n_clusters=3, random_state=42)
            labels = kmeans.fit_predict(embeddings)

            # Metrics
            inertia = kmeans.inertia_
            cluster_centers = kmeans.cluster_centers_
            print(f"📉 Inertia: {inertia:.2f}")
            print("📊 Cluster sizes:")
            for i in range(3):
                count = np.sum(labels == i)
                print(f"  🔹 Cluster {i}: {count} questions")

            print("💾 Saving clustered questions...")
            ClusteredQuestion.objects.filter(paper=paper).delete()  # optional: clear old ones
            for i, q in enumerate(tqdm(questions, desc="   ⬇️ Saving")):
                ClusteredQuestion.objects.create(
                    paper=q.paper,
                    text=q.text,
                    module=q.module,
                    cluster_label=labels[i]
                )

        print("\n✅ All clustering done and saved! 🎉")
