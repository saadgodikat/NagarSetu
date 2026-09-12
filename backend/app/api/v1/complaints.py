from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.ai.classification import get_classifier
from app.ai.department import department_id_for_category
from app.ai.resolution_verifier import verify_complaint_resolution
from app.ai.severity import rule_severity
from app.api.deps import get_current_user, require_roles
from app.complaints.service import (
    ComplaintError,
    create_complaint,
    decide_resolution,
    get_citizen_complaint,
    list_citizen_complaints,
    to_out,
)
from app.db import get_db
from app.models.complaint import Complaint
from app.models.enums import ComplaintCategory, UserRole
from app.models.user import User
from app.schemas.complaints import ClassifyOut, ComplaintListOut, ComplaintOut, VerificationReportOut
from app.schemas.operations import ResolutionDecision

router = APIRouter(prefix="/api/v1", tags=["complaints"])


def _raise(exc: ComplaintError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/ai/classify", response_model=ClassifyOut)
def classify_complaint(
    description: str = Form(default=""),
    photo: UploadFile | None = File(default=None),
    user: User = Depends(get_current_user),
) -> ClassifyOut:
    photo_bytes = None
    if photo is not None:
        photo_bytes = photo.file.read()
    result = get_classifier().classify(photo_bytes, description)
    severity, reasons = rule_severity(description or result.category.value)
    return ClassifyOut(
        category=result.category,
        confidence=result.confidence,
        source=result.source,
        severity=severity,
        severity_reason=reasons,
        suggested_department_id=department_id_for_category(result.category),
    )


@router.post("/complaints", response_model=ComplaintOut, status_code=201)
def submit_complaint(
    title: str = Form(...),
    description: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    photo: UploadFile = File(...),
    category: ComplaintCategory | None = Form(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ComplaintOut:
    content = photo.file.read()
    try:
        complaint = create_complaint(
            db,
            citizen=user,
            title=title,
            description=description,
            latitude=latitude,
            longitude=longitude,
            photo=content,
            photo_name=photo.filename,
            photo_type=photo.content_type,
            category_override=category,
        )
    except ComplaintError as exc:
        _raise(exc)
    loaded = get_citizen_complaint(db, user, complaint.id)
    return to_out(db, loaded, include_timeline=True)


@router.get("/complaints", response_model=ComplaintListOut)
def list_complaints(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_roles(UserRole.citizen)),
    db: Session = Depends(get_db),
) -> ComplaintListOut:
    try:
        rows, total = list_citizen_complaints(db, user, page, page_size)
    except ComplaintError as exc:
        _raise(exc)
    return ComplaintListOut(
        data=[to_out(db, row, include_timeline=False) for row in rows],
        pagination={
            "page": page,
            "pageSize": page_size,
            "totalItems": total,
            "totalPages": ceil(total / page_size) if page_size else 0,
        },
    )


@router.get("/complaints/{complaint_id}", response_model=ComplaintOut)
def get_complaint(
    complaint_id: UUID,
    user: User = Depends(require_roles(UserRole.citizen)),
    db: Session = Depends(get_db),
) -> ComplaintOut:
    try:
        complaint = get_citizen_complaint(db, user, complaint_id)
    except ComplaintError as exc:
        _raise(exc)
    return to_out(db, complaint, include_timeline=True)


@router.post("/complaints/{complaint_id}/resolution/confirm", response_model=ComplaintOut)
def confirm_resolution(
    complaint_id: UUID,
    body: ResolutionDecision | None = None,
    user: User = Depends(require_roles(UserRole.citizen)),
    db: Session = Depends(get_db),
) -> ComplaintOut:
    try:
        complaint = decide_resolution(
            db,
            user,
            complaint_id,
            confirmed=True,
            reason=body.reason if body else None,
            rating=body.rating if body else None,
            feedback=body.feedback if body else None,
        )
    except ComplaintError as exc:
        _raise(exc)
    return to_out(db, complaint, include_timeline=True)


@router.post("/complaints/{complaint_id}/resolution/reject", response_model=ComplaintOut)
def reject_resolution(
    complaint_id: UUID,
    body: ResolutionDecision,
    user: User = Depends(require_roles(UserRole.citizen)),
    db: Session = Depends(get_db),
) -> ComplaintOut:
    try:
        complaint = decide_resolution(
            db,
            user,
            complaint_id,
            confirmed=False,
            reason=body.reason,
            rating=body.rating,
            feedback=body.feedback,
        )
    except ComplaintError as exc:
        _raise(exc)
    return to_out(db, complaint, include_timeline=True)


@router.get("/complaints/{complaint_id}/verification", response_model=VerificationReportOut)
def get_complaint_verification(
    complaint_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VerificationReportOut:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if user.role == UserRole.citizen and complaint.citizen_id != user.id:
        raise HTTPException(status_code=404, detail="Complaint not found")

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


@router.post("/ai/verification", response_model=VerificationReportOut)
def ai_verification(
    complaint_id: UUID = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VerificationReportOut:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if user.role == UserRole.citizen and complaint.citizen_id != user.id:
        raise HTTPException(status_code=404, detail="Complaint not found")

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
