from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.complaint import Complaint
from app.models.enums import ComplaintStatus, Severity, UserRole
from app.models.org import Department, Ward
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsSummaryOut,
    DepartmentWorkloadMetric,
    EmergingIssueMetric,
    WardDistributionMetric,
)

TERMINAL_STATUSES = {ComplaintStatus.closed, ComplaintStatus.rejected}


def get_summary(
    db: Session,
    user: User,
    *,
    department_id: int | None,
) -> AnalyticsSummaryOut:
    if user.role != UserRole.admin:
        department_id = user.department_id

    filters = []
    if department_id is not None:
        filters.append(Complaint.assigned_department_id == department_id)
    complaints = list(db.scalars(select(Complaint).where(*filters)).all())
    now = datetime.now(timezone.utc)

    status_breakdown = {status.value: 0 for status in ComplaintStatus}
    department_rows: dict[int | None, list[Complaint]] = defaultdict(list)
    ward_rows: dict[int | None, list[Complaint]] = defaultdict(list)
    category_rows: dict[str, list[Complaint]] = defaultdict(list)
    for complaint in complaints:
        status_breakdown[complaint.status.value] += 1
        department_rows[complaint.assigned_department_id].append(complaint)
        ward_rows[complaint.ward_id].append(complaint)
        category_rows[complaint.category.value].append(complaint)

    open_complaints = [item for item in complaints if item.status not in TERMINAL_STATUSES]
    overdue_complaints = [
        item
        for item in open_complaints
        if item.sla_deadline is not None and item.sla_deadline < now
    ]
    closed = [item for item in complaints if item.status == ComplaintStatus.closed]
    durations = [
        (item.closed_at - item.created_at).total_seconds() / 3600
        for item in closed
        if item.closed_at is not None and item.created_at is not None
    ]

    department_names = {
        row.id: row.name
        for row in db.scalars(
            select(Department).where(Department.id.in_([key for key in department_rows if key is not None]))
        ).all()
    }
    ward_names = {
        row.id: (row.ward_name, row.zone_id)
        for row in db.scalars(
            select(Ward).where(Ward.id.in_([key for key in ward_rows if key is not None]))
        ).all()
    }

    workload = []
    for key, rows in sorted(department_rows.items(), key=lambda item: item[0] or 0):
        workload.append(
            DepartmentWorkloadMetric(
                department_id=key,
                department_name=department_names.get(key, "Unassigned department"),
                total=len(rows),
                open=sum(item.status not in TERMINAL_STATUSES for item in rows),
                overdue=sum(
                    item.status not in TERMINAL_STATUSES
                    and item.sla_deadline is not None
                    and item.sla_deadline < now
                    for item in rows
                ),
            )
        )

    ward_distribution = []
    for key, rows in sorted(ward_rows.items(), key=lambda item: item[0] or 0):
        ward_name, zone_id = ward_names.get(key, ("Ward not mapped", None))
        ward_distribution.append(
            WardDistributionMetric(
                ward_id=key,
                ward_name=ward_name,
                zone_id=zone_id,
                total=len(rows),
            )
        )

    emerging_issues = sorted(
        (
            EmergingIssueMetric(
                category=category,
                count=len(rows),
                open_count=sum(item.status not in TERMINAL_STATUSES for item in rows),
            )
            for category, rows in category_rows.items()
        ),
        key=lambda item: (-item.open_count, -item.count, item.category),
    )[:5]

    return AnalyticsSummaryOut(
        generated_at=now.isoformat(),
        total_complaints=len(complaints),
        open_complaints=len(open_complaints),
        critical_complaints=sum(item.severity == Severity.CRITICAL for item in complaints),
        overdue_complaints=len(overdue_complaints),
        unassigned_complaints=sum(item.assigned_to is None for item in open_complaints),
        resolution_rate=round((len(closed) / len(complaints)) * 100, 2) if complaints else 0,
        average_resolution_hours=round(sum(durations) / len(durations), 2) if durations else None,
        status_breakdown=status_breakdown,
        department_workload=workload,
        ward_distribution=ward_distribution,
        emerging_issues=emerging_issues,
    )
