from django.core.management.base import BaseCommand
from classifier.models import Question, ClusteredQuestion

from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from tqdm import tqdm
import numpy as np
import string
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

# Download NLTK resources if not already present
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')

stop_words = set(stopwords.words("english"))
lemmatizer = WordNetLemmatizer()

# Preprocessing function
def preprocess_text(text):
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    tokens = nltk.word_tokenize(text)
    cleaned_tokens = [lemmatizer.lemmatize(word) for word in tokens if word not in stop_words]
    return " ".join(cleaned_tokens)

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

                questions = Question.objects.filter(paper=paper, module=module)
                raw_texts = [q.text for q in questions]

                if not raw_texts:
                    print(f"❌ No questions found for paper {paper}, module {module}. Skipping...\n")
                    continue

                print(f"🧹 Preprocessing {len(raw_texts)} questions...")
                processed_texts = [preprocess_text(text) for text in raw_texts]

                print(f"🧠 Encoding preprocessed texts...")
                embeddings = model.encode(processed_texts)

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
                ClusteredQuestion.objects.filter(paper=paper, module=module).delete()
                for i, q in enumerate(tqdm(questions, desc=f"   ⬇️ Saving Module {module}")):
                    ClusteredQuestion.objects.create(
                        paper=q.paper,
                        text=q.text,
                        module=q.module,
                        cluster_label=labels[i],
                        embedding=embeddings[i].tolist()
                    )

        clustered_questions = ClusteredQuestion.objects.exclude(embedding__isnull=True)
        print(f"Number of questions with embeddings saved: {clustered_questions.count()}")
        print("\n✅ All clustering done and saved! 🎉")
