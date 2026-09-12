"""
Tests for Phase 6: Multi-Signal Resolution Verification.

Validates:
  1. Before/After photo comparison (including identical-photo fraud detection)
  2. GPS proximity validation (haversine calculations, geofence radius)
  3. Timestamp validation (chronology, plausible duration, SLA compliance)
  4. Citizen feedback (confirmation, 1-5 star ratings, rejection veto)
  5. Composite verification decision synthesis and recommendations
  6. verify_complaint_resolution helper and schema serialization
"""

import io
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import numpy as np
from PIL import Image

from app.ai.interfaces import ResolutionVerifier, SignalResult, VerificationResult
from app.ai.resolution_verifier import (
    MultiSignalResolutionVerifier,
    get_resolution_verifier,
    haversine_distance_meters,
    verify_complaint_resolution,
)
from app.models.enums import ComplaintCategory, ComplaintStatus, ImageType, Severity
from app.schemas.complaints import VerificationReportOut


# ---------------------------------------------------------------------------
# Test Helpers: Generate Synthetic Test Images
# ---------------------------------------------------------------------------
def _create_test_image(color: tuple[int, int, int], pattern: str = "plain") -> bytes:
    """Create a 64x64 PNG image in bytes."""
    img = Image.new("RGB", (64, 64), color=color)
    if pattern == "cross":
        # Draw contrasting pixels
        for i in range(64):
            img.putpixel((i, i), (255, 255, 255))
            img.putpixel((i, 63 - i), (255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class MockComplaint:
    """Mock complaint object for testing verify_complaint_resolution."""

    def __init__(
        self,
        complaint_id=None,
        lat=17.6599,
        lng=75.9064,
        status=ComplaintStatus.resolution_submitted,
        created_at=None,
        assigned_at=None,
        resolved_at=None,
        sla_deadline=None,
        citizen_rating=None,
        citizen_feedback=None,
    ):
        now = datetime.now(timezone.utc)
        self.id = complaint_id or uuid4()
        self.location_lat = lat
        self.location_lng = lng
        self.status = status
        self.created_at = created_at or (now - timedelta(hours=5))
        self.assigned_at = assigned_at or (now - timedelta(hours=3))
        self.resolved_at = resolved_at or (now - timedelta(minutes=10))
        self.sla_deadline = sla_deadline or (now + timedelta(hours=19))
        self.citizen_rating = citizen_rating
        self.citizen_feedback = citizen_feedback
        self.verification_score = None
        self.verification_status = None
        self.verification_details = None
        self.verified_at = None
        self.images = []


# ---------------------------------------------------------------------------
# Signal 1: Photo Comparison Tests
# ---------------------------------------------------------------------------
def test_photo_signal_missing_after_photo() -> None:
    verifier = MultiSignalResolutionVerifier()
    before_img = _create_test_image((100, 100, 100))
    sig = verifier.evaluate_photo_signal(before_img, None)

    assert sig.passed is False
    assert sig.score == 0.0
    assert sig.status == "missing_after_photo"
    assert sig.metrics["has_after_photo"] is False


def test_photo_signal_missing_before_photo() -> None:
    verifier = MultiSignalResolutionVerifier()
    after_img = _create_test_image((120, 120, 120))
    sig = verifier.evaluate_photo_signal(None, after_img)

    assert sig.passed is True
    assert sig.score == 0.60
    assert sig.status == "single_photo_available"


def test_photo_signal_identical_photo_fraud_detection() -> None:
    """Anti-fraud check: submitting the exact same photo as before & after must be flagged."""
    verifier = MultiSignalResolutionVerifier()
    img_bytes = _create_test_image((80, 80, 80), pattern="cross")

    sig = verifier.evaluate_photo_signal(img_bytes, img_bytes)

    assert sig.passed is False
    assert sig.score == 0.0
    assert sig.status == "identical_photos_detected"
    assert "Fraud risk" in sig.details


def test_photo_signal_valid_distinct_resolution_photos() -> None:
    verifier = MultiSignalResolutionVerifier()
    before_img = _create_test_image((50, 50, 50), pattern="plain")
    after_img = _create_test_image((200, 200, 200), pattern="cross")

    sig = verifier.evaluate_photo_signal(before_img, after_img)

    assert sig.passed is True
    assert sig.score >= 0.70
    assert sig.status in ("valid_visual_change", "distinct_photos_uploaded")
    assert sig.metrics["visual_difference"] is not None
    assert sig.metrics["visual_difference"] > 0.05


# ---------------------------------------------------------------------------
# Signal 2: GPS Proximity Tests
# ---------------------------------------------------------------------------
def test_haversine_distance_calculation() -> None:
    # Solapur coordinates: exact same point
    dist_zero = haversine_distance_meters(17.6599, 75.9064, 17.6599, 75.9064)
    assert round(dist_zero, 1) == 0.0

    # Slight offset (~111 meters north: 0.001 deg lat)
    dist_nearby = haversine_distance_meters(17.6599, 75.9064, 17.6609, 75.9064)
    assert 100.0 <= dist_nearby <= 125.0


def test_gps_signal_exact_location() -> None:
    verifier = MultiSignalResolutionVerifier()
    sig = verifier.evaluate_gps_signal(17.6599, 75.9064, 17.6599, 75.9064)

    assert sig.passed is True
    assert sig.score == 1.0
    assert sig.status == "exact_location_match"


def test_gps_signal_close_vicinity() -> None:
    verifier = MultiSignalResolutionVerifier()
    # ~200m away
    sig = verifier.evaluate_gps_signal(17.6599, 75.9064, 17.6617, 75.9064)

    assert sig.passed is True
    assert sig.score == 0.75
    assert sig.status == "close_proximity_match"


def test_gps_signal_borderline_warning() -> None:
    verifier = MultiSignalResolutionVerifier()
    # ~400m away
    sig = verifier.evaluate_gps_signal(17.6599, 75.9064, 17.6635, 75.9064)

    assert sig.passed is False
    assert sig.score == 0.40
    assert sig.status == "borderline_proximity_warning"


def test_gps_signal_out_of_bounds_mismatch() -> None:
    verifier = MultiSignalResolutionVerifier()
    # ~2.2 km away
    sig = verifier.evaluate_gps_signal(17.6599, 75.9064, 17.6800, 75.9064)

    assert sig.passed is False
    assert sig.score == 0.0
    assert sig.status == "out_of_bounds_location_mismatch"


def test_gps_signal_missing_coordinates() -> None:
    verifier = MultiSignalResolutionVerifier()
    sig = verifier.evaluate_gps_signal(17.6599, 75.9064, None, None)

    assert sig.passed is False
    assert sig.score == 0.50
    assert sig.status == "gps_missing"


# ---------------------------------------------------------------------------
# Signal 3: Timestamp Validity Tests
# ---------------------------------------------------------------------------
def test_timestamp_signal_valid_within_sla() -> None:
    verifier = MultiSignalResolutionVerifier(min_duration_seconds=30)
    now = datetime.now(timezone.utc)
    created = now - timedelta(hours=4)
    assigned = now - timedelta(hours=2)
    resolved = now - timedelta(minutes=5)
    sla = now + timedelta(hours=20)

    sig = verifier.evaluate_timestamp_signal(created, assigned, resolved, sla)

    assert sig.passed is True
    assert sig.score == 1.0
    assert sig.status == "resolved_within_sla"
    assert sig.metrics["within_sla"] is True


def test_timestamp_signal_resolved_after_sla() -> None:
    verifier = MultiSignalResolutionVerifier(min_duration_seconds=30)
    now = datetime.now(timezone.utc)
    created = now - timedelta(hours=48)
    assigned = now - timedelta(hours=36)
    resolved = now - timedelta(minutes=10)
    sla = now - timedelta(hours=12)  # expired 12h ago

    sig = verifier.evaluate_timestamp_signal(created, assigned, resolved, sla)

    assert sig.passed is True
    assert sig.score == 0.75
    assert sig.status == "resolved_after_sla"
    assert sig.metrics["within_sla"] is False


def test_timestamp_signal_clock_anomaly_negative() -> None:
    verifier = MultiSignalResolutionVerifier()
    now = datetime.now(timezone.utc)
    created = now
    resolved = now - timedelta(hours=1)  # before created

    sig = verifier.evaluate_timestamp_signal(created, None, resolved, None)

    assert sig.passed is False
    assert sig.score == 0.0
    assert sig.status == "invalid_chronology"


def test_timestamp_signal_suspiciously_instantaneous() -> None:
    verifier = MultiSignalResolutionVerifier(min_duration_seconds=30)
    now = datetime.now(timezone.utc)
    created = now - timedelta(seconds=10)
    assigned = now - timedelta(seconds=10)
    resolved = now  # 10s turnaround < 30s min

    sig = verifier.evaluate_timestamp_signal(created, assigned, resolved, None)

    assert sig.passed is False
    assert sig.score == 0.40
    assert sig.status == "suspiciously_instantaneous_resolution"


# ---------------------------------------------------------------------------
# Signal 4: Citizen Feedback Tests
# ---------------------------------------------------------------------------
def test_citizen_signal_confirmed_with_5_stars() -> None:
    verifier = MultiSignalResolutionVerifier()
    sig = verifier.evaluate_citizen_signal(citizen_confirmed=True, citizen_rating=5)

    assert sig.passed is True
    assert sig.score == 1.0
    assert sig.status == "confirmed_by_citizen"


def test_citizen_signal_confirmed_with_3_stars() -> None:
    verifier = MultiSignalResolutionVerifier()
    sig = verifier.evaluate_citizen_signal(citizen_confirmed=True, citizen_rating=3)

    assert sig.passed is True
    assert sig.score == 0.60
    assert sig.status == "confirmed_by_citizen"


def test_citizen_signal_rejected() -> None:
    verifier = MultiSignalResolutionVerifier()
    sig = verifier.evaluate_citizen_signal(
        citizen_confirmed=False,
        feedback_notes="Pothole was only half filled, dangerous edge remains.",
    )

    assert sig.passed is False
    assert sig.score == 0.0
    assert sig.status == "rejected_by_citizen"


def test_citizen_signal_pending() -> None:
    verifier = MultiSignalResolutionVerifier()
    sig = verifier.evaluate_citizen_signal(citizen_confirmed=None)

    assert sig.passed is True
    assert sig.score == 0.60
    assert sig.status == "pending_citizen_confirmation"


# ---------------------------------------------------------------------------
# Composite Verification Decision Tests
# ---------------------------------------------------------------------------
def test_composite_verification_all_pass_citizen_confirmed() -> None:
    verifier = MultiSignalResolutionVerifier()
    before_img = _create_test_image((60, 60, 60))
    after_img = _create_test_image((220, 220, 220), pattern="cross")

    now = datetime.now(timezone.utc)
    metadata = {
        "complaint_lat": 17.6599,
        "complaint_lng": 75.9064,
        "evidence_lat": 17.65995,
        "evidence_lng": 75.90642,
        "created_at": now - timedelta(hours=3),
        "assigned_at": now - timedelta(hours=2),
        "resolved_at": now - timedelta(minutes=15),
        "sla_deadline": now + timedelta(hours=21),
        "citizen_confirmed": True,
        "citizen_rating": 5,
        "citizen_feedback": "Excellent work",
    }

    result = verifier.verify(before_img, after_img, metadata)

    assert result.verified is True
    assert result.status == "verified"
    assert result.composite_score >= 0.85
    assert len(result.flags) == 0
    assert "closure" in result.recommendation.lower()


def test_composite_verification_provisionally_verified_when_citizen_pending() -> None:
    verifier = MultiSignalResolutionVerifier()
    before_img = _create_test_image((60, 60, 60))
    after_img = _create_test_image((220, 220, 220), pattern="cross")

    now = datetime.now(timezone.utc)
    metadata = {
        "complaint_lat": 17.6599,
        "complaint_lng": 75.9064,
        "evidence_lat": 17.6599,
        "evidence_lng": 75.9064,
        "created_at": now - timedelta(hours=3),
        "assigned_at": now - timedelta(hours=2),
        "resolved_at": now - timedelta(minutes=15),
        "sla_deadline": now + timedelta(hours=21),
        "citizen_confirmed": None,  # Pending
    }

    result = verifier.verify(before_img, after_img, metadata)

    assert result.verified is True
    assert result.status == "provisionally_verified"
    assert result.composite_score >= 0.75
    assert "awaiting citizen" in result.recommendation.lower()


def test_composite_verification_blocks_on_identical_photo_fraud() -> None:
    verifier = MultiSignalResolutionVerifier()
    same_img = _create_test_image((100, 100, 100), pattern="cross")

    now = datetime.now(timezone.utc)
    metadata = {
        "complaint_lat": 17.6599,
        "complaint_lng": 75.9064,
        "evidence_lat": 17.6599,
        "evidence_lng": 75.9064,
        "created_at": now - timedelta(hours=3),
        "assigned_at": now - timedelta(hours=2),
        "resolved_at": now - timedelta(minutes=15),
        "citizen_confirmed": True,
    }

    result = verifier.verify(same_img, same_img, metadata)

    assert result.verified is False
    assert result.status == "rejected"
    assert "identical_photos_fraud_risk" in result.flags
    assert "FRAUD RISK" in result.recommendation


def test_composite_verification_citizen_rejection_overrides() -> None:
    verifier = MultiSignalResolutionVerifier()
    before_img = _create_test_image((40, 40, 40))
    after_img = _create_test_image((200, 200, 200), pattern="cross")

    now = datetime.now(timezone.utc)
    metadata = {
        "complaint_lat": 17.6599,
        "complaint_lng": 75.9064,
        "evidence_lat": 17.6599,
        "evidence_lng": 75.9064,
        "created_at": now - timedelta(hours=3),
        "assigned_at": now - timedelta(hours=2),
        "resolved_at": now - timedelta(minutes=15),
        "citizen_confirmed": False,
        "citizen_feedback": "Pothole still present",
    }

    result = verifier.verify(before_img, after_img, metadata)

    assert result.verified is False
    assert result.status == "rejected"
    assert "citizen_rejected_resolution" in result.flags
    assert "re-opened" in result.recommendation.lower()


# ---------------------------------------------------------------------------
# verify_complaint_resolution Helper & Serialization Tests
# ---------------------------------------------------------------------------
def test_verify_complaint_resolution_helper_stamps_complaint() -> None:
    complaint = MockComplaint(citizen_rating=5, citizen_feedback="All cleared")
    before_img = _create_test_image((50, 50, 50))
    after_img = _create_test_image((180, 180, 180), pattern="cross")

    result = verify_complaint_resolution(
        complaint,
        before_content=before_img,
        after_content=after_img,
        evidence_lat=17.6599,
        evidence_lng=75.9064,
        citizen_confirmed=True,
    )

    assert result.verified is True
    assert complaint.verification_score == result.composite_score
    assert complaint.verification_status == result.status
    assert complaint.verification_details is not None
    assert complaint.verification_details["status"] == result.status
    assert complaint.verified_at is not None

    # Test Pydantic serialization
    report_out = VerificationReportOut(
        complaint_id=complaint.id,
        verified=result.verified,
        status=result.status,
        composite_score=result.composite_score,
        signals=result.signals,
        recommendation=result.recommendation,
        flags=result.flags,
        evaluated_at=result.evaluated_at,
        source=result.source,
    )
    assert report_out.verified is True
    assert report_out.composite_score == result.composite_score
    assert len(report_out.signals) == 4


def test_factory_returns_singleton() -> None:
    v1 = get_resolution_verifier()
    v2 = get_resolution_verifier()
    assert v1 is v2
    assert isinstance(v1, ResolutionVerifier)
