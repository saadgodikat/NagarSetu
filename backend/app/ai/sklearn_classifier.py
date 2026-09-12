import logging
from pathlib import Path

import joblib
import numpy as np

from app.ai.interfaces import ClassificationResult, ComplaintClassifier
from app.config import settings
from app.models.enums import ComplaintCategory

logger = logging.getLogger(__name__)

# Category String to ComplaintCategory Enum Mapping
STR_TO_ENUM = {
    "garbage": ComplaintCategory.garbage,
    "pothole": ComplaintCategory.pothole,
    "drainage": ComplaintCategory.drainage,
    "streetlight": ComplaintCategory.streetlight,
    "water_leakage": ComplaintCategory.water_leakage,
    "other": ComplaintCategory.other,
}


class SklearnTextComplaintClassifier(ComplaintClassifier):
    """
    Genuine ML Complaint Classifier using TF-IDF + LogisticRegression.
    Falls back to KeywordComplaintClassifier if confidence is below threshold
    or if model loading/inference fails.
    """

    def __init__(self, fallback_classifier: ComplaintClassifier, model_path: str | Path | None = None):
        self.fallback = fallback_classifier
        self.model_path = Path(model_path or settings.ml_model_path)
        self.vectorizer = None
        self.classifier = None
        self.model_version = "sklearn_text_v1.0.0"
        self.threshold = settings.ml_confidence_threshold
        self._load_model()

    def _load_model(self) -> bool:
        if not self.model_path.exists():
            # Try absolute path relative to project root if relative path fails
            alt_path = Path(__file__).resolve().parents[3] / self.model_path
            if alt_path.exists():
                self.model_path = alt_path
            else:
                logger.warning(f"ML Model file not found at {self.model_path}. Using fallback.")
                return False

        try:
            artifact = joblib.load(self.model_path)
            self.vectorizer = artifact["vectorizer"]
            self.classifier = artifact["classifier"]
            self.model_version = f"sklearn_text_{artifact.get('model_version', 'v1.0.0')}"
            self.threshold = artifact.get("threshold", self.threshold)
            logger.info(f"Loaded ML Text Classifier model from {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load ML Text Classifier from {self.model_path}: {e}")
            return False

    def classify(self, image: bytes | None, text: str) -> ClassificationResult:
        # Handle malformed or empty text input
        clean_text = (text or "").strip()
        if not clean_text:
            return self.fallback.classify(image, text)

        if self.vectorizer is None or self.classifier is None:
            if not self._load_model():
                return self.fallback.classify(image, text)

        try:
            X = self.vectorizer.transform([clean_text])
            probabilities = self.classifier.predict_proba(X)[0]
            max_idx = np.argmax(probabilities)
            predicted_str = self.classifier.classes_[max_idx]
            confidence = float(probabilities[max_idx])

            # Confidence Gating Check
            if confidence < self.threshold:
                logger.info(
                    f"ML prediction confidence ({confidence:.2f}) below threshold ({self.threshold:.2f}). Falling back."
                )
                return self.fallback.classify(image, text)

            category_enum = STR_TO_ENUM.get(predicted_str, ComplaintCategory.other)
            return ClassificationResult(
                category=category_enum,
                confidence=round(confidence, 4),
                source=self.model_version,
            )
        except Exception as e:
            logger.error(f"Inference error in SklearnTextComplaintClassifier: {e}")
            return self.fallback.classify(image, text)
