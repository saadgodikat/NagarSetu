"""
Train NagarIQ Phase 3 SLA Breach Probability Predictor.

Model: GradientBoostingClassifier (sklearn) – outputs calibrated breach probability.
Features: category (OHE), severity_ordinal, priority_score, hours_since_submission,
          hours_since_status_change, related_count, assigned, department_id,
          sla_deadline_hours, is_safety_risk.

Outputs:
  backend/models/sla_breach_predictor_v1.joblib
  ML_SLA_PREDICTION_REPORT.md (appended)

Usage:
    python scripts/ml_training/train_sla_model.py \
        --data scripts/ml_training/data/sla_dataset.csv \
        --out backend/models/sla_breach_predictor_v1.joblib
"""

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    classification_report,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer

CATEGORICAL_FEATURES = ["category"]
ORDINAL_FEATURES = [
    "severity_ordinal",
    "priority_score",
    "hours_since_submission",
    "hours_since_status_change",
    "related_count",
    "assigned",
    "department_id",
    "sla_deadline_hours",
    "is_safety_risk",
]
ALL_FEATURES = CATEGORICAL_FEATURES + ORDINAL_FEATURES
TARGET = "breach"


def build_pipeline() -> Pipeline:
    ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", ohe, CATEGORICAL_FEATURES),
            ("num", "passthrough", ORDINAL_FEATURES),
        ]
    )
    gbt = GradientBoostingClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.85,
        min_samples_leaf=10,
        random_state=42,
    )
    # Isotonic calibration gives well-calibrated probabilities
    calibrated = CalibratedClassifierCV(gbt, cv=3, method="isotonic")
    return Pipeline([("prep", preprocessor), ("clf", calibrated)])


def main() -> None:
    parser = argparse.ArgumentParser(description="Train SLA breach predictor")
    parser.add_argument(
        "--data",
        default="scripts/ml_training/data/sla_dataset.csv",
        help="Path to CSV training data",
    )
    parser.add_argument(
        "--out",
        default="backend/models/sla_breach_predictor_v1.joblib",
        help="Output model path",
    )
    args = parser.parse_args()

    data_path = Path(args.data)
    out_path = Path(args.out)

    if not data_path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {data_path}. "
            "Run generate_sla_dataset.py first."
        )

    df = pd.read_csv(data_path)
    print(f"Loaded {len(df)} samples from {data_path}")
    print(f"  Breach rate: {df[TARGET].mean()*100:.1f}%")

    X = df[ALL_FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=42
    )
    print(f"  Train: {len(X_train)}  Test: {len(X_test)}")

    pipeline = build_pipeline()

    # Cross-validation
    print("\nRunning 5-fold cross-validation (ROC-AUC)...")
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(pipeline, X_train, y_train, cv=skf, scoring="roc_auc")
    print(f"  CV ROC-AUC: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # Final fit
    pipeline.fit(X_train, y_train)

    # Evaluation
    y_prob = pipeline.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.50).astype(int)

    roc_auc = roc_auc_score(y_test, y_prob)
    avg_prec = average_precision_score(y_test, y_prob)
    brier = brier_score_loss(y_test, y_prob)

    print("\n=== Test Set Evaluation ===")
    print(f"  ROC-AUC:            {roc_auc:.4f}")
    print(f"  Average Precision:  {avg_prec:.4f}")
    print(f"  Brier Score Loss:   {brier:.4f}  (lower = better calibration)")
    print("\nClassification Report (threshold=0.50):")
    print(classification_report(y_test, y_pred, target_names=["no_breach", "breach"]))

    # Feature importance (from GBT inside the calibrated wrapper)
    try:
        ohe_cols = list(
            pipeline.named_steps["prep"]
            .named_transformers_["cat"]
            .get_feature_names_out(CATEGORICAL_FEATURES)
        )
        feature_names = ohe_cols + ORDINAL_FEATURES
        # Pull the base estimator from CalibratedClassifierCV
        base_estimators = pipeline.named_steps["clf"].calibrated_classifiers_
        importances = np.mean(
            [est.estimator.feature_importances_ for est in base_estimators], axis=0
        )
        fi = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)
        print("\nTop-10 Feature Importances:")
        for name, imp in fi[:10]:
            print(f"  {name:<35s} {imp:.4f}")
    except Exception as e:
        print(f"  (Could not extract feature importances: {e})")
        fi = []

    # Save artifact
    out_path.parent.mkdir(parents=True, exist_ok=True)
    artifact = {
        "pipeline": pipeline,
        "model_version": "sla_breach_v1.0.0",
        "feature_names": ALL_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "ordinal_features": ORDINAL_FEATURES,
        "threshold": 0.50,
        "metrics": {
            "roc_auc": round(roc_auc, 4),
            "avg_precision": round(avg_prec, 4),
            "brier_score": round(brier, 4),
            "cv_roc_auc_mean": round(float(cv_scores.mean()), 4),
            "cv_roc_auc_std": round(float(cv_scores.std()), 4),
        },
        "feature_importances": {name: round(float(imp), 4) for name, imp in fi},
    }
    joblib.dump(artifact, out_path)
    print(f"\nModel saved -> {out_path}")


if __name__ == "__main__":
    main()
