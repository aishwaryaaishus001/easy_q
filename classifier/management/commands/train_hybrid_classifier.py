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
import json

DIFFICULTY_MAP = {'easy': 0, 'medium': 1, 'hard': 2}

class Command(BaseCommand):
    help = 'Train and compare multiple classifiers, select the best model, and use it for predictions'

    def handle(self, *args, **options):
        print("📌 Loading SBERT model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')

        # Fetching all questions with difficulty labels
        questions = ClusteredQuestion.objects.exclude(difficulty__isnull=True)

        texts = [q.text for q in questions]
        y = [DIFFICULTY_MAP[q.difficulty.lower()] for q in questions]
        X = np.array([q.get_embedding() for q in questions])  # Use stored embeddings directly

        print(f"🧠 Using {len(texts)} questions with embeddings for training...")

        # Split data into training and testing sets
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

            # If this model performs better, keep it as the best model
            if accuracy > best_score:
                best_score = accuracy
                best_model = clf
                best_model_name = model_name

        # Output the best model
        print(f"\n🎉 Best model is: {best_model_name} with accuracy: {best_score:.4f}")

        # Use the best model for further tasks (e.g., saving it for future use)
        # Save the best model (if needed)
        # joblib.dump(best_model, 'best_difficulty_classifier.pkl')
        # print("💾 Best model saved as best_difficulty_classifier.pkl")

        # Now you can use the best_model to make predictions or save it for future use
        # For now, we're just using it for further tasks (like making predictions)

        print("\n💡 Now you can use the best model for further tasks such as predicting new questions' difficulty or saving it.")
