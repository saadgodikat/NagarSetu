from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.complaints.service import ComplaintError, to_out
from app.db import get_db
from app.models.enums import ComplaintStatus, UserRole
from app.models.ops import SlaPolicy
from app.models.user import User
from app.operations.service import (
    assign_field_worker,
    list_department_complaints,
    update_status,
)
from app.schemas.complaints import ComplaintListOut, ComplaintOut
from app.schemas.operations import (
    ComplaintAssignment,
    ComplaintStatusUpdate,
    SlaPolicyOut,
    SlaPolicyUpsert,
    SlaRunOut,
)
from app.schemas.common import UserOut
from app.sla.service import run_sla_evaluation

router = APIRouter(prefix="/api/v1/operations", tags=["operations"])
OPS_ROLES = (UserRole.officer, UserRole.department_head, UserRole.admin)


def _raise(exc: ComplaintError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/complaints", response_model=ComplaintListOut)
def queue(
    status: ComplaintStatus | None = Query(default=None),
    department_id: int | None = Query(default=None, ge=1),
    user: User = Depends(require_roles(*OPS_ROLES)),
    db: Session = Depends(get_db),
) -> ComplaintListOut:
    rows = list_department_complaints(db, user, status=status, department_id=department_id)
    return ComplaintListOut(
        data=[to_out(db, row, include_timeline=False) for row in rows],
        pagination={"page": 1, "pageSize": len(rows), "totalItems": len(rows), "totalPages": 1},
    )


@router.get("/workers", response_model=list[UserOut])
def workers(
    user: User = Depends(require_roles(*OPS_ROLES)),
    db: Session = Depends(get_db),
) -> list[UserOut]:
    query = select(User).where(User.role == UserRole.field_worker)
    if user.role != UserRole.admin:
        query = query.where(User.department_id == user.department_id)
    return list(db.scalars(query.order_by(User.name)).all())


@router.get("/complaints/{complaint_id}", response_model=ComplaintOut)
def detail(
    complaint_id: UUID,
    user: User = Depends(require_roles(*OPS_ROLES)),
    db: Session = Depends(get_db),
) -> ComplaintOut:
    from app.operations.service import _get_for_user

    try:
        return to_out(db, _get_for_user(db, user, complaint_id), include_timeline=True)
    except ComplaintError as exc:
        _raise(exc)


@router.patch("/complaints/{complaint_id}/status", response_model=ComplaintOut)
def set_status(
    complaint_id: UUID,
    body: ComplaintStatusUpdate,
    user: User = Depends(require_roles(*OPS_ROLES)),
    db: Session = Depends(get_db),
) -> ComplaintOut:
    try:
        return to_out(db, update_status(db, user, complaint_id, body.status), include_timeline=True)
    except ComplaintError as exc:
        _raise(exc)


@router.post("/complaints/{complaint_id}/assign", response_model=ComplaintOut)
def assign(
    complaint_id: UUID,
    body: ComplaintAssignment,
    user: User = Depends(require_roles(*OPS_ROLES)),
    db: Session = Depends(get_db),
) -> ComplaintOut:
    try:
        return to_out(db, assign_field_worker(db, user, complaint_id, body.field_worker_id), include_timeline=True)
    except ComplaintError as exc:
        _raise(exc)


@router.get("/sla/policies", response_model=list[SlaPolicyOut])
def list_sla_policies(
    user: User = Depends(require_roles(*OPS_ROLES)),
    db: Session = Depends(get_db),
) -> list[SlaPolicy]:
    query = select(SlaPolicy).order_by(SlaPolicy.status)
    if user.role != UserRole.admin:
        query = query.where(SlaPolicy.department_id == user.department_id)
    return list(db.scalars(query).all())


@router.put("/sla/policies/{status}", response_model=SlaPolicyOut)
def upsert_sla_policy(
    status: ComplaintStatus,
    body: SlaPolicyUpsert,
    user: User = Depends(require_roles(*OPS_ROLES)),
    db: Session = Depends(get_db),
) -> SlaPolicy:
    department_id = body.department_id if user.role == UserRole.admin else user.department_id
    if department_id is None:
        raise HTTPException(status_code=422, detail="A department is required for SLA policies")
    policy = db.scalars(
        select(SlaPolicy).where(
            SlaPolicy.department_id == department_id,
            SlaPolicy.status == status.value,
        )
    ).first()
    if policy is None:
        policy = SlaPolicy(department_id=department_id, status=status.value)
        db.add(policy)
    policy.reminder_after_minutes = body.reminder_after_minutes
    policy.escalate_after_minutes = body.escalate_after_minutes
    policy.enabled = body.enabled
    db.commit()
    db.refresh(policy)
    return policy


@router.post("/sla/run", response_model=SlaRunOut)
def run_sla(
    user: User = Depends(require_roles(*OPS_ROLES)),
    db: Session = Depends(get_db),
) -> SlaRunOut:
    result = run_sla_evaluation(db)
    return SlaRunOut(
        evaluated_at=result.evaluated_at,
        reminders_created=result.reminders_created,
        escalations_created=result.escalations_created,
    )


# ---------------------------------------------------------------------------
# Phase 3 – SLA Breach Prediction endpoints
# ---------------------------------------------------------------------------
from app.schemas.complaints import SLAPredictionOut  # noqa: E402
from app.models.complaint import Complaint as _Complaint  # noqa: E402
from app.ai.sla_predictor import extract_sla_features, get_sla_predictor  # noqa: E402
from sqlalchemy import func as sqlfunc  # noqa: E402
from app.models.ops import ComplaintRelation as _CR  # noqa: E402


@router.post("/complaints/{complaint_id}/sla-prediction", response_model=SLAPredictionOut)
def refresh_sla_prediction(
    complaint_id: UUID,
    user: User = Depends(require_roles(*OPS_ROLES)),
    db: Session = Depends(get_db),
) -> SLAPredictionOut:
    """
    Re-run SLA breach prediction for a single complaint on demand.

    This is useful when an officer wants an up-to-date risk score between
    SLA evaluation sweeps. Results are also persisted back to the DB.
    """
    from app.operations.service import _get_for_user
    try:
        complaint = _get_for_user(db, user, complaint_id)
    except ComplaintError as exc:
        _raise(exc)

    related_count = db.scalar(
        sqlfunc.count(_CR.id)
        .__class__(sqlfunc.count())
        .select_from(_CR)
        .where(_CR.complaint_id == complaint.id)
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
    )
    prediction = get_sla_predictor().predict(features)

    # Persist updated prediction
    complaint.breach_probability = prediction.breach_probability
    complaint.escalation_level = prediction.escalation_level
    complaint.sla_predicted_at = prediction.predicted_at
    db.commit()

    return SLAPredictionOut(
        complaint_id=complaint.id,
        breach_probability=prediction.breach_probability,
        escalation_level=prediction.escalation_level,
        source=prediction.source,
        confidence_reasons=prediction.confidence_reasons,
        predicted_at=prediction.predicted_at,
    )


@router.get("/sla/high-risk", response_model=ComplaintListOut)
def high_risk_complaints(
    threshold: float = Query(default=0.60, ge=0.0, le=1.0),
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(require_roles(*OPS_ROLES)),
    db: Session = Depends(get_db),
) -> ComplaintListOut:
    """
    Return complaints whose breach_probability is at or above the threshold.
    Ordered by breach_probability descending (highest risk first).
    """
    from app.models.enums import ComplaintStatus as _CS
    active_statuses = [
        _CS.submitted.value, _CS.under_review.value,
        _CS.assigned.value, _CS.in_progress.value,
        _CS.resolution_submitted.value, _CS.reopened.value,
    ]
    query = (
        db.query(_Complaint)
        .filter(
            _Complaint.breach_probability >= threshold,
            _Complaint.status.in_(active_statuses),
        )
        .order_by(_Complaint.breach_probability.desc())
        .limit(limit)
    )
    if user.role != UserRole.admin and user.department_id is not None:
        query = query.filter(_Complaint.assigned_department_id == user.department_id)

    rows = query.all()
    return ComplaintListOut(
        data=[to_out(db, row, include_timeline=False) for row in rows],
        pagination={"page": 1, "pageSize": len(rows), "totalItems": len(rows), "totalPages": 1},
    )


# ---------------------------------------------------------------------------
# Phase 6 – Multi-Signal Resolution Verification endpoints for Operations
# ---------------------------------------------------------------------------
from app.schemas.complaints import VerificationReportOut  # noqa: E402
from app.ai.resolution_verifier import verify_complaint_resolution  # noqa: E402


@router.get("/complaints/{complaint_id}/verification", response_model=VerificationReportOut)
def operations_get_verification(
    complaint_id: UUID,
    user: User = Depends(require_roles(*OPS_ROLES)),
    db: Session = Depends(get_db),
) -> VerificationReportOut:
    """Retrieve detailed multi-signal verification report for a complaint."""
    from app.operations.service import _get_for_user
    try:
        complaint = _get_for_user(db, user, complaint_id)
    except ComplaintError as exc:
        _raise(exc)

    if not complaint.verification_details:
        result = verify_complaint_resolution(complaint)
        db.commit()
    else:
        details = complaint.verification_details
        from datetime import datetime, timezone
        return VerificationReportOut(
            complaint_id=complaint.id,
            verified=details.get("verified", False),
            status=complaint.verification_status or "pending",
            composite_score=complaint.verification_score or 0.0,
            signals=details.get("signals", {}),
            recommendation=details.get("recommendation", ""),
            flags=details.get("flags", []),
            evaluated_at=details.get("evaluated_at", datetime.now(timezone.utc).isoformat()),
            source=details.get("source", "multi_signal_rule_engine"),
        )
    return VerificationReportOut(
        complaint_id=complaint.id,
        verified=result.verified,
        status=result.status,
        composite_score=result.composite_score,
        signals=result.signals,
        recommendation=result.recommendation,
        flags=result.flags,
        evaluated_at=result.evaluated_at,
        source=result.source,
    )


@router.post("/complaints/{complaint_id}/verify", response_model=VerificationReportOut)
def operations_trigger_verify(
    complaint_id: UUID,
    user: User = Depends(require_roles(*OPS_ROLES)),
    db: Session = Depends(get_db),
) -> VerificationReportOut:
    """Trigger re-evaluation of multi-signal resolution verification on demand."""
    from app.operations.service import _get_for_user
    try:
        complaint = _get_for_user(db, user, complaint_id)
    except ComplaintError as exc:
        _raise(exc)

    result = verify_complaint_resolution(complaint)
    db.commit()

    return VerificationReportOut(
        complaint_id=complaint.id,
        verified=result.verified,
        status=result.status,
        composite_score=result.composite_score,
        signals=result.signals,
        recommendation=result.recommendation,
        flags=result.flags,
        evaluated_at=result.evaluated_at,
        source=result.source,
    )


from app.schemas.complaints import ClassifyOut  # noqa: E402
from app.ai.classification import get_classifier  # noqa: E402
from app.ai.department import department_id_for_category  # noqa: E402
from app.ai.severity import rule_severity  # noqa: E402
from app.ai.resolution_verifier import load_image_bytes  # noqa: E402


@router.post("/complaints/{complaint_id}/reclassify", response_model=ClassifyOut)
def operations_reclassify(
    complaint_id: UUID,
    apply_updates: bool = Query(default=True, description="Whether to update category and department in-place"),
    user: User = Depends(require_roles(*OPS_ROLES)),
    db: Session = Depends(get_db),
) -> ClassifyOut:
    """
    Run Vision / Multimodal classification on complaint evidence photo.
    Optionally updates the category and suggested department.
    """
    from app.operations.service import _get_for_user
    try:
        complaint = _get_for_user(db, user, complaint_id)
    except ComplaintError as exc:
        _raise(exc)

    photo_bytes = None
    from app.models.enums import ImageType
    if complaint.images:
        for img in complaint.images:
            if img.image_type == ImageType.before:
                photo_bytes = load_image_bytes(img.url)
                break
        if not photo_bytes and complaint.images:
            photo_bytes = load_image_bytes(complaint.images[0].url)

    result = get_classifier().classify(photo_bytes, complaint.description)
    severity, reasons = rule_severity(complaint.description or result.category.value)
    suggested_dept = department_id_for_category(result.category)

    if apply_updates:
        complaint.category = result.category
        complaint.category_confidence = result.confidence
        complaint.assigned_department_id = suggested_dept
        db.commit()

    return ClassifyOut(
        category=result.category,
        confidence=result.confidence,
        source=result.source,
        severity=severity,
        severity_reason=reasons,
        suggested_department_id=suggested_dept,
    )
