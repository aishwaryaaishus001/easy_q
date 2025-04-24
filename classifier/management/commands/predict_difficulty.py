import joblib
from django.core.management.base import BaseCommand
from sentence_transformers import SentenceTransformer
import numpy as np

DIFFICULTY_LABELS = ['easy', 'medium', 'hard']
from django.core.management.base import BaseCommand
from classifier.utils import predict_difficulty

class Command(BaseCommand):
    help = 'Predict the difficulty of a new question using the trained model.'

    def handle(self, *args, **options):
        question = input("❓ Enter a question to predict its difficulty: ").strip()

        if not question:
            print("⚠️ No input provided. Exiting...")
            return

        difficulty = predict_difficulty(question)

        print(f"\n🎯 Predicted Difficulty: **{difficulty.upper()}**")

    def handle(self, *args, **options):
        # Load trained model
        print("📦 Loading the trained model...")
        model = joblib.load('classifier/trained_models/best_difficulty_classifier.pkl')

        # Load SBERT model
        print("📌 Loading SBERT for embedding...")
        sbert_model = SentenceTransformer('all-MiniLM-L6-v2')

        # Take user input
        question = input("❓ Enter a question to predict its difficulty: ").strip()

        if not question:
            print("⚠️ No input provided. Exiting...")
            return

        # Generate embedding
        print("🔍 Generating embedding for the question...")
        embedding = sbert_model.encode([question])

        # Predict difficulty
        print("🤖 Predicting difficulty...")
        prediction = model.predict(embedding)[0]
        difficulty = DIFFICULTY_LABELS[prediction]

        print(f"\n🎯 Predicted Difficulty: **{difficulty.upper()}**")
