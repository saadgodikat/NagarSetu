from app.ai.classification import KeywordComplaintClassifier
from app.ai.department import department_id_for_category
from app.ai.priority import score_priority
from app.ai.severity import rule_severity
from app.models.enums import ComplaintCategory, Severity
from app.storage.images import validate_image


def test_garbage_keywords_classify_as_garbage() -> None:
    result = KeywordComplaintClassifier().classify(
        None, "Garbage has not been collected for 4 days near Tuljapur Naka."
    )
    assert result.category == ComplaintCategory.garbage
    assert result.source == "demo_classifier"
    assert 0 < result.confidence <= 1


def test_unknown_text_classifies_as_other() -> None:
    result = KeywordComplaintClassifier().classify(None, "Something is wrong on my street")
    assert result.category == ComplaintCategory.other


def test_high_severity_from_public_health_keywords() -> None:
    severity, reasons = rule_severity(
        "Garbage has not been collected for 4 days. It smells terrible and is unsafe."
    )
    assert severity == Severity.HIGH
    assert reasons


def test_garbage_maps_to_solid_waste() -> None:
    assert department_id_for_category(ComplaintCategory.garbage) == 1


def test_other_maps_to_public_works() -> None:
    assert department_id_for_category(ComplaintCategory.other) == 7


def test_priority_returns_score_and_reasons() -> None:
    score, label, reasons = score_priority(
        severity=Severity.HIGH,
        related_count=3,
        duration_days=4,
        safety_risk=True,
    )
    assert score == 100
    assert label == "critical"
    assert len(reasons) == 4


def test_rejects_non_image_bytes() -> None:
    ok, reason = validate_image(b"not-an-image", "file.txt", "text/plain")
    assert ok is False
    assert reason
