import joblib
from django.core.management.base import BaseCommand
from classifier.models import ClusteredQuestion

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
import xgboost as xgb

from sentence_transformers import SentenceTransformer

import numpy as np

DIFFICULTY_MAP = {'easy': 0, 'medium': 1, 'hard': 2}

class Command(BaseCommand):
    help = 'Train multiple ML models to predict difficulty using SBERT embeddings and compare their performance.'

    def handle(self, *args, **options):
        print("📌 Loading SBERT model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')

        print("📥 Fetching questions with difficulty labels...")
        qs = ClusteredQuestion.objects.exclude(difficulty__isnull=True)

        texts = [q.text for q in qs]
        y = [DIFFICULTY_MAP[q.difficulty.lower()] for q in qs]

        print(f"🧠 Embedding {len(texts)} questions...")
        X = model.encode(texts)

        print("🔀 Splitting data for training/testing...")
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Initialize classifiers
        classifiers = {
            'Logistic Regression': LogisticRegression(max_iter=1000),
            'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
            'Support Vector Machine': SVC(random_state=42),
            'XGBoost': xgb.XGBClassifier(random_state=42)
        }

        # Track the best model and score
        best_model = None
        best_score = 0
        best_model_name = ""

        # Train and evaluate each model
        for model_name, clf in classifiers.items():
            print(f"\n🎯 Training {model_name}...")
            clf.fit(X_train, y_train)

            print(f"✅ Training complete for {model_name}. Evaluating...")
            y_pred = clf.predict(X_test)

            report = classification_report(y_test, y_pred, target_names=['easy', 'medium', 'hard'], output_dict=True)
            accuracy = report['accuracy']
            print(f"📝 Classification Report for {model_name}:\n{classification_report(y_test, y_pred, target_names=['easy', 'medium', 'hard'])}")

            # If this model performs better, save it
            if accuracy > best_score:
                best_score = accuracy
                best_model = clf
                best_model_name = model_name

        # Save the best model
        print(f"\n🎉 Best model is: {best_model_name} with accuracy: {best_score:.4f}")
        joblib.dump(best_model, 'best_difficulty_classifier.pkl')
        print("💾 Best model saved as best_difficulty_classifier.pkl")
