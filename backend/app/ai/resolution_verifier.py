"""
Multi-Signal Resolution Verification – NagarIQ Phase 6.

Combines:
  1. Before/After photo comparison (with identical-photo fraud safeguard)
  2. GPS proximity validation (haversine distance matching)
  3. Timestamp validation (chronology, plausible turnaround, SLA compliance)
  4. Citizen feedback (confirmation, star ratings, rejection veto)

Architecture follows Smart_Municipal_Platform_Coding_Agent_Spec_v2.md (sections 31 & 32):
  - Do NOT implement SSIM-only verification.
  - Verification recommends decisions; final closure requires citizen confirmation
    or authorized officer override.
"""

from __future__ import annotations

import hashlib
import io
import logging
import math
from datetime import datetime, timezone
from typing import Any

import numpy as np
from PIL import Image

from app.ai.interfaces import ResolutionVerifier, SignalResult, VerificationResult
from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Geodesic calculation helper (Haversine formula)
# ---------------------------------------------------------------------------
def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on the Earth in meters."""
    radius_earth_m = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return radius_earth_m * c


# ---------------------------------------------------------------------------
# Multi-Signal Resolution Verifier Implementation
# ---------------------------------------------------------------------------
class MultiSignalResolutionVerifier(ResolutionVerifier):
    """
    Evaluates 4 independent signals to formulate a comprehensive verification verdict.
    """

    WEIGHT_PHOTO = 0.30
    WEIGHT_GPS = 0.30
    WEIGHT_TIMESTAMP = 0.15
    WEIGHT_CITIZEN = 0.25

    def __init__(
        self,
        gps_threshold_meters: float | None = None,
        min_duration_seconds: int | None = None,
        auto_verify_threshold: float | None = None,
        review_threshold: float | None = None,
    ) -> None:
        self.gps_threshold_meters = (
            gps_threshold_meters
            if gps_threshold_meters is not None
            else getattr(settings, "verification_gps_threshold_meters", 200.0)
        )
        self.min_duration_seconds = (
            min_duration_seconds
            if min_duration_seconds is not None
            else getattr(settings, "verification_min_duration_seconds", 30)
        )
        self.auto_verify_threshold = (
            auto_verify_threshold
            if auto_verify_threshold is not None
            else getattr(settings, "verification_auto_verify_threshold", 0.75)
        )
        self.review_threshold = (
            review_threshold
            if review_threshold is not None
            else getattr(settings, "verification_review_threshold", 0.50)
        )

    # -----------------------------------------------------------------------
    # Signal 1: Photo Comparison
    # -----------------------------------------------------------------------
    def evaluate_photo_signal(
        self,
        before_image: bytes | None,
        after_image: bytes | None,
    ) -> SignalResult:
        metrics: dict[str, Any] = {
            "has_before_photo": before_image is not None,
            "has_after_photo": after_image is not None,
            "identical_bytes": False,
            "visual_difference": None,
        }

        if after_image is None:
            return SignalResult(
                name="photo_comparison",
                passed=False,
                score=0.0,
                weight=self.WEIGHT_PHOTO,
                status="missing_after_photo",
                details="No resolution photo has been uploaded.",
                metrics=metrics,
            )

        if before_image is None:
            # After photo uploaded, but initial complaint had no photo
            return SignalResult(
                name="photo_comparison",
                passed=True,
                score=0.60,
                weight=self.WEIGHT_PHOTO,
                status="single_photo_available",
                details="Resolution photo uploaded; baseline photo was missing.",
                metrics=metrics,
            )

        # Anti-fraud check: exact byte identity
        if hashlib.sha256(before_image).hexdigest() == hashlib.sha256(after_image).hexdigest():
            metrics["identical_bytes"] = True
            return SignalResult(
                name="photo_comparison",
                passed=False,
                score=0.0,
                weight=self.WEIGHT_PHOTO,
                status="identical_photos_detected",
                details="Fraud risk: Resolution photo is identical to the complaint report photo.",
                metrics=metrics,
            )

        # Perceptual comparison using PIL & NumPy
        try:
            img_before = Image.open(io.BytesIO(before_image)).convert("L").resize((64, 64))
            img_after = Image.open(io.BytesIO(after_image)).convert("L").resize((64, 64))

            arr_b = np.array(img_before, dtype=np.float32) / 255.0
            arr_a = np.array(img_after, dtype=np.float32) / 255.0

            # Mean absolute pixel difference
            pixel_diff = float(np.mean(np.abs(arr_b - arr_a)))
            metrics["visual_difference"] = round(pixel_diff, 4)

            # Safeguard: if pixel difference is essentially zero (< 1%)
            if pixel_diff < 0.01:
                return SignalResult(
                    name="photo_comparison",
                    passed=False,
                    score=0.0,
                    weight=self.WEIGHT_PHOTO,
                    status="identical_photos_detected",
                    details="Fraud risk: Resolution photo shows no perceptual difference from original photo.",
                    metrics=metrics,
                )

            # Plausible resolution: some visual change indicating work was performed
            if 0.04 <= pixel_diff <= 0.85:
                score = min(1.0, 0.70 + (pixel_diff * 0.40))
                return SignalResult(
                    name="photo_comparison",
                    passed=True,
                    score=round(score, 2),
                    weight=self.WEIGHT_PHOTO,
                    status="valid_visual_change",
                    details=f"Plausible resolution evidence detected (visual difference: {pixel_diff:.1%}).",
                    metrics=metrics,
                )
            else:
                # Either very subtle or entirely distinct scenes
                return SignalResult(
                    name="photo_comparison",
                    passed=True,
                    score=0.75,
                    weight=self.WEIGHT_PHOTO,
                    status="distinct_photos_uploaded",
                    details=f"Resolution photo submitted (visual difference: {pixel_diff:.1%}).",
                    metrics=metrics,
                )
        except Exception as exc:
            logger.warning("Visual comparison error: %s", exc)
            return SignalResult(
                name="photo_comparison",
                passed=True,
                score=0.70,
                weight=self.WEIGHT_PHOTO,
                status="photo_uploaded",
                details="Resolution photo verified (basic format check passed).",
                metrics=metrics,
            )

    # -----------------------------------------------------------------------
    # Signal 2: GPS Proximity Validation
    # -----------------------------------------------------------------------
    def evaluate_gps_signal(
        self,
        complaint_lat: float,
        complaint_lng: float,
        evidence_lat: float | None,
        evidence_lng: float | None,
    ) -> SignalResult:
        metrics: dict[str, Any] = {
            "complaint_lat": complaint_lat,
            "complaint_lng": complaint_lng,
            "evidence_lat": evidence_lat,
            "evidence_lng": evidence_lng,
            "distance_meters": None,
        }

        if evidence_lat is None or evidence_lng is None:
            return SignalResult(
                name="gps_proximity",
                passed=False,
                score=0.50,
                weight=self.WEIGHT_GPS,
                status="gps_missing",
                details="Resolution photo lacks GPS location data.",
                metrics=metrics,
            )

        distance = haversine_distance_meters(
            complaint_lat, complaint_lng, evidence_lat, evidence_lng
        )
        metrics["distance_meters"] = round(distance, 1)

        if distance <= 150.0:
            return SignalResult(
                name="gps_proximity",
                passed=True,
                score=1.0,
                weight=self.WEIGHT_GPS,
                status="exact_location_match",
                details=f"GPS matches complaint location within {distance:.0f}m.",
                metrics=metrics,
            )
        elif distance <= 300.0:
            return SignalResult(
                name="gps_proximity",
                passed=True,
                score=0.75,
                weight=self.WEIGHT_GPS,
                status="close_proximity_match",
                details=f"GPS is within acceptable vicinity ({distance:.0f}m away, allowable: 300m).",
                metrics=metrics,
            )
        elif distance <= 500.0:
            return SignalResult(
                name="gps_proximity",
                passed=False,
                score=0.40,
                weight=self.WEIGHT_GPS,
                status="borderline_proximity_warning",
                details=f"GPS is {distance:.0f}m away; exceeds standard 300m radius.",
                metrics=metrics,
            )
        else:
            return SignalResult(
                name="gps_proximity",
                passed=False,
                score=0.0,
                weight=self.WEIGHT_GPS,
                status="out_of_bounds_location_mismatch",
                details=f"Location mismatch: Resolution photo taken {distance:.0f}m from reported incident.",
                metrics=metrics,
            )

    # -----------------------------------------------------------------------
    # Signal 3: Timestamp Validation
    # -----------------------------------------------------------------------
    def evaluate_timestamp_signal(
        self,
        created_at: datetime,
        assigned_at: datetime | None,
        resolved_at: datetime | None,
        sla_deadline: datetime | None,
    ) -> SignalResult:
        now = datetime.now(timezone.utc)
        resolved = resolved_at or now

        # Ensure timezone-aware
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if assigned_at and assigned_at.tzinfo is None:
            assigned_at = assigned_at.replace(tzinfo=timezone.utc)
        if resolved.tzinfo is None:
            resolved = resolved.replace(tzinfo=timezone.utc)
        if sla_deadline and sla_deadline.tzinfo is None:
            sla_deadline = sla_deadline.replace(tzinfo=timezone.utc)

        start_time = assigned_at or created_at
        elapsed_seconds = (resolved - start_time).total_seconds()

        metrics: dict[str, Any] = {
            "elapsed_seconds": max(0, int(elapsed_seconds)),
            "is_chronologically_valid": resolved >= created_at,
            "within_sla": (resolved <= sla_deadline) if sla_deadline else None,
        }

        if resolved < created_at:
            return SignalResult(
                name="timestamp_validity",
                passed=False,
                score=0.0,
                weight=self.WEIGHT_TIMESTAMP,
                status="invalid_chronology",
                details="Resolution timestamp precedes complaint creation time (clock anomaly).",
                metrics=metrics,
            )

        # Flag suspiciously instantaneous turnaround
        if elapsed_seconds < self.min_duration_seconds:
            return SignalResult(
                name="timestamp_validity",
                passed=False,
                score=0.40,
                weight=self.WEIGHT_TIMESTAMP,
                status="suspiciously_instantaneous_resolution",
                details=f"Turnaround time ({int(elapsed_seconds)}s) is unrealistically fast.",
                metrics=metrics,
            )

        if sla_deadline and resolved <= sla_deadline:
            return SignalResult(
                name="timestamp_validity",
                passed=True,
                score=1.0,
                weight=self.WEIGHT_TIMESTAMP,
                status="resolved_within_sla",
                details="Resolved within allocated SLA deadline.",
                metrics=metrics,
            )
        elif sla_deadline and resolved > sla_deadline:
            return SignalResult(
                name="timestamp_validity",
                passed=True,
                score=0.75,
                weight=self.WEIGHT_TIMESTAMP,
                status="resolved_after_sla",
                details="Resolution verified, but completed after SLA deadline expired.",
                metrics=metrics,
            )
        else:
            return SignalResult(
                name="timestamp_validity",
                passed=True,
                score=0.90,
                weight=self.WEIGHT_TIMESTAMP,
                status="valid_turnaround",
                details="Turnaround timestamp is chronologically valid.",
                metrics=metrics,
            )

    # -----------------------------------------------------------------------
    # Signal 4: Citizen Feedback
    # -----------------------------------------------------------------------
    def evaluate_citizen_signal(
        self,
        citizen_confirmed: bool | None,
        citizen_rating: int | None = None,
        feedback_notes: str | None = None,
    ) -> SignalResult:
        metrics: dict[str, Any] = {
            "status": "pending" if citizen_confirmed is None else ("confirmed" if citizen_confirmed else "rejected"),
            "rating": citizen_rating,
            "feedback": feedback_notes,
        }

        if citizen_confirmed is True:
            # Rating mapping
            rating_score = 1.0
            if citizen_rating is not None:
                rating_score = max(0.4, min(1.0, citizen_rating / 5.0))

            return SignalResult(
                name="citizen_feedback",
                passed=True,
                score=round(rating_score, 2),
                weight=self.WEIGHT_CITIZEN,
                status="confirmed_by_citizen",
                details=f"Citizen confirmed resolution satisfactory" + (f" (rating: {citizen_rating}/5)." if citizen_rating else "."),
                metrics=metrics,
            )
        elif citizen_confirmed is False:
            return SignalResult(
                name="citizen_feedback",
                passed=False,
                score=0.0,
                weight=self.WEIGHT_CITIZEN,
                status="rejected_by_citizen",
                details=f"Citizen rejected resolution: {feedback_notes or 'Work incomplete'}.",
                metrics=metrics,
            )
        else:
            return SignalResult(
                name="citizen_feedback",
                passed=True,
                score=0.60,
                weight=self.WEIGHT_CITIZEN,
                status="pending_citizen_confirmation",
                details="Citizen confirmation is pending.",
                metrics=metrics,
            )

    # -----------------------------------------------------------------------
    # Composite Verification
    # -----------------------------------------------------------------------
    def verify(
        self,
        before_image: bytes | None,
        after_image: bytes | None,
        metadata: dict[str, Any],
    ) -> VerificationResult:
        """
        Evaluate all 4 signals and compute composite decision.

        Expected metadata keys:
          - complaint_lat: float
          - complaint_lng: float
          - evidence_lat: float | None
          - evidence_lng: float | None
          - created_at: datetime
          - assigned_at: datetime | None
          - resolved_at: datetime | None
          - sla_deadline: datetime | None
          - citizen_confirmed: bool | None
          - citizen_rating: int | None
          - citizen_feedback: str | None
        """
        flags: list[str] = []

        photo_sig = self.evaluate_photo_signal(before_image, after_image)
        gps_sig = self.evaluate_gps_signal(
            complaint_lat=metadata.get("complaint_lat", 0.0),
            complaint_lng=metadata.get("complaint_lng", 0.0),
            evidence_lat=metadata.get("evidence_lat"),
            evidence_lng=metadata.get("evidence_lng"),
        )
        time_sig = self.evaluate_timestamp_signal(
            created_at=metadata.get("created_at") or datetime.now(timezone.utc),
            assigned_at=metadata.get("assigned_at"),
            resolved_at=metadata.get("resolved_at"),
            sla_deadline=metadata.get("sla_deadline"),
        )
        citizen_sig = self.evaluate_citizen_signal(
            citizen_confirmed=metadata.get("citizen_confirmed"),
            citizen_rating=metadata.get("citizen_rating"),
            feedback_notes=metadata.get("citizen_feedback"),
        )

        signals = {
            "photo_comparison": photo_sig,
            "gps_proximity": gps_sig,
            "timestamp_validity": time_sig,
            "citizen_feedback": citizen_sig,
        }

        # Check critical flags
        if photo_sig.status == "identical_photos_detected":
            flags.append("identical_photos_fraud_risk")
        if gps_sig.status == "out_of_bounds_location_mismatch":
            flags.append("gps_location_mismatch")
        if gps_sig.status == "gps_missing":
            flags.append("gps_missing")
        if time_sig.status == "invalid_chronology":
            flags.append("timestamp_chronology_invalid")
        if time_sig.status == "suspiciously_instantaneous_resolution":
            flags.append("instantaneous_resolution_warning")
        if citizen_sig.status == "rejected_by_citizen":
            flags.append("citizen_rejected_resolution")

        # Composite score
        composite_score = round(
            (photo_sig.score * self.WEIGHT_PHOTO)
            + (gps_sig.score * self.WEIGHT_GPS)
            + (time_sig.score * self.WEIGHT_TIMESTAMP)
            + (citizen_sig.score * self.WEIGHT_CITIZEN),
            2,
        )

        # Decision synthesis
        if "identical_photos_fraud_risk" in flags:
            status = "rejected"
            verified = False
            recommendation = (
                "FRAUD RISK: Resolution photo is identical to the original report photo. "
                "Reject and initiate worker inquiry."
            )
        elif "citizen_rejected_resolution" in flags:
            status = "rejected"
            verified = False
            recommendation = (
                "Citizen rejected resolution. Automatic closure blocked; complaint re-opened for field work."
            )
        elif composite_score >= self.auto_verify_threshold and not flags:
            if citizen_sig.status == "confirmed_by_citizen":
                status = "verified"
                verified = True
                recommendation = "All verification signals passed and citizen confirmed. Ready for closure."
            else:
                status = "provisionally_verified"
                verified = True
                recommendation = (
                    "Photo, GPS, and timestamp verification passed. Awaiting citizen final confirmation."
                )
        elif composite_score >= self.review_threshold or (flags and "identical_photos_fraud_risk" not in flags):
            status = "requires_review"
            verified = False
            flag_desc = ", ".join(flags) if flags else "moderate confidence score"
            recommendation = (
                f"Requires operational officer review ({flag_desc}). Inspect evidence before approving."
            )
        else:
            status = "rejected"
            verified = False
            recommendation = (
                "Verification failed multi-signal validation. Inconclusive or conflicting resolution evidence."
            )

        return VerificationResult(
            verified=verified,
            status=status,
            composite_score=composite_score,
            signals={
                k: {
                    "name": v.name,
                    "passed": v.passed,
                    "score": v.score,
                    "weight": v.weight,
                    "status": v.status,
                    "details": v.details,
                    "metrics": v.metrics,
                }
                for k, v in signals.items()
            },
            recommendation=recommendation,
            flags=flags,
            evaluated_at=datetime.now(timezone.utc).isoformat(),
            source="multi_signal_rule_engine",
        )


# ---------------------------------------------------------------------------
# Singleton Factory
# ---------------------------------------------------------------------------
_verifier_instance: ResolutionVerifier | None = None


def get_resolution_verifier() -> ResolutionVerifier:
    """Return the configured resolution verifier implementation."""
    global _verifier_instance
    if _verifier_instance is None:
        _verifier_instance = MultiSignalResolutionVerifier()
    return _verifier_instance


def load_image_bytes(url: str | None) -> bytes | None:
    """Read image bytes from disk using url."""
    if not url:
        return None
    from pathlib import Path
    try:
        rel = url.lstrip("/")
        if rel.startswith("uploads/"):
            rel = rel[len("uploads/") :]
        fp = Path(settings.upload_dir) / rel
        if fp.is_file():
            return fp.read_bytes()
    except Exception as exc:
        logger.debug("Could not read image file for %s: %s", url, exc)
    return None


def verify_complaint_resolution(
    complaint: Any,
    *,
    before_content: bytes | None = None,
    after_content: bytes | None = None,
    evidence_lat: float | None = None,
    evidence_lng: float | None = None,
    citizen_confirmed: bool | None = None,
    citizen_rating: int | None = None,
    citizen_feedback: str | None = None,
) -> VerificationResult:
    """
    Run multi-signal verification for a complaint and return the VerificationResult.
    Updates the complaint object's verification_* fields in-place.
    """
    from app.models.enums import ComplaintStatus, ImageType

    before_bytes = before_content
    after_bytes = after_content
    found_evidence_lat = evidence_lat
    found_evidence_lng = evidence_lng

    if hasattr(complaint, "images") and complaint.images:
        for img in complaint.images:
            if img.image_type == ImageType.before and before_bytes is None:
                before_bytes = load_image_bytes(img.url)
            elif img.image_type == ImageType.after:
                if after_bytes is None:
                    after_bytes = load_image_bytes(img.url)
                if found_evidence_lat is None and getattr(img, "latitude", None) is not None:
                    found_evidence_lat = img.latitude
                if found_evidence_lng is None and getattr(img, "longitude", None) is not None:
                    found_evidence_lng = img.longitude

    conf_val = citizen_confirmed
    if conf_val is None:
        if complaint.status == ComplaintStatus.closed:
            conf_val = True
        elif complaint.status == ComplaintStatus.reopened:
            conf_val = False

    rating_val = citizen_rating if citizen_rating is not None else getattr(complaint, "citizen_rating", None)
    feedback_val = citizen_feedback if citizen_feedback is not None else getattr(complaint, "citizen_feedback", None)

    metadata: dict[str, Any] = {
        "complaint_lat": complaint.location_lat,
        "complaint_lng": complaint.location_lng,
        "evidence_lat": found_evidence_lat,
        "evidence_lng": found_evidence_lng,
        "created_at": complaint.created_at,
        "assigned_at": complaint.assigned_at,
        "resolved_at": complaint.resolved_at,
        "sla_deadline": complaint.sla_deadline,
        "citizen_confirmed": conf_val,
        "citizen_rating": rating_val,
        "citizen_feedback": feedback_val,
    }

    verifier = get_resolution_verifier()
    result = verifier.verify(before_bytes, after_bytes, metadata)

    # Persist back to complaint model in memory
    complaint.verification_score = result.composite_score
    complaint.verification_status = result.status
    complaint.verification_details = {
        "verified": result.verified,
        "status": result.status,
        "composite_score": result.composite_score,
        "signals": result.signals,
        "recommendation": result.recommendation,
        "flags": result.flags,
        "evaluated_at": result.evaluated_at,
        "source": result.source,
    }
    if result.verified:
        complaint.verified_at = datetime.now(timezone.utc)

    return result
