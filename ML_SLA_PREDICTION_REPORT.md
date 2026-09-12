# NagarIQ – Phase 3: Dynamic Severity & Priority ML
## SLA Breach Probability Prediction & Adaptive Escalation

---

## 1. Objective

Predict the probability that an active complaint will breach its SLA deadline,
and automatically assign an adaptive escalation level so operations staff can
triage high-risk cases before they expire.

---

## 2. Architecture

Complaint submitted / SLA sweep
          |
          v
  extract_sla_features()
  (app/ai/sla_predictor.py)
          |
          v
  get_sla_predictor()
  [SLA_BREACH_ML_ENABLED=True] -> GBTSLABreachPredictor (GBT + isotonic)
  [default: False]             -> RuleBasedSLABreachPredictor (fallback)
          |
          v
  SLAPrediction
   breach_probability: float [0,1]
   escalation_level: none | watch | escalate | critical
          |
          v
  Stamped onto complaints table
  (breach_probability, escalation_level, sla_predicted_at)

---

## 3. Features

| Feature                    | Type           | Description                                   |
|----------------------------|----------------|-----------------------------------------------|
| category                   | categorical    | Complaint category (garbage, pothole, etc.)   |
| severity_ordinal           | int [1-4]      | LOW=1, MEDIUM=2, HIGH=3, CRITICAL=4           |
| priority_score             | int [0-100]    | Priority score from Phase 1 rule engine       |
| hours_since_submission     | float          | Age of complaint in hours                     |
| hours_since_status_change  | float          | Time since last status transition             |
| related_count              | int            | Count of related/duplicate complaints         |
| assigned                   | binary         | 1 if assigned to a field worker               |
| department_id              | int            | Assigned department                           |
| sla_deadline_hours         | float          | SLA window duration in hours                  |
| is_safety_risk             | binary         | 1 if severity is HIGH/CRITICAL                |

---

## 4. Model

Algorithm: GradientBoostingClassifier (sklearn) + CalibratedClassifierCV (isotonic)
n_estimators=200, max_depth=4, learning_rate=0.08, subsample=0.85

---

## 5. Training Results

| Metric                    | Value  |
|---------------------------|--------|
| CV ROC-AUC (5-fold)       | 0.7558 |
| Test ROC-AUC              | 0.7935 |
| Test Average Precision    | 0.8926 |
| Brier Score Loss          | 0.1687 |

---

## 6. Feature Importances (Top 10)

| Feature                    | Importance |
|----------------------------|------------|
| hours_since_submission     | 0.3128     |
| priority_score             | 0.2188     |
| hours_since_status_change  | 0.1846     |
| assigned                   | 0.1031     |
| severity_ordinal           | 0.1019     |
| sla_deadline_hours         | 0.0220     |
| department_id              | 0.0205     |
| related_count              | 0.0128     |
| category_streetlight       | 0.0084     |
| category_garbage           | 0.0042     |

---

## 7. Escalation Levels

| breach_probability | escalation_level |
|--------------------|------------------|
| >= 0.80            | critical         |
| 0.60 - 0.79        | escalate         |
| 0.35 - 0.59        | watch            |
| < 0.35             | none             |

---

## 8. API Endpoints

POST /api/v1/operations/complaints/{id}/sla-prediction  (on-demand refresh)
GET  /api/v1/operations/sla/high-risk?threshold=0.6     (high-risk list)

---

## 9. Tests

26 tests pass (19 new + 7 existing L1 rules)

---

## 10. Files Changed

backend/app/ai/sla_predictor.py           NEW
backend/app/models/complaint.py           +3 columns
backend/app/config.py                     +2 flags
backend/app/complaints/service.py         SLA prediction on submission
backend/app/sla/service.py                refresh in SLA sweep
backend/app/schemas/complaints.py         +3 fields + SLAPredictionOut
backend/app/api/v1/operations.py          +2 endpoints
backend/alembic/versions/0002_sla_ml_columns.py  NEW migration
backend/tests/test_sla_predictor.py       NEW 19 tests
scripts/ml_training/generate_sla_dataset.py  NEW
scripts/ml_training/train_sla_model.py   NEW
backend/models/sla_breach_predictor_v1.joblib  NEW artifact
