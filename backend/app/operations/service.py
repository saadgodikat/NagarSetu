from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_department
from app.complaints.service import ComplaintError
from app.models.complaint import Complaint
from app.models.enums import ComplaintStatus, NotificationChannel, NotificationStatus, UserRole
from app.models.ops import AssignmentHistory, AuditLog, NotificationOutbox
from app.models.user import User
from app.sla.service import set_sla_deadline


def _get_for_user(db: Session, user: User, complaint_id: UUID) -> Complaint:
    complaint = db.scalars(
        select(Complaint)
        .options(selectinload(Complaint.images))
        .where(Complaint.id == complaint_id)
    ).first()
    if complaint is None:
        raise ComplaintError(404, "Complaint not found")
    require_department(user, complaint.assigned_department_id)
    return complaint


def list_department_complaints(
    db: Session,
    user: User,
    *,
    status: ComplaintStatus | None,
    department_id: int | None,
) -> list[Complaint]:
    requested_department = department_id if user.role == UserRole.admin else user.department_id
    if user.role == UserRole.admin and department_id is None:
        requested_department = None
    filters = []
    if requested_department is not None:
        filters.append(Complaint.assigned_department_id == requested_department)
    if status is not None:
        filters.append(Complaint.status == status)
    return list(
        db.scalars(
            select(Complaint)
            .options(selectinload(Complaint.images))
            .where(*filters)
            .order_by(Complaint.created_at.desc())
        ).all()
    )


def update_status(db: Session, user: User, complaint_id: UUID, new_status: ComplaintStatus) -> Complaint:
    complaint = _get_for_user(db, user, complaint_id)
    allowed = {
        ComplaintStatus.submitted: {ComplaintStatus.under_review, ComplaintStatus.rejected},
        ComplaintStatus.reopened: {ComplaintStatus.under_review, ComplaintStatus.rejected},
        ComplaintStatus.under_review: {ComplaintStatus.rejected},
        ComplaintStatus.resolution_submitted: {ComplaintStatus.verified, ComplaintStatus.reopened},
    }
    if new_status not in allowed.get(complaint.status, set()):
        raise ComplaintError(409, f"Cannot change status from {complaint.status.value} to {new_status.value}")
    old_status = complaint.status.value
    complaint.status = new_status
    set_sla_deadline(db, complaint)
    db.add(
        AuditLog(
            user_id=user.id,
            action="status_changed",
            complaint_id=complaint.id,
            old_status=old_status,
            new_status=new_status.value,
        )
    )
    _notify_citizen(db, complaint, "complaint_status_changed", f"Complaint status: {new_status.value}")
    db.commit()
    db.refresh(complaint)
    return complaint


def assign_field_worker(
    db: Session, user: User, complaint_id: UUID, field_worker_id: UUID
) -> Complaint:
    complaint = _get_for_user(db, user, complaint_id)
    worker = db.get(User, field_worker_id)
    if (
        worker is None
        or worker.role != UserRole.field_worker
        or worker.department_id != complaint.assigned_department_id
    ):
        raise ComplaintError(422, "Field worker must belong to the complaint department")
    now = datetime.now(timezone.utc)
    old_status = complaint.status.value
    if complaint.assigned_to is not None:
        db.query(AssignmentHistory).filter(
            AssignmentHistory.complaint_id == complaint.id,
            AssignmentHistory.unassigned_at.is_(None),
        ).update({"unassigned_at": now})
    complaint.assigned_to = worker.id
    complaint.assigned_at = now
    complaint.status = ComplaintStatus.assigned
    set_sla_deadline(db, complaint, now)
    db.add(
        AssignmentHistory(
            complaint_id=complaint.id,
            assigned_by=user.id,
            assigned_to=worker.id,
            department_id=complaint.assigned_department_id,
            reason="Officer assignment",
        )
    )
    db.add(
        AuditLog(
            user_id=user.id,
            action="complaint_assigned",
            complaint_id=complaint.id,
            old_status=old_status,
            new_status=ComplaintStatus.assigned.value,
            metadata_={"assigned_to": str(worker.id)},
        )
    )
    db.add(
        NotificationOutbox(
            user_id=worker.id,
            type="complaint_assigned",
            title="Complaint assigned",
            message=complaint.title,
            payload={"complaint_id": str(complaint.id)},
            channel=NotificationChannel.in_app,
            status=NotificationStatus.sent,
        )
    )
    _notify_citizen(db, complaint, "complaint_assigned", "Your complaint was assigned for resolution")
    db.commit()
    db.refresh(complaint)
    return complaint


def _notify_citizen(db: Session, complaint: Complaint, kind: str, message: str) -> None:
    db.add(
        NotificationOutbox(
            user_id=complaint.citizen_id,
            type=kind,
            title="Complaint update",
            message=message,
            payload={"complaint_id": str(complaint.id)},
            channel=NotificationChannel.in_app,
            status=NotificationStatus.sent,
        )
    )
