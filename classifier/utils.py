'''import os
import joblib
from sentence_transformers import SentenceTransformer

DIFFICULTY_LABELS = ['easy', 'medium', 'hard']

MODEL_PATH = os.path.join('classifier', 'trained_models', 'best_difficulty_classifier.pkl')
classifier = joblib.load(MODEL_PATH)
sbert_model = SentenceTransformer('all-MiniLM-L6-v2')'''

from sklearn.cluster import KMeans
import numpy as np
from sentence_transformers import SentenceTransformer
from classifier.models import ClusteredQuestion
import ast

# Load SBERT model once globally
sbert_model = SentenceTransformer('all-MiniLM-L6-v2')

# Difficulty mapping based on cluster labels
CLUSTER_DIFFICULTY = {
    0: 'easy',
    1: 'medium',
    2: 'hard'
}

def predict_difficulty(text, paper, module):
    try:
        new_embedding = sbert_model.encode([text])[0]
        existing_qs = ClusteredQuestion.objects.filter(paper=paper, module=module).exclude(embedding__isnull=True)

        if existing_qs.count() >= 3:
            existing_embeddings = np.array([
                np.array(ast.literal_eval(q.embedding)) if isinstance(q.embedding, str) else np.array(q.embedding)
                for q in existing_qs
            ])

            kmeans = KMeans(n_clusters=3, random_state=42)
            kmeans.fit(existing_embeddings)

            cluster_label = int(kmeans.predict([new_embedding])[0])
            difficulty = CLUSTER_DIFFICULTY.get(cluster_label, 'unknown')

            return {
                'difficulty': difficulty,
                'cluster_label': cluster_label,
                'embedding': new_embedding.tolist()  # Convert to list for JSON safety
            }

        else:
            return {
                'difficulty': 'unknown',
                'cluster_label': None,
                'embedding': new_embedding.tolist()
            }

    except Exception as e:
        print(f"[ERROR in predict_difficulty]: {str(e)}")
        return {
            'difficulty': 'unknown',
            'cluster_label': None,
            'embedding': []
        }
