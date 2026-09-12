from app.ai.interfaces import ClassificationResult, ComplaintClassifier
from app.models.enums import ComplaintCategory

_KEYWORDS: list[tuple[ComplaintCategory, tuple[str, ...]]] = [
    (ComplaintCategory.garbage, ("garbage", "waste", "trash", "dump", "uncollected")),
    (ComplaintCategory.pothole, ("pothole", "pot hole", "crater")),
    (ComplaintCategory.drainage, ("drainage", "drain", "sewage", "sewer")),
    (ComplaintCategory.streetlight, ("streetlight", "street light", "lamp")),
    (ComplaintCategory.water_leakage, ("water leak", "leakage", "pipeline", "burst pipe")),
]


class KeywordComplaintClassifier(ComplaintClassifier):
    """Deterministic demo classifier. Not a trained model."""

    def classify(self, image: bytes | None, text: str) -> ClassificationResult:
        blob = (text or "").lower()
        for category, words in _KEYWORDS:
            if any(word in blob for word in words):
                return ClassificationResult(
                    category=category, confidence=0.92, source="demo_classifier"
                )
        return ClassificationResult(
            category=ComplaintCategory.other, confidence=0.55, source="demo_classifier"
        )


def get_classifier() -> ComplaintClassifier:
    from app.ai.sklearn_classifier import SklearnTextComplaintClassifier
    from app.ai.vision_classifier import TorchVisionComplaintClassifier
    from app.config import settings

    keyword_fallback = KeywordComplaintClassifier()
    text_classifier = (
        SklearnTextComplaintClassifier(fallback_classifier=keyword_fallback)
        if settings.ml_text_classifier_enabled
        else keyword_fallback
    )

    if settings.vision_ai_enabled:
        return TorchVisionComplaintClassifier(fallback_classifier=text_classifier)
    return text_classifier

