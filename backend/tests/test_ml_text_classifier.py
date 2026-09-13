from pathlib import Path
import pytest

from app.ai.classification import KeywordComplaintClassifier, get_classifier
from app.ai.sklearn_classifier import SklearnTextComplaintClassifier
from app.config import settings
from app.models.enums import ComplaintCategory


def test_disabled_ml_mode_returns_keyword_classifier(monkeypatch):
    monkeypatch.setattr(settings, "vision_ai_enabled", False)
    monkeypatch.setattr(settings, "ml_text_classifier_enabled", False)
    classifier = get_classifier()
    assert isinstance(classifier, KeywordComplaintClassifier)
    
    result = classifier.classify(None, "Garbage near my house")
    assert result.source == "demo_classifier"
    assert result.category == ComplaintCategory.garbage


def test_enabled_ml_mode_returns_sklearn_classifier(monkeypatch):
    monkeypatch.setattr(settings, "vision_ai_enabled", False)
    monkeypatch.setattr(settings, "ml_text_classifier_enabled", True)
    classifier = get_classifier()
    assert isinstance(classifier, SklearnTextComplaintClassifier)


def test_sklearn_classifier_predictions_all_six_categories(monkeypatch):
    monkeypatch.setattr(settings, "ml_text_classifier_enabled", True)
    classifier = SklearnTextComplaintClassifier(fallback_classifier=KeywordComplaintClassifier())

    test_cases = [
        ("Garbage and waste dumped on roadside", ComplaintCategory.garbage),
        ("Huge deep pothole on main road causing accidents", ComplaintCategory.pothole),
        ("Clogged storm water drain overflowing foul sewage water", ComplaintCategory.drainage),
        ("Dark street due to broken lamp on electric pole", ComplaintCategory.streetlight),
        ("Burst water supply pipe leaking drinking water on road", ComplaintCategory.water_leakage),
        ("Illegal shop banner encroachment blocking walkway", ComplaintCategory.other),
    ]

    for text, expected_cat in test_cases:
        result = classifier.classify(None, text)
        assert result.category == expected_cat
        assert result.confidence > 0.50
        assert "sklearn_text" in result.source


def test_probability_confidence_distribution_and_threshold_fallback(monkeypatch):
    fallback = KeywordComplaintClassifier()
    classifier = SklearnTextComplaintClassifier(fallback_classifier=fallback)

    # Test confidence score is bounded between 0.0 and 1.0
    result = classifier.classify(None, "Huge pothole on road")
    assert 0.0 <= result.confidence <= 1.0
    assert result.source.startswith("sklearn_text")

    # High threshold forcing fallback
    classifier.threshold = 0.9999
    fallback_result = classifier.classify(None, "Huge pothole on road")
    assert fallback_result.source == "demo_classifier"


def test_fallback_on_missing_model_file():
    fallback = KeywordComplaintClassifier()
    missing_path = Path("backend/models/non_existent_model.joblib")
    classifier = SklearnTextComplaintClassifier(fallback_classifier=fallback, model_path=missing_path)

    result = classifier.classify(None, "Garbage dumped on street")
    assert result.source == "demo_classifier"
    assert result.category == ComplaintCategory.garbage


def test_malformed_empty_and_whitespace_text_handling():
    fallback = KeywordComplaintClassifier()
    classifier = SklearnTextComplaintClassifier(fallback_classifier=fallback)

    for empty_input in ["", "   ", None, "\n\t"]:
        result = classifier.classify(None, empty_input)
        assert result.source == "demo_classifier"
        assert result.category == ComplaintCategory.other
