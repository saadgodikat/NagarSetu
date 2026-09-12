from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.ai.classification import get_classifier
from app.ai.department import department_id_for_category
from app.ai.duplicates import (
    duration_days_from_text,
    find_possible_duplicates,
    record_possible_duplicates,
)
from app.ai.priority import score_priority
from app.ai.severity import rule_severity
from app.ai.sla_predictor import extract_sla_features, get_sla_predictor
from app.geo.lookup import lookup_ward_id
from app.models.complaint import Complaint, Image
from app.models.enums import (
    ComplaintCategory,
    ComplaintStatus,
    ImageType,
    NotificationChannel,
    NotificationStatus,
    Severity,
    UserRole,
)
from app.models.ops import AuditLog, ComplaintRelation, NotificationOutbox
from app.models.org import Ward
from app.models.user import User
from app.schemas.complaints import ComplaintOut, TimelineEventOut
from app.storage.images import save_image, validate_image
from app.sla.service import set_sla_deadline


class ComplaintError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def create_complaint(
    db: Session,
    *,
    citizen: User,
    title: str,
    description: str,
    latitude: float,
    longitude: float,
    photo: bytes,
    photo_name: str | None,
    photo_type: str | None,
    category_override: ComplaintCategory | None,
) -> Complaint:
    if citizen.role != UserRole.citizen:
        raise ComplaintError(403, "Only citizens can submit complaints")
    title = title.strip()
    description = description.strip()
    if not title or not description:
        raise ComplaintError(422, "Title and description are required")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ComplaintError(422, "Invalid coordinates")
    ok, info = validate_image(photo, photo_name, photo_type)
    if not ok:
        raise ComplaintError(422, info)

    classification = get_classifier().classify(photo, description)
    category = category_override or classification.category
    severity, sev_reasons = rule_severity(description)
    dept_id = department_id_for_category(category)
    matches = find_possible_duplicates(
        db, category=category, lat=latitude, lng=longitude, text=f"{title} {description}"
    )
    safety = severity in (Severity.HIGH, Severity.CRITICAL) or any(
        word in description.lower() for word in ("unsafe", "danger", "contaminated")
    )
    score, label, pri_reasons = score_priority(
        severity=severity,
        related_count=len(matches),
        duration_days=duration_days_from_text(description),
        safety_risk=safety,
    )
    ward_id = lookup_ward_id(db, longitude, latitude)
    zone_id = None
    if ward_id is not None:
        ward = db.get(Ward, ward_id)
        zone_id = ward.zone_id if ward else None

    complaint = Complaint(
        citizen_id=citizen.id,
        title=title[:255],
        description=description,
        category=category,
        category_confidence=classification.confidence,
        severity=severity,
        severity_reason=sev_reasons,
        priority_score=score,
        priority_label=label,
        priority_reasons=pri_reasons,
        ward_id=ward_id,
        zone_id=zone_id,
        location_lat=latitude,
        location_lng=longitude,
        assigned_department_id=dept_id,
        status=ComplaintStatus.submitted,
    )
    db.add(complaint)
    db.flush()
    set_sla_deadline(db, complaint)
    # Phase 3 – SLA breach prediction at submission time
    _apply_sla_prediction(db, complaint, related_count=len(matches))
    url = save_image(photo, info)
    db.add(
        Image(
            complaint_id=complaint.id,
            url=url,
            image_type=ImageType.before,
            created_by=citizen.id,
        )
    )
    record_possible_duplicates(db, complaint, matches)
    db.add(
        AuditLog(
            user_id=citizen.id,
            action="complaint_submitted",
            complaint_id=complaint.id,
            old_status=None,
            new_status=ComplaintStatus.submitted.value,
            metadata_={"classification_source": classification.source},
        )
    )
    _notify_department(db, complaint)
    db.commit()
    db.refresh(complaint)
    return complaint


def list_citizen_complaints(
    db: Session, citizen: User, page: int, page_size: int
) -> tuple[list[Complaint], int]:
    if page < 1 or page_size < 1 or page_size > 100:
        raise ComplaintError(422, "Invalid pagination")
    filters = [Complaint.citizen_id == citizen.id]
    total = db.scalar(select(func.count()).select_from(Complaint).where(*filters)) or 0
    rows = db.scalars(
        select(Complaint)
        .options(selectinload(Complaint.images))
        .where(*filters)
        .order_by(Complaint.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), int(total)


def get_citizen_complaint(db: Session, citizen: User, complaint_id: UUID) -> Complaint:
    complaint = db.scalars(
        select(Complaint).options(selectinload(Complaint.images)).where(Complaint.id == complaint_id)
    ).first()
    if complaint is None:
        raise ComplaintError(404, "Complaint not found")
    if complaint.citizen_id != citizen.id:
        raise ComplaintError(404, "Complaint not found")
    return complaint


def decide_resolution(
    db: Session,
    citizen: User,
    complaint_id: UUID,
    *,
    confirmed: bool,
    reason: str | None,
    rating: int | None = None,
    feedback: str | None = None,
) -> Complaint:
    complaint = get_citizen_complaint(db, citizen, complaint_id)
    if complaint.status not in (ComplaintStatus.resolution_submitted, ComplaintStatus.verified):
        raise ComplaintError(409, "This complaint is not awaiting citizen confirmation")
    if not any(image.image_type == ImageType.after for image in complaint.images):
        raise ComplaintError(409, "Resolution evidence is missing")
    clean_reason = (reason or "").strip()
    if not confirmed and not clean_reason:
        raise ComplaintError(422, "Explain why the resolution was rejected")

    old_status = complaint.status.value
    new_status = ComplaintStatus.closed if confirmed else ComplaintStatus.reopened
    complaint.status = new_status
    if confirmed:
        complaint.closed_at = datetime.now(timezone.utc)
    else:
        complaint.closed_at = None

    if rating is not None:
        complaint.citizen_rating = rating
    combined_notes = clean_reason or feedback
    if combined_notes:
        complaint.citizen_feedback = combined_notes

    # Update verification verdict with citizen feedback
    try:
        from app.ai.resolution_verifier import verify_complaint_resolution
        verify_complaint_resolution(
            complaint,
            citizen_confirmed=confirmed,
            citizen_rating=rating,
            citizen_feedback=combined_notes,
        )
    except Exception:
        pass

    log_meta = {}
    if clean_reason:
        log_meta["reason"] = clean_reason
    if rating:
        log_meta["rating"] = rating
    if feedback:
        log_meta["feedback"] = feedback

    db.add(
        AuditLog(
            user_id=citizen.id,
            action="resolution_confirmed" if confirmed else "resolution_rejected",
            complaint_id=complaint.id,
            old_status=old_status,
            new_status=new_status.value,
            metadata_=log_meta if log_meta else None,
        )
    )
    if complaint.assigned_to is not None:
        db.add(
            NotificationOutbox(
                user_id=complaint.assigned_to,
                type="resolution_confirmed" if confirmed else "resolution_rejected",
                title="Resolution decision",
                message="Citizen confirmed the resolution" if confirmed else "Citizen requested more work",
                payload={"complaint_id": str(complaint.id)},
                channel=NotificationChannel.in_app,
                status=NotificationStatus.sent,
            )
        )
    db.commit()
    db.refresh(complaint)
    return complaint


def to_out(db: Session, complaint: Complaint, *, include_timeline: bool) -> ComplaintOut:
    ward_name = None
    if complaint.ward_id is not None:
        ward = db.get(Ward, complaint.ward_id)
        ward_name = ward.ward_name if ward else None
    related = db.scalar(
        select(func.count()).select_from(ComplaintRelation).where(
            ComplaintRelation.complaint_id == complaint.id
        )
    ) or 0
    events: list[TimelineEventOut] = []
    if include_timeline:
        logs = db.scalars(
            select(AuditLog)
            .where(AuditLog.complaint_id == complaint.id)
            .order_by(AuditLog.timestamp.asc())
        ).all()
        events = [
            TimelineEventOut(
                action=log.action,
                old_status=log.old_status,
                new_status=log.new_status,
                timestamp=log.timestamp,
            )
            for log in logs
        ]
    assigned_to_name = None
    if complaint.assigned_to is not None:
        assignee = db.get(User, complaint.assigned_to)
        assigned_to_name = assignee.name if assignee else None
    source = None
    if include_timeline:
        for log in db.scalars(
            select(AuditLog).where(
                AuditLog.complaint_id == complaint.id, AuditLog.action == "complaint_submitted"
            )
        ):
            if log.metadata_ and "classification_source" in log.metadata_:
                source = log.metadata_["classification_source"]
    return ComplaintOut(
        id=complaint.id,
        title=complaint.title,
        description=complaint.description,
        category=complaint.category,
        category_confidence=complaint.category_confidence,
        classification_source=source,
        severity=complaint.severity,
        severity_reason=complaint.severity_reason,
        priority_score=complaint.priority_score,
        priority_label=complaint.priority_label,
        priority_reasons=complaint.priority_reasons,
        ward_id=complaint.ward_id,
        ward_name=ward_name,
        zone_id=complaint.zone_id,
        location_lat=complaint.location_lat,
        location_lng=complaint.location_lng,
        assigned_department_id=complaint.assigned_department_id,
        assigned_to=complaint.assigned_to,
        assigned_to_name=assigned_to_name,
        status=complaint.status,
        sla_deadline=complaint.sla_deadline,
        escalated_at=complaint.escalated_at,
        breach_probability=complaint.breach_probability,
        escalation_level=complaint.escalation_level,
        sla_predicted_at=complaint.sla_predicted_at,
        verification_score=complaint.verification_score,
        verification_status=complaint.verification_status,
        verification_details=complaint.verification_details,
        verified_at=complaint.verified_at,
        citizen_rating=complaint.citizen_rating,
        citizen_feedback=complaint.citizen_feedback,
        created_at=complaint.created_at,
        images=list(complaint.images),
        timeline=events,
        related_count=int(related),
    )


def _apply_sla_prediction(db: "Session", complaint: "Complaint", *, related_count: int) -> None:
    """Run SLA breach prediction and stamp results onto complaint (in-place)."""
    try:
        from datetime import timezone as _tz

        features = extract_sla_features(
            category=complaint.category,
            severity=complaint.severity,
            priority_score=complaint.priority_score,
            created_at=complaint.created_at,
            status_changed_at=complaint.created_at,  # just submitted
            related_count=related_count,
            assigned_to=complaint.assigned_to,
            assigned_department_id=complaint.assigned_department_id,
            sla_deadline=complaint.sla_deadline,
        )
        prediction = get_sla_predictor().predict(features)
        complaint.breach_probability = prediction.breach_probability
        complaint.escalation_level = prediction.escalation_level
        complaint.sla_predicted_at = prediction.predicted_at
    except Exception as exc:  # pragma: no cover
        import logging
        logging.getLogger(__name__).error("SLA prediction failed: %s", exc)


def _notify_department(db: Session, complaint: Complaint) -> None:
    officers = db.scalars(
        select(User).where(
            User.department_id == complaint.assigned_department_id,
            User.role.in_((UserRole.officer, UserRole.department_head)),
        )
    ).all()
    for officer in officers:
        db.add(
            NotificationOutbox(
                user_id=officer.id,
                type="complaint_submitted",
                title="New complaint submitted",
                message=complaint.title,
                payload={"complaint_id": str(complaint.id)},
                channel=NotificationChannel.in_app,
                status=NotificationStatus.sent,
            )
        )
