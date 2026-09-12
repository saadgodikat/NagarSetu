from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.complaint import Complaint
from app.models.enums import ComplaintStatus, NotificationChannel, NotificationStatus, UserRole
from app.models.ops import AuditLog, NotificationOutbox, SlaAudit, SlaPolicy
from app.models.user import User
from app.ai.sla_predictor import extract_sla_features, get_sla_predictor
from app.models.ops import ComplaintRelation

ACTIVE_STATUSES = {
    ComplaintStatus.submitted,
    ComplaintStatus.under_review,
    ComplaintStatus.assigned,
    ComplaintStatus.in_progress,
    ComplaintStatus.resolution_submitted,
    ComplaintStatus.reopened,
}


@dataclass(frozen=True)
class SlaRunResult:
    evaluated_at: datetime
    reminders_created: int
    escalations_created: int


def policy_for(db: Session, department_id: int | None, status: ComplaintStatus) -> SlaPolicy | None:
    if department_id is None:
        return None
    return db.scalars(
        select(SlaPolicy)
        .where(
            SlaPolicy.status == status.value,
            SlaPolicy.enabled.is_(True),
            SlaPolicy.department_id.in_((department_id,)),
        )
        .order_by(SlaPolicy.department_id.desc())
    ).first()


def set_sla_deadline(db: Session, complaint: Complaint, now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    policy = policy_for(db, complaint.assigned_department_id, complaint.status)
    complaint.sla_deadline = (
        now + timedelta(minutes=policy.escalate_after_minutes) if policy is not None else None
    )


def _status_started_at(db: Session, complaint: Complaint) -> datetime:
    event_time = db.scalar(
        select(AuditLog.timestamp)
        .where(
            AuditLog.complaint_id == complaint.id,
            AuditLog.new_status == complaint.status.value,
        )
        .order_by(AuditLog.timestamp.desc())
    )
    return event_time or complaint.created_at


def _already_recorded(db: Session, complaint_id, sla_type: str) -> bool:
    return (
        db.scalar(
            select(SlaAudit.id).where(
                SlaAudit.complaint_id == complaint_id,
                SlaAudit.sla_type == sla_type,
            )
        )
        is not None
    )


def _recipient_ids(db: Session, complaint: Complaint, *, escalation: bool) -> list:
    if not escalation and complaint.assigned_to is not None:
        return [complaint.assigned_to]
    users = db.scalars(
        select(User).where(
            User.department_id == complaint.assigned_department_id,
            User.role.in_((UserRole.officer, UserRole.department_head)),
        )
    ).all()
    return [user.id for user in users]


def run_sla_evaluation(db: Session, now: datetime | None = None) -> SlaRunResult:
    evaluated_at = now or datetime.now(timezone.utc)
    reminders = 0
    escalations = 0
    complaints = db.scalars(
        select(Complaint).where(Complaint.status.in_([status.value for status in ACTIVE_STATUSES]))
    ).all()

    for complaint in complaints:
        policy = policy_for(db, complaint.assigned_department_id, complaint.status)
        if policy is None:
            continue
        started_at = _status_started_at(db, complaint)
        elapsed = evaluated_at - started_at
        for sla_type, threshold in (
            ("reminder", policy.reminder_after_minutes),
            ("escalation", policy.escalate_after_minutes),
        ):
            if elapsed < timedelta(minutes=threshold) or _already_recorded(db, complaint.id, sla_type):
                continue
            expected_time = started_at + timedelta(minutes=threshold)
            db.add(
                SlaAudit(
                    complaint_id=complaint.id,
                    sla_type=sla_type,
                    expected_time=expected_time,
                    actual_time=evaluated_at,
                    action_taken=f"{sla_type}_created",
                )
            )
            for user_id in _recipient_ids(db, complaint, escalation=sla_type == "escalation"):
                db.add(
                    NotificationOutbox(
                        user_id=user_id,
                        type=f"sla_{sla_type}",
                        title=f"SLA {sla_type}",
                        message=f"{complaint.title} requires attention",
                        payload={"complaint_id": str(complaint.id)},
                        channel=NotificationChannel.in_app,
                        status=NotificationStatus.sent,
                    )
                )
            db.add(
                AuditLog(
                    user_id=None,
                    action=f"sla_{sla_type}",
                    complaint_id=complaint.id,
                    metadata_={"threshold_minutes": threshold},
                )
            )
            if sla_type == "reminder":
                reminders += 1
            else:
                complaint.escalated_at = evaluated_at
                escalations += 1
    db.commit()
    # Refresh SLA breach predictions for all active complaints
    _refresh_breach_predictions(db, complaints, evaluated_at)
    return SlaRunResult(evaluated_at, reminders, escalations)


def _refresh_breach_predictions(db: Session, complaints: list[Complaint], now: datetime) -> None:
    """Update breach_probability and escalation_level for active complaints."""
    predictor = get_sla_predictor()
    for complaint in complaints:
        try:
            from sqlalchemy import func as sqlfunc
            related_count = db.scalar(
                select(sqlfunc.count())
                .select_from(ComplaintRelation)
                .where(ComplaintRelation.complaint_id == complaint.id)
            ) or 0
            features = extract_sla_features(
                category=complaint.category,
                severity=complaint.severity,
                priority_score=complaint.priority_score,
                created_at=complaint.created_at,
                status_changed_at=None,
                related_count=related_count,
                assigned_to=complaint.assigned_to,
                assigned_department_id=complaint.assigned_department_id,
                sla_deadline=complaint.sla_deadline,
                now=now,
            )
            prediction = predictor.predict(features)
            complaint.breach_probability = prediction.breach_probability
            complaint.escalation_level = prediction.escalation_level
            complaint.sla_predicted_at = prediction.predicted_at
        except Exception as exc:  # pragma: no cover
            import logging
            logging.getLogger(__name__).error(
                "SLA prediction refresh failed for %s: %s", complaint.id, exc
            )
    db.commit()
