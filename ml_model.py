"""
MedGenius - ML Recommendation Engine
Uses TF-IDF Vectorization + Cosine Similarity + Naive Bayes for medicine recommendations
"""

import numpy as np
import pickle
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import warnings
warnings.filterwarnings('ignore')

from medicine_data import MEDICINES_DB


class MedGeniusRecommendationEngine:
    """
    ML-powered medicine recommendation engine using:
    1. TF-IDF Vectorization of symptoms/conditions
    2. Cosine Similarity for medicine matching
    3. Logistic Regression classifier for condition prediction
    4. Content-based filtering for alternative recommendations
    """

    def __init__(self):
        self.tfidf = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words='english',
            max_features=5000,
            analyzer='word'
        )
        self.classifier = LogisticRegression(
            max_iter=1000,
            C=1.0,
            random_state=42
        )
        self.medicine_vectors = None
        self.medicines = MEDICINES_DB
        self.label_encoder = LabelEncoder()
        self.is_trained = False
        self.model_path = os.path.join(os.path.dirname(__file__), '../models/medgenius_model.pkl')

    def _prepare_training_data(self):
        """Create training data from medicine database with augmentation"""
        X_texts = []
        y_labels = []

        # Symptom templates for data augmentation
        templates = [
            "{symptoms}",
            "patient has {symptoms}",
            "suffering from {symptoms}",
            "symptoms include {symptoms}",
            "experiencing {symptoms}",
            "complains of {symptoms}",
            "diagnosed with {symptoms}",
            "{conditions}",
            "treatment for {conditions}",
            "medicine for {conditions}",
            "drug for {conditions}",
        ]

        for med in self.medicines:
            symptoms = med["symptoms"]
            conditions = " ".join(med["conditions"])
            combined = f"{symptoms} {conditions}"

            for template in templates:
                text = template.format(
                    symptoms=symptoms,
                    conditions=conditions
                )
                X_texts.append(text)
                y_labels.append(med["name"])

            # Add brand name aliases
            for brand in med["brand_names"]:
                X_texts.append(f"{brand} {symptoms}")
                y_labels.append(med["name"])

        return X_texts, y_labels

    def train(self):
        """Train the recommendation model"""
        print("[MedGenius ML] Preparing training data...")
        X_texts, y_labels = self._prepare_training_data()

        print(f"[MedGenius ML] Training on {len(X_texts)} samples for {len(self.medicines)} medicines")

        # Fit and transform training data
        X = self.tfidf.fit_transform(X_texts)
        y = self.label_encoder.fit_transform(y_labels)

        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Train classifier
        self.classifier.fit(X_train, y_train)

        # Evaluate
        y_pred = self.classifier.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        print(f"[MedGenius ML] Model Accuracy: {acc*100:.1f}%")

        # Build medicine feature vectors for similarity search
        med_texts = [f"{m['symptoms']} {' '.join(m['conditions'])} {m['category']}" 
                     for m in self.medicines]
        self.medicine_vectors = self.tfidf.transform(med_texts)

        self.is_trained = True
        self._save_model()
        print("[MedGenius ML] ✅ Model trained and saved!")
        return acc

    def _save_model(self):
        """Save the trained model"""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        model_data = {
            'tfidf': self.tfidf,
            'classifier': self.classifier,
            'label_encoder': self.label_encoder,
            'medicine_vectors': self.medicine_vectors,
        }
        with open(self.model_path, 'wb') as f:
            pickle.dump(model_data, f)

    def load_model(self):
        """Load a previously trained model"""
        if os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as f:
                data = pickle.load(f)
            self.tfidf = data['tfidf']
            self.classifier = data['classifier']
            self.label_encoder = data['label_encoder']
            self.medicine_vectors = data['medicine_vectors']
            self.is_trained = True
            print("[MedGenius ML] ✅ Model loaded from disk")
            return True
        return False

    def recommend_by_symptoms(self, symptom_text, top_k=5):
        """
        Recommend medicines based on symptom description
        Returns top-k medicines with confidence scores
        """
        if not self.is_trained:
            self.train()

        # Vectorize input
        query_vec = self.tfidf.transform([symptom_text.lower()])

        # Get classifier probabilities
        proba = self.classifier.predict_proba(query_vec)[0]
        top_indices = np.argsort(proba)[::-1][:top_k]

        # Cosine similarity for additional ranking
        similarities = cosine_similarity(query_vec, self.medicine_vectors).flatten()

        results = []
        seen_meds = set()

        for idx in top_indices:
            med_name = self.label_encoder.inverse_transform([idx])[0]
            confidence = float(proba[idx])

            if confidence < 0.01:
                continue

            # Find medicine in DB
            med = next((m for m in self.medicines if m["name"] == med_name), None)
            if med and med["name"] not in seen_meds:
                seen_meds.add(med["name"])
                med_idx = self.medicines.index(med)
                sim_score = float(similarities[med_idx])
                combined_score = (confidence * 0.6) + (sim_score * 0.4)

                results.append({
                    "medicine": med,
                    "confidence": round(confidence * 100, 1),
                    "similarity": round(sim_score * 100, 1),
                    "score": round(combined_score * 100, 1)
                })

        # Also add cosine-similarity based results
        top_sim_indices = np.argsort(similarities)[::-1][:top_k]
        for idx in top_sim_indices:
            med = self.medicines[idx]
            if med["name"] not in seen_meds and similarities[idx] > 0.05:
                seen_meds.add(med["name"])
                results.append({
                    "medicine": med,
                    "confidence": round(similarities[idx] * 60, 1),
                    "similarity": round(float(similarities[idx]) * 100, 1),
                    "score": round(float(similarities[idx]) * 70, 1)
                })

        # Sort by combined score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def find_generic_alternatives(self, brand_name_or_condition, top_k=3):
        """Find cheaper generic alternatives for a medicine or condition"""
        if not self.is_trained:
            self.train()

        # Find the source medicine
        source_med = None
        brand_lower = brand_name_or_condition.lower()

        for med in self.medicines:
            if (brand_lower in med["name"].lower() or
                brand_lower in med["generic_name"].lower() or
                any(brand_lower in b.lower() for b in med["brand_names"])):
                source_med = med
                break

        if not source_med:
            return []

        # Find similar medicines using cosine similarity
        source_idx = self.medicines.index(source_med)
        source_vec = self.medicine_vectors[source_idx]

        similarities = cosine_similarity(source_vec, self.medicine_vectors).flatten()
        similar_indices = np.argsort(similarities)[::-1]

        alternatives = []
        for idx in similar_indices:
            med = self.medicines[idx]
            if med["id"] != source_med["id"] and similarities[idx] > 0.1:
                alternatives.append({
                    "medicine": med,
                    "similarity": round(float(similarities[idx]) * 100, 1),
                    "same_category": med["category"] == source_med["category"]
                })
                if len(alternatives) >= top_k:
                    break

        return alternatives

    def search_medicines(self, query, top_k=8):
        """General medicine search with fuzzy matching"""
        if not self.is_trained:
            self.train()

        results = []
        query_lower = query.lower()

        # Direct name matching (high priority)
        for med in self.medicines:
            score = 0
            if query_lower in med["name"].lower():
                score = 100
            elif query_lower in med["generic_name"].lower():
                score = 95
            elif any(query_lower in b.lower() for b in med["brand_names"]):
                score = 90
            elif any(query_lower in c.lower() for c in med["conditions"]):
                score = 75

            if score > 0:
                results.append({"medicine": med, "score": score})

        # ML-based semantic search if not enough results
        if len(results) < 3:
            ml_results = self.recommend_by_symptoms(query, top_k=5)
            seen = {r["medicine"]["name"] for r in results}
            for r in ml_results:
                if r["medicine"]["name"] not in seen:
                    results.append({
                        "medicine": r["medicine"],
                        "score": r["score"] * 0.8
                    })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]


# Singleton model instance
_model_instance = None

def get_model():
    global _model_instance
    if _model_instance is None:
        _model_instance = MedGeniusRecommendationEngine()
        if not _model_instance.load_model():
            _model_instance.train()
    return _model_instance


if __name__ == "__main__":
    print("=== MedGenius ML Training ===")
    engine = MedGeniusRecommendationEngine()
    acc = engine.train()
    print(f"\nTraining Accuracy: {acc*100:.1f}%")

    # Test recommendations
    test_queries = [
        "I have fever and headache",
        "high blood sugar diabetes symptoms",
        "chest infection cough bacterial",
        "acidity and heartburn after eating",
        "allergy sneezing itchy eyes"
    ]

    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        recs = engine.recommend_by_symptoms(query, top_k=3)
        for i, r in enumerate(recs, 1):
            print(f"  {i}. {r['medicine']['name']} (Score: {r['score']}%)")