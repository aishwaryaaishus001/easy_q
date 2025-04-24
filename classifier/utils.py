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
import os
import joblib

# Load SBERT model once globally
sbert_model = SentenceTransformer('all-MiniLM-L6-v2')

# Difficulty mapping based on cluster labels
CLUSTER_DIFFICULTY = {
    0: 'easy',
    1: 'medium',
    2: 'hard'
}

import nltk
import string
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

# Load these once
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')

stop_words = set(stopwords.words("english"))
lemmatizer = WordNetLemmatizer()

def preprocess_text(text):
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    tokens = nltk.word_tokenize(text)
    cleaned_tokens = [lemmatizer.lemmatize(word) for word in tokens if word not in stop_words]
    return " ".join(cleaned_tokens)


'''def predict_difficulty(text, paper, module):
    try:
        # 🔁 Preprocess before encoding
        cleaned_text = preprocess_text(text)
        new_embedding = sbert_model.encode([cleaned_text])[0]

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
                'embedding': new_embedding.tolist()
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
        }'''

DIFFICULTY_LABELS = ['easy', 'medium', 'hard']
MODEL_PATH = os.path.join('classifier', 'trained_models', 'best_difficulty_classifier.pkl')
# Load trained classifier model once
classifier = joblib.load(MODEL_PATH)

def predict_difficulty(text, paper, module):
    try:
        # Preprocess and encode
        cleaned_text = preprocess_text(text)
        embedding = sbert_model.encode([cleaned_text])[0]

        # Reshape since sklearn expects 2D input
        prediction = classifier.predict([embedding])[0]
        probability = classifier.predict_proba([embedding])[0]

        existing_qs = ClusteredQuestion.objects.filter(paper=paper, module=module).exclude(embedding__isnull=True)

        if existing_qs.count() >= 3:
            existing_embeddings = np.array([
                np.array(ast.literal_eval(q.embedding)) if isinstance(q.embedding, str) else np.array(q.embedding)
                for q in existing_qs
            ])

            kmeans = KMeans(n_clusters=3, random_state=42)
            kmeans.fit(existing_embeddings)

            cluster_label = int(kmeans.predict([embedding])[0])

        return {
            'difficulty': DIFFICULTY_LABELS[prediction],
            'confidence': round(np.max(probability), 3),
            'embedding': embedding.tolist(),
            'cluster_label': cluster_label
        }

    except Exception as e:
        print(f"[ERROR in predict_difficulty]: {str(e)}")
        return {
            'difficulty': 'unknown',
            'confidence': 0.0,
            'embedding': []
        }
