"""
Generate synthetic SLA breach training data for NagarIQ Phase 3.

Features used:
  - category (one-hot encoded)
  - severity (ordinal: LOW=1, MEDIUM=2, HIGH=3, CRITICAL=4)
  - priority_score (0-100)
  - hours_since_submission (age of complaint)
  - hours_since_status_change
  - related_count (duplicate/related complaint count)
  - assigned (bool: 1 if assigned to an officer)
  - department_id (int)
  - sla_deadline_hours (SLA window in hours from submission)
  - is_safety_risk (bool)

Label:
  - breach (1 = SLA was/will be breached, 0 = resolved within SLA)

Usage:
    python scripts/ml_training/generate_sla_dataset.py --out scripts/ml_training/data/sla_dataset.csv
"""

import argparse
import random
import csv
from pathlib import Path

SEED = 42
random.seed(SEED)

CATEGORIES = ["pothole", "garbage", "drainage", "streetlight", "water_leakage", "other"]
SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
SEVERITY_ORD = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

# Department IDs from seed data
DEPARTMENTS = [1, 2, 3, 4, 5, 6, 7]

# SLA windows per department (hours) – approximates DB SlaPolicy data
SLA_HOURS = {1: 48, 2: 72, 3: 48, 4: 24, 5: 24, 6: 96, 7: 72}

# Historical breach rate parameters per severity (affects whether breach happens)
BREACH_BASE_RATE = {"LOW": 0.12, "MEDIUM": 0.28, "HIGH": 0.52, "CRITICAL": 0.70}


def generate_sample(i: int) -> dict:
    category = random.choice(CATEGORIES)
    severity = random.choices(
        SEVERITIES, weights=[35, 40, 18, 7], k=1
    )[0]
    dept_id = DEPARTMENTS[CATEGORIES.index(category)] if category != "other" else 7
    sla_hours = SLA_HOURS[dept_id]

    hours_since_submission = random.uniform(0, sla_hours * 1.8)
    hours_since_status_change = random.uniform(0, min(hours_since_submission, sla_hours))
    related_count = random.choices([0, 1, 2, 3, 4, 5], weights=[60, 20, 10, 5, 3, 2])[0]
    assigned = random.choices([0, 1], weights=[30, 70])[0]
    is_safety_risk = 1 if severity in ("HIGH", "CRITICAL") and random.random() < 0.6 else 0
    priority_score = min(
        100,
        SEVERITY_ORD[severity] * 15
        + related_count * 8
        + (25 if is_safety_risk else 0)
        + random.randint(0, 10),
    )

    # Breach probability model (ground truth label generation)
    base_p = BREACH_BASE_RATE[severity]
    # Older complaints more likely to breach
    age_factor = min(1.0, hours_since_submission / sla_hours)
    # Unassigned = higher breach risk
    assign_factor = 0.25 if not assigned else 0.0
    # Related count boosts breach risk
    related_factor = min(0.2, related_count * 0.04)
    # Safety risk boosts breach chance
    safety_factor = 0.15 if is_safety_risk else 0.0

    p_breach = min(0.97, base_p + age_factor * 0.4 + assign_factor + related_factor + safety_factor)
    breach = 1 if random.random() < p_breach else 0

    return {
        "id": i,
        "category": category,
        "severity": severity,
        "severity_ordinal": SEVERITY_ORD[severity],
        "priority_score": priority_score,
        "hours_since_submission": round(hours_since_submission, 2),
        "hours_since_status_change": round(hours_since_status_change, 2),
        "related_count": related_count,
        "assigned": assigned,
        "department_id": dept_id,
        "sla_deadline_hours": sla_hours,
        "is_safety_risk": is_safety_risk,
        "breach": breach,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SLA breach training dataset")
    parser.add_argument("--n", type=int, default=6000, help="Number of samples (default: 6000)")
    parser.add_argument(
        "--out",
        type=str,
        default="scripts/ml_training/data/sla_dataset.csv",
        help="Output CSV path",
    )
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    samples = [generate_sample(i) for i in range(args.n)]
    fieldnames = list(samples[0].keys())

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(samples)

    breach_count = sum(s["breach"] for s in samples)
    print(f"Generated {args.n} samples -> {out_path}")
    print(f"  Breach: {breach_count} ({breach_count/args.n*100:.1f}%)")
    print(f"  No-breach: {args.n - breach_count} ({(args.n-breach_count)/args.n*100:.1f}%)")


if __name__ == "__main__":
    main()
