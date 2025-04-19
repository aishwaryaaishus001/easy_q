import os
import joblib
import logging
import matplotlib.pyplot as plt
from django.core.management.base import BaseCommand
from classifier.models import ClusteredQuestion
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, ConfusionMatrixDisplay
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
import xgboost as xgb
from sentence_transformers import SentenceTransformer
import numpy as np

# Create directories if they don't exist
os.makedirs('classifier/trained_models/images', exist_ok=True)
os.makedirs('classifier/trained_models', exist_ok=True)

DIFFICULTY_MAP = {'easy': 0, 'medium': 1, 'hard': 2}
LABELS = ['easy', 'medium', 'hard']

class Command(BaseCommand):
    help = 'Train and compare multiple classifiers, select the best model, and use it for predictions'

    def handle(self, *args, **options):
        print("📌 Loading SBERT model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')

        questions = ClusteredQuestion.objects.exclude(difficulty__isnull=True)

        texts = [q.text for q in questions]
        y = [DIFFICULTY_MAP[q.difficulty.lower()] for q in questions]
        X = np.array([q.get_embedding() for q in questions])

        print(f"🧠 Using {len(texts)} questions with embeddings for training...")

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        classifiers = {
            'Logistic Regression': LogisticRegression(max_iter=1000),
            'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
            'Support Vector Machine': SVC(probability=True, random_state=42),
            'XGBoost': xgb.XGBClassifier(random_state=42)
        }

        best_model = None
        best_score = 0
        best_model_name = ""

        for model_name, clf in classifiers.items():
            print(f"\n🎯 Training {model_name}...")
            clf.fit(X_train, y_train)

            y_pred = clf.predict(X_test)
            report = classification_report(y_test, y_pred, target_names=LABELS, output_dict=True)
            accuracy = report['accuracy']
            print(f"📝 Classification Report for {model_name}:\n{classification_report(y_test, y_pred, target_names=LABELS)}")

            # Save confusion matrix
            cm = confusion_matrix(y_test, y_pred)
            disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=LABELS)
            cm_path = f"classifier/trained_models/images/confusion_matrix_{model_name.replace(' ', '_')}.png"
            disp.plot(cmap='Blues', values_format='d')
            plt.savefig(cm_path)
            print(f"📊 Confusion matrix saved at: {cm_path}")
            plt.close()

            if accuracy > best_score:
                best_score = accuracy
                best_model = clf
                best_model_name = model_name

        print(f"\n🎉 Best model is: {best_model_name} with accuracy: {best_score:.4f}")

        # Save best model
        model_dir = "classifier/trained_models"
        model_path = os.path.join(model_dir, "best_difficulty_classifier.pkl")
        joblib.dump(best_model, model_path)
        print(f"💾 Best model saved at: {model_path}")

