import io
from unittest.mock import MagicMock, patch

from PIL import Image
import pytest

from app.ai.classification import KeywordComplaintClassifier, get_classifier
from app.ai.interfaces import ClassificationResult
from app.ai.vision_classifier import TorchVisionComplaintClassifier
from app.config import settings
from app.models.enums import ComplaintCategory


def _create_sample_image_bytes(color=(100, 100, 100)) -> bytes:
    img = Image.new("RGB", (224, 224), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_vision_classifier_valid_image_inference():
    img_bytes = _create_sample_image_bytes(color=(100, 100, 100))
    classifier = TorchVisionComplaintClassifier()

    result = classifier.classify(img_bytes, "Deep pothole on road")
    assert isinstance(result, ClassificationResult)
    assert isinstance(result.category, ComplaintCategory)
    assert 0.0 <= result.confidence <= 1.0
    assert result.source in ("vision_mobilenet_v3", "demo_classifier", "ml_sklearn")


def test_vision_classifier_none_image_fallback():
    fallback = KeywordComplaintClassifier()
    classifier = TorchVisionComplaintClassifier(fallback_classifier=fallback)

    result = classifier.classify(None, "Huge pile of garbage rotting near corner")
    assert result.category == ComplaintCategory.garbage
    assert result.source == "demo_classifier"


def test_vision_classifier_corrupted_image_fallback():
    fallback = KeywordComplaintClassifier()
    classifier = TorchVisionComplaintClassifier(fallback_classifier=fallback)

    corrupt_bytes = b"this is not a valid image format"
    result = classifier.classify(corrupt_bytes, "Streetlight broken and dark")
    assert result.category == ComplaintCategory.streetlight
    assert result.source == "demo_classifier"


def test_vision_classifier_low_confidence_fallback():
    fallback = KeywordComplaintClassifier()
    classifier = TorchVisionComplaintClassifier(
        confidence_threshold=2.0,  # Impossible threshold forcing fallback
        fallback_classifier=fallback,
    )

    img_bytes = _create_sample_image_bytes()
    result = classifier.classify(img_bytes, "Drinking water pipeline burst")
    # Should delegate to fallback
    assert result.category == ComplaintCategory.water_leakage
    assert result.source == "demo_classifier"


def test_get_classifier_factory_vision_mode():
    with patch.object(settings, "vision_ai_enabled", True):
        clf = get_classifier()
        assert isinstance(clf, TorchVisionComplaintClassifier)

    with patch.object(settings, "vision_ai_enabled", False):
        with patch.object(settings, "ml_text_classifier_enabled", False):
            clf = get_classifier()
            assert isinstance(clf, KeywordComplaintClassifier)
