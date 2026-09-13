"""
Emerging crisis detection service.

Compares complaint volume in the current window vs the previous window
for each (category, ward) combination. Raises an alert only when the
percentage increase crosses a configurable threshold AND there is enough
historical data to make the comparison meaningful.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.complaint import Complaint
from app.models.enums import ComplaintCategory, ComplaintStatus
from app.models.org import Ward

TERMINAL = {ComplaintStatus.closed, ComplaintStatus.rejected}

# Configurable defaults
DEFAULT_WINDOW_HOURS = 24
DEFAULT_SPIKE_THRESHOLD_PCT = 100.0   # 100 % increase = double
DEFAULT_MIN_CURRENT_COUNT = 3         # need at least 3 in current window


@dataclass
class CrisisAlert:
    category: str
    ward_id: int | None
    ward_name: str
    current_count: int
    previous_count: int
    pct_increase: float
    open_count: int
    recommendation: str
    severity: str          # "warning" | "critical"


def _recommendation(category: str, open_count: int, pct: float) -> str:
    templates: dict[str, str] = {
        "garbage": "Deploy additional sanitation workers to clear the backlog.",
        "pothole": "Prioritise road repair crew deployment in this area.",
        "drainage": "Inspect and clear drainage infrastructure urgently.",
        "streetlight": "Dispatch electrical maintenance team for bulk repairs.",
        "water_leakage": "Alert water supply department for emergency pipe inspection.",
        "other": "Review and triage complaints; consider cross-department coordination.",
    }
    base = templates.get(category, "Review complaint cluster and allocate resources.")
    if open_count >= 10:
        base = f"URGENT — {open_count} unresolved. " + base
    return base


def detect_emerging_crises(
    db: Session,
    *,
    window_hours: int = DEFAULT_WINDOW_HOURS,
    spike_threshold_pct: float = DEFAULT_SPIKE_THRESHOLD_PCT,
    min_current_count: int = DEFAULT_MIN_CURRENT_COUNT,
    department_id: int | None = None,
) -> list[CrisisAlert]:
    now = datetime.now(timezone.utc)
    current_start = now - timedelta(hours=window_hours)
    previous_start = current_start - timedelta(hours=window_hours)

    base_q = select(Complaint)
    if department_id is not None:
        base_q = base_q.where(Complaint.assigned_department_id == department_id)

    current_rows = list(db.scalars(
        base_q.where(Complaint.created_at >= current_start)
    ).all())

    previous_rows = list(db.scalars(
        base_q.where(
            Complaint.created_at >= previous_start,
            Complaint.created_at < current_start,
        )
    ).all())

    if not current_rows and not previous_rows:
        return []

    # Build ward name cache
    ward_ids = {c.ward_id for c in current_rows + previous_rows if c.ward_id}
    ward_names: dict[int, str] = {}
    if ward_ids:
        for w in db.scalars(select(Ward).where(Ward.id.in_(ward_ids))).all():
            ward_names[w.id] = w.ward_name

    # Bucket by (category, ward_id)
    def bucket(rows: list[Complaint]) -> dict[tuple, list[Complaint]]:
        b: dict[tuple, list[Complaint]] = {}
        for c in rows:
            key = (c.category.value, c.ward_id)
            b.setdefault(key, []).append(c)
        return b

    cur_bucket = bucket(current_rows)
    prev_bucket = bucket(previous_rows)

    alerts: list[CrisisAlert] = []
    for key, cur_list in cur_bucket.items():
        category, ward_id = key
        cur_count = len(cur_list)
        if cur_count < min_current_count:
            continue

        prev_count = len(prev_bucket.get(key, []))
        if prev_count == 0:
            # No previous data — cannot compute a meaningful percentage
            continue

        pct = ((cur_count - prev_count) / prev_count) * 100.0
        if pct < spike_threshold_pct:
            continue

        open_count = sum(1 for c in cur_list if c.status not in TERMINAL)
        ward_name = ward_names.get(ward_id, "Ward not mapped") if ward_id else "City-wide"
        severity = "critical" if pct >= 200 or open_count >= 10 else "warning"

        alerts.append(CrisisAlert(
            category=category,
            ward_id=ward_id,
            ward_name=ward_name,
            current_count=cur_count,
            previous_count=prev_count,
            pct_increase=round(pct, 1),
            open_count=open_count,
            recommendation=_recommendation(category, open_count, pct),
            severity=severity,
        ))

    # Sort: critical first, then by pct_increase desc
    alerts.sort(key=lambda a: (0 if a.severity == "critical" else 1, -a.pct_increase))
    return alerts
