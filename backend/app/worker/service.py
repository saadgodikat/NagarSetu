from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai.resolution_verifier import verify_complaint_resolution
from app.complaints.service import ComplaintError
from app.models.complaint import Complaint, Image
from app.models.enums import (
    ComplaintStatus,
    ImageType,
    NotificationChannel,
    NotificationStatus,
    UserRole,
)
from app.models.ops import AuditLog, NotificationOutbox, SupportRequest, WorkerNote
from app.models.user import User
from app.storage.images import save_image, validate_image


def _get_assigned(db: Session, worker: User, complaint_id: UUID) -> Complaint:
    complaint = db.scalars(
        select(Complaint)
        .options(selectinload(Complaint.images))
        .where(Complaint.id == complaint_id, Complaint.assigned_to == worker.id)
    ).first()
    if complaint is None:
        raise ComplaintError(404, "Assigned complaint not found")
    return complaint


def list_tasks(db: Session, worker: User) -> list[Complaint]:
    return list(
        db.scalars(
            select(Complaint)
            .options(selectinload(Complaint.images))
            .where(Complaint.assigned_to == worker.id)
            .order_by(Complaint.priority_score.desc().nullslast(), Complaint.created_at.asc())
        ).all()
    )


def get_task(db: Session, worker: User, complaint_id: UUID) -> Complaint:
    return _get_assigned(db, worker, complaint_id)


def update_task_status(
    db: Session, worker: User, complaint_id: UUID, new_status: ComplaintStatus
) -> Complaint:
    complaint = _get_assigned(db, worker, complaint_id)
    allowed = {
        ComplaintStatus.assigned: {ComplaintStatus.in_progress},
        ComplaintStatus.in_progress: {ComplaintStatus.resolution_submitted},
    }
    if new_status not in allowed.get(complaint.status, set()):
        raise ComplaintError(409, f"Cannot change status from {complaint.status.value} to {new_status.value}")
    if new_status == ComplaintStatus.resolution_submitted and not any(
        image.image_type == ImageType.after for image in complaint.images
    ):
        raise ComplaintError(409, "Upload a resolution photo before completing the task")
    old_status = complaint.status.value
    complaint.status = new_status
    if new_status == ComplaintStatus.resolution_submitted:
        complaint.resolved_at = datetime.now(timezone.utc)
        try:
            verify_complaint_resolution(complaint)
        except Exception:
            pass
    db.add(
        AuditLog(
            user_id=worker.id,
            action="worker_status_changed",
            complaint_id=complaint.id,
            old_status=old_status,
            new_status=new_status.value,
        )
    )
    db.add(
        NotificationOutbox(
            user_id=complaint.citizen_id,
            type="complaint_status_changed",
            title="Complaint update",
            message=f"Work status: {new_status.value}",
            payload={"complaint_id": str(complaint.id)},
            channel=NotificationChannel.in_app,
            status=NotificationStatus.sent,
        )
    )
    db.commit()
    db.refresh(complaint)
    return complaint


def add_note(db: Session, worker: User, complaint_id: UUID, note: str) -> Complaint:
    complaint = _get_assigned(db, worker, complaint_id)
    clean_note = note.strip()
    if not clean_note:
        raise ComplaintError(422, "Note is required")
    db.add(WorkerNote(complaint_id=complaint.id, worker_id=worker.id, note=clean_note))
    db.add(
        AuditLog(
            user_id=worker.id,
            action="worker_note_added",
            complaint_id=complaint.id,
            metadata_={"note": clean_note},
        )
    )
    db.commit()
    db.refresh(complaint)
    return complaint


def add_support_request(
    db: Session, worker: User, complaint_id: UUID, description: str
) -> Complaint:
    complaint = _get_assigned(db, worker, complaint_id)
    clean_description = description.strip()
    if not clean_description:
        raise ComplaintError(422, "Support description is required")
    db.add(
        SupportRequest(
            complaint_id=complaint.id,
            requested_by=worker.id,
            description=clean_description,
        )
    )
    db.add(
        AuditLog(
            user_id=worker.id,
            action="support_requested",
            complaint_id=complaint.id,
        )
    )
    db.commit()
    db.refresh(complaint)
    return complaint


def add_resolution_photo(
    db: Session,
    worker: User,
    complaint_id: UUID,
    content: bytes,
    filename: str | None,
    content_type: str | None,
    latitude: float | None = None,
    longitude: float | None = None,
    captured_at: datetime | None = None,
) -> Complaint:
    complaint = _get_assigned(db, worker, complaint_id)
    if complaint.status not in {ComplaintStatus.in_progress, ComplaintStatus.assigned}:
        raise ComplaintError(409, "Start work before submitting resolution evidence")
    ok, info = validate_image(content, filename, content_type)
    if not ok:
        raise ComplaintError(422, info)
    url = save_image(content, info)
    new_image = Image(
        complaint_id=complaint.id,
        url=url,
        image_type=ImageType.after,
        created_by=worker.id,
        latitude=latitude,
        longitude=longitude,
        captured_at=captured_at,
    )
    db.add(new_image)
    if complaint.status == ComplaintStatus.assigned:
        complaint.status = ComplaintStatus.in_progress

    # Run verification check with this resolution evidence
    try:
        verify_complaint_resolution(
            complaint,
            after_content=content,
            evidence_lat=latitude,
            evidence_lng=longitude,
        )
    except Exception:
        pass

    log_meta = {}
    if latitude is not None and longitude is not None:
        log_meta["latitude"] = latitude
        log_meta["longitude"] = longitude

    db.add(
        AuditLog(
            user_id=worker.id,
            action="resolution_photo_uploaded",
            complaint_id=complaint.id,
            new_status=complaint.status.value,
            metadata_=log_meta if log_meta else None,
        )
    )
    db.commit()
    db.refresh(complaint)
    return complaint
