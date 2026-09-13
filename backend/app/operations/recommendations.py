"""
Smart worker recommendation service.

Scores available field workers for a given complaint using:
- Current active task count (workload)
- Haversine distance from complaint location
- Department/category compatibility (same department = match)

Returns ranked list with scores. No fake data — all from DB.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.complaint import Complaint
from app.models.enums import ComplaintStatus, UserRole
from app.models.user import User

ACTIVE_STATUSES = [
    ComplaintStatus.assigned.value,
    ComplaintStatus.in_progress.value,
]


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@dataclass
class WorkerRecommendation:
    worker_id: UUID
    worker_name: str
    active_tasks: int
    distance_km: float | None
    department_match: bool
    score: float          # 0–100, higher = better recommendation
    reason: str


def recommend_workers(
    db: Session,
    complaint_id: UUID,
    limit: int = 5,
) -> list[WorkerRecommendation]:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        return []

    # Workers in the same department
    workers = list(db.scalars(
        select(User).where(
            User.role == UserRole.field_worker,
            User.department_id == complaint.assigned_department_id,
        )
    ).all())

    if not workers:
        return []

    # Active task counts per worker
    task_counts: dict[UUID, int] = {}
    rows = db.execute(
        select(Complaint.assigned_to, func.count().label("cnt"))
        .where(
            Complaint.assigned_to.in_([w.id for w in workers]),
            Complaint.status.in_(ACTIVE_STATUSES),
        )
        .group_by(Complaint.assigned_to)
    ).all()
    for row in rows:
        task_counts[row[0]] = row[1]

    results: list[WorkerRecommendation] = []
    for worker in workers:
        active = task_counts.get(worker.id, 0)

        # Distance score — only if complaint has coordinates
        dist_km: float | None = None
        if complaint.location_lat and complaint.location_lng:
            # Use complaint location as proxy for worker location
            # (real GPS not stored per worker — use last assigned complaint location)
            last = db.scalars(
                select(Complaint)
                .where(
                    Complaint.assigned_to == worker.id,
                    Complaint.location_lat.isnot(None),
                )
                .order_by(Complaint.created_at.desc())
                .limit(1)
            ).first()
            if last:
                dist_km = _haversine_km(
                    complaint.location_lat, complaint.location_lng,
                    last.location_lat, last.location_lng,
                )

        # Score: workload (40%), distance (40%), dept match always true here (20%)
        workload_score = max(0.0, 1.0 - (active / 10.0))  # 0 tasks = 1.0, 10+ = 0
        if dist_km is not None:
            dist_score = max(0.0, 1.0 - (dist_km / 20.0))  # 0 km = 1.0, 20+ km = 0
        else:
            dist_score = 0.5  # unknown distance = neutral

        raw = (0.40 * workload_score) + (0.40 * dist_score) + (0.20 * 1.0)
        score = round(raw * 100, 1)

        parts = [f"Dept match", f"{active} active task{'s' if active != 1 else ''}"]
        if dist_km is not None:
            parts.append(f"{dist_km:.1f} km away")
        reason = " · ".join(parts)

        results.append(WorkerRecommendation(
            worker_id=worker.id,
            worker_name=worker.name,
            active_tasks=active,
            distance_km=round(dist_km, 2) if dist_km is not None else None,
            department_match=True,
            score=score,
            reason=reason,
        ))

    results.sort(key=lambda r: -r.score)
    return results[:limit]
