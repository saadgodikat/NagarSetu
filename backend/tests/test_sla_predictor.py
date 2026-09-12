"""
Unit tests for Phase 3 – SLA Breach Predictor.

Tests cover:
  - Feature extraction (extract_sla_features)
  - Escalation level mapping
  - RuleBasedSLABreachPredictor (no model required)
  - GBTSLABreachPredictor fallback behaviour (model file absent)
  - get_sla_predictor factory (flag disabled → rule-based)
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.ai.sla_predictor import (
    GBTSLABreachPredictor,
    RuleBasedSLABreachPredictor,
    SLAFeatures,
    breach_probability_to_escalation,
    extract_sla_features,
    get_sla_predictor,
)
from app.models.enums import ComplaintCategory, Severity

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
NOW = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
CREATED_6H_AGO = NOW - timedelta(hours=6)
CREATED_50H_AGO = NOW - timedelta(hours=50)


def _features(**kwargs) -> SLAFeatures:
    defaults = dict(
        category="garbage",
        severity_ordinal=2,
        priority_score=30,
        hours_since_submission=6.0,
        hours_since_status_change=4.0,
        related_count=0,
        assigned=1,
        department_id=1,
        sla_deadline_hours=48.0,
        is_safety_risk=0,
    )
    defaults.update(kwargs)
    return SLAFeatures(**defaults)


# ---------------------------------------------------------------------------
# Escalation level mapping
# ---------------------------------------------------------------------------
class TestBreachProbabilityToEscalation:
    def test_critical_at_80(self):
        assert breach_probability_to_escalation(0.80) == "critical"

    def test_critical_above_80(self):
        assert breach_probability_to_escalation(0.95) == "critical"

    def test_escalate_between_60_and_80(self):
        assert breach_probability_to_escalation(0.70) == "escalate"

    def test_watch_between_35_and_60(self):
        assert breach_probability_to_escalation(0.50) == "watch"

    def test_none_below_35(self):
        assert breach_probability_to_escalation(0.10) == "none"

    def test_exact_boundary_60(self):
        assert breach_probability_to_escalation(0.60) == "escalate"

    def test_exact_boundary_35(self):
        assert breach_probability_to_escalation(0.35) == "watch"


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------
class TestExtractSLAFeatures:
    def test_basic_extraction(self):
        f = extract_sla_features(
            category=ComplaintCategory.garbage,
            severity=Severity.HIGH,
            priority_score=60,
            created_at=CREATED_6H_AGO,
            status_changed_at=CREATED_6H_AGO,
            related_count=2,
            assigned_to="some-uuid",
            assigned_department_id=1,
            sla_deadline=None,
            now=NOW,
        )
        assert f.category == "garbage"
        assert f.severity_ordinal == 3  # HIGH
        assert f.priority_score == 60
        assert 5.9 <= f.hours_since_submission <= 6.1
        assert f.related_count == 2
        assert f.assigned == 1
        assert f.department_id == 1
        assert f.sla_deadline_hours == 48.0  # default for dept 1
        assert f.is_safety_risk == 1  # HIGH severity

    def test_unassigned_maps_to_zero(self):
        f = extract_sla_features(
            category=ComplaintCategory.pothole,
            severity=Severity.LOW,
            priority_score=10,
            created_at=CREATED_6H_AGO,
            status_changed_at=None,
            related_count=0,
            assigned_to=None,
            assigned_department_id=None,
            sla_deadline=None,
            now=NOW,
        )
        assert f.assigned == 0
        assert f.is_safety_risk == 0
        assert f.department_id == 7  # falls back to default dept

    def test_sla_deadline_overrides_dept_default(self):
        sla = CREATED_6H_AGO + timedelta(hours=24)
        f = extract_sla_features(
            category=ComplaintCategory.streetlight,
            severity=Severity.MEDIUM,
            priority_score=20,
            created_at=CREATED_6H_AGO,
            status_changed_at=None,
            related_count=0,
            assigned_to=None,
            assigned_department_id=4,
            sla_deadline=sla,
            now=NOW,
        )
        assert abs(f.sla_deadline_hours - 24.0) < 0.1

    def test_future_status_change_clamps_to_zero(self):
        future = NOW + timedelta(hours=2)
        f = extract_sla_features(
            category=ComplaintCategory.drainage,
            severity=Severity.MEDIUM,
            priority_score=20,
            created_at=CREATED_6H_AGO,
            status_changed_at=future,
            related_count=0,
            assigned_to=None,
            assigned_department_id=3,
            sla_deadline=None,
            now=NOW,
        )
        assert f.hours_since_status_change == 0.0

    def test_to_dict_matches_feature_names(self):
        f = _features()
        d = f.to_dict()
        expected_keys = {
            "category", "severity_ordinal", "priority_score",
            "hours_since_submission", "hours_since_status_change",
            "related_count", "assigned", "department_id",
            "sla_deadline_hours", "is_safety_risk",
        }
        assert set(d.keys()) == expected_keys


# ---------------------------------------------------------------------------
# Rule-based predictor
# ---------------------------------------------------------------------------
class TestRuleBasedSLABreachPredictor:
    def setup_method(self):
        self.predictor = RuleBasedSLABreachPredictor()

    def test_new_assigned_low_severity_low_risk(self):
        f = _features(hours_since_submission=1.0, severity_ordinal=1, assigned=1, sla_deadline_hours=48.0)
        pred = self.predictor.predict(f)
        assert pred.breach_probability < 0.35
        assert pred.escalation_level == "none"
        assert pred.source == "rule_based"

    def test_old_unassigned_high_severity_high_risk(self):
        f = _features(
            hours_since_submission=45.0,
            severity_ordinal=3,
            assigned=0,
            sla_deadline_hours=48.0,
            is_safety_risk=1,
            related_count=4,
        )
        pred = self.predictor.predict(f)
        assert pred.breach_probability >= 0.60
        assert pred.escalation_level in ("escalate", "critical")
        assert len(pred.confidence_reasons) > 0

    def test_probability_bounded_0_to_1(self):
        f = _features(
            hours_since_submission=1000.0,
            severity_ordinal=4,
            assigned=0,
            is_safety_risk=1,
            related_count=10,
        )
        pred = self.predictor.predict(f)
        assert 0.0 <= pred.breach_probability <= 1.0

    def test_predicted_at_is_recent(self):
        f = _features()
        pred = self.predictor.predict(f)
        age = (datetime.now(timezone.utc) - pred.predicted_at).total_seconds()
        assert age < 5.0  # within 5 seconds


# ---------------------------------------------------------------------------
# GBT predictor – fallback when model file is absent
# ---------------------------------------------------------------------------
class TestGBTSLABreachPredictorFallback:
    def test_falls_back_to_rule_based_when_model_missing(self):
        with patch("app.config.settings") as mock_settings:
            mock_settings.sla_breach_model_path = "/nonexistent/path/model.joblib"
            mock_settings.sla_breach_ml_enabled = True
            predictor = GBTSLABreachPredictor(model_path="/nonexistent/path/model.joblib")
            assert predictor._pipeline is None

        # Should still produce a valid prediction via fallback
        f = _features()
        pred = predictor.predict(f)
        assert 0.0 <= pred.breach_probability <= 1.0
        assert pred.escalation_level in ("none", "watch", "escalate", "critical")

    def test_fallback_source_indicates_unavailability(self):
        predictor = GBTSLABreachPredictor(model_path="/nonexistent/model.joblib")
        f = _features()
        pred = predictor.predict(f)
        assert "fallback" in pred.source or pred.source == "rule_based"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
class TestGetSlaPredictor:
    def test_returns_rule_based_when_disabled(self):
        import app.ai.sla_predictor as mod
        original = mod._predictor_instance
        mod._predictor_instance = None
        try:
            with patch("app.config.settings") as mock_settings:
                mock_settings.sla_breach_ml_enabled = False
                mock_settings.sla_breach_model_path = "nonexistent.joblib"
                p = get_sla_predictor()
            assert isinstance(p, RuleBasedSLABreachPredictor)
        finally:
            mod._predictor_instance = original
