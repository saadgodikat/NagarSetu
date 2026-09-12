"""
SLA Breach Predictor – NagarIQ Phase 3.

Provides a replaceable interface for SLA breach probability prediction and
adaptive escalation level recommendation.

Architecture:
  - SLAFeatures: dataclass representing the feature vector
  - SLAPrediction: dataclass for the output
  - SLABreachPredictor: abstract base class (replaceable interface)
  - GBTSLABreachPredictor: GradientBoosting implementation backed by joblib artifact
  - RuleBasedSLABreachPredictor: deterministic fallback (no model required)
  - get_sla_predictor(): factory – returns enabled implementation

Feature flags (config.py):
  - sla_breach_ml_enabled: bool  (default False → uses rule-based fallback)
  - sla_breach_model_path: str
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from app.models.enums import ComplaintCategory, ComplaintStatus, Severity

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Escalation levels
# ---------------------------------------------------------------------------
EscalationLevel = Literal["none", "watch", "escalate", "critical"]

_ESCALATION_THRESHOLDS: list[tuple[float, EscalationLevel]] = [
    (0.80, "critical"),
    (0.60, "escalate"),
    (0.35, "watch"),
    (0.0, "none"),
]


def breach_probability_to_escalation(probability: float) -> EscalationLevel:
    """Map breach probability [0, 1] to an escalation level string."""
    for threshold, level in _ESCALATION_THRESHOLDS:
        if probability >= threshold:
            return level
    return "none"


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------
_SEVERITY_ORD = {
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}

_SLA_HOURS_BY_DEPT: dict[int, float] = {
    1: 48.0,
    2: 72.0,
    3: 48.0,
    4: 24.0,
    5: 24.0,
    6: 96.0,
    7: 72.0,
}
_DEFAULT_SLA_HOURS = 72.0


@dataclass(frozen=True)
class SLAFeatures:
    category: str
    severity_ordinal: int
    priority_score: int
    hours_since_submission: float
    hours_since_status_change: float
    related_count: int
    assigned: int  # 0 or 1
    department_id: int
    sla_deadline_hours: float
    is_safety_risk: int  # 0 or 1

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "severity_ordinal": self.severity_ordinal,
            "priority_score": self.priority_score,
            "hours_since_submission": self.hours_since_submission,
            "hours_since_status_change": self.hours_since_status_change,
            "related_count": self.related_count,
            "assigned": self.assigned,
            "department_id": self.department_id,
            "sla_deadline_hours": self.sla_deadline_hours,
            "is_safety_risk": self.is_safety_risk,
        }


def extract_sla_features(
    *,
    category: ComplaintCategory,
    severity: Severity,
    priority_score: int | None,
    created_at: datetime,
    status_changed_at: datetime | None,
    related_count: int,
    assigned_to: object | None,
    assigned_department_id: int | None,
    sla_deadline: datetime | None,
    now: datetime | None = None,
) -> SLAFeatures:
    """Build an SLAFeatures dataclass from a Complaint's current state."""
    now = now or datetime.now(timezone.utc)

    def _hours(dt: datetime | None) -> float:
        if dt is None:
            return 0.0
        # Make both timezone-aware if needed
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = now - dt
        return max(0.0, delta.total_seconds() / 3600)

    dept_id = assigned_department_id or 7
    sla_hours = _SLA_HOURS_BY_DEPT.get(dept_id, _DEFAULT_SLA_HOURS)
    if sla_deadline is not None:
        # Use actual SLA deadline if set
        if sla_deadline.tzinfo is None:
            sla_deadline = sla_deadline.replace(tzinfo=timezone.utc)
        delta_to_deadline = (sla_deadline - created_at).total_seconds() / 3600
        sla_hours = max(1.0, delta_to_deadline)

    sev = severity if isinstance(severity, Severity) else Severity(severity)
    is_safety = 1 if sev in (Severity.HIGH, Severity.CRITICAL) else 0

    return SLAFeatures(
        category=category.value if isinstance(category, ComplaintCategory) else category,
        severity_ordinal=_SEVERITY_ORD.get(sev, 2),
        priority_score=priority_score or 20,
        hours_since_submission=_hours(created_at),
        hours_since_status_change=_hours(status_changed_at),
        related_count=related_count,
        assigned=1 if assigned_to is not None else 0,
        department_id=dept_id,
        sla_deadline_hours=sla_hours,
        is_safety_risk=is_safety,
    )


# ---------------------------------------------------------------------------
# Prediction output
# ---------------------------------------------------------------------------
@dataclass
class SLAPrediction:
    breach_probability: float
    escalation_level: EscalationLevel
    source: str
    confidence_reasons: list[str] = field(default_factory=list)
    predicted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------
class SLABreachPredictor:
    """Replaceable interface for SLA breach probability prediction."""

    def predict(self, features: SLAFeatures) -> SLAPrediction:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Rule-based fallback (no model required)
# ---------------------------------------------------------------------------
class RuleBasedSLABreachPredictor(SLABreachPredictor):
    """
    Deterministic fallback predictor.

    Uses age-fraction + severity + assignment state to produce a rough
    breach probability. No ML model is required.
    """

    def predict(self, features: SLAFeatures) -> SLAPrediction:
        reasons: list[str] = []

        age_fraction = min(
            1.0,
            features.hours_since_submission / max(1.0, features.sla_deadline_hours),
        )
        p = age_fraction * 0.50  # baseline: age drives up to 50%

        sev_boost = (features.severity_ordinal - 1) * 0.08  # 0..0.24
        p += sev_boost
        if features.severity_ordinal >= 3:
            reasons.append("High severity detected")

        if not features.assigned:
            p += 0.20
            reasons.append("Complaint not yet assigned")

        if features.related_count >= 3:
            p += 0.10
            reasons.append(f"{features.related_count} related complaints")

        if features.is_safety_risk:
            p += 0.10
            reasons.append("Public safety risk")

        p = float(min(0.97, max(0.0, p)))
        level = breach_probability_to_escalation(p)
        return SLAPrediction(
            breach_probability=round(p, 4),
            escalation_level=level,
            source="rule_based",
            confidence_reasons=reasons,
        )


# ---------------------------------------------------------------------------
# GBT ML predictor
# ---------------------------------------------------------------------------
class GBTSLABreachPredictor(SLABreachPredictor):
    """
    Gradient Boosting + isotonic calibration predictor.
    Falls back to RuleBasedSLABreachPredictor if model cannot be loaded.
    """

    def __init__(self, model_path: str | Path | None = None) -> None:
        from app.config import settings

        self._fallback = RuleBasedSLABreachPredictor()
        self._pipeline = None
        self._model_version = "gbt_sla_v1.0.0"
        self._threshold: float = 0.50
        self._load(Path(model_path or settings.sla_breach_model_path))

    def _load(self, path: Path) -> None:
        if not path.exists():
            alt = Path(__file__).resolve().parents[3] / path
            if alt.exists():
                path = alt
            else:
                logger.warning(
                    "SLA breach model not found at %s – using rule-based fallback.", path
                )
                return
        try:
            artifact = __import__("joblib").load(path)
            self._pipeline = artifact["pipeline"]
            self._model_version = artifact.get("model_version", self._model_version)
            self._threshold = artifact.get("threshold", self._threshold)
            logger.info("Loaded SLA breach predictor from %s", path)
        except Exception as exc:
            logger.error("Failed to load SLA breach model: %s", exc)

    def predict(self, features: SLAFeatures) -> SLAPrediction:
        if self._pipeline is None:
            pred = self._fallback.predict(features)
            pred.source = f"rule_based_fallback (model unavailable)"
            return pred

        try:
            import pandas as pd

            df = pd.DataFrame([features.to_dict()])
            proba = float(self._pipeline.predict_proba(df)[0, 1])
            level = breach_probability_to_escalation(proba)
            reasons: list[str] = []
            if proba >= 0.80:
                reasons.append("Model predicts very high breach risk")
            elif proba >= 0.60:
                reasons.append("Model predicts elevated breach risk")
            if features.severity_ordinal >= 3:
                reasons.append("High severity")
            if not features.assigned:
                reasons.append("Not yet assigned")
            return SLAPrediction(
                breach_probability=round(proba, 4),
                escalation_level=level,
                source=self._model_version,
                confidence_reasons=reasons,
            )
        except Exception as exc:
            logger.error("SLA breach prediction inference error: %s", exc)
            return self._fallback.predict(features)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
_predictor_instance: SLABreachPredictor | None = None


def get_sla_predictor() -> SLABreachPredictor:
    """Return the configured SLA breach predictor (singleton)."""
    global _predictor_instance
    if _predictor_instance is not None:
        return _predictor_instance

    from app.config import settings

    if settings.sla_breach_ml_enabled:
        _predictor_instance = GBTSLABreachPredictor()
    else:
        _predictor_instance = RuleBasedSLABreachPredictor()
        logger.info("SLA breach ML disabled – using rule-based predictor.")

    return _predictor_instance
