from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.complaints.service import ComplaintError, to_out
from app.db import get_db
from app.models.enums import ComplaintStatus, UserRole
from app.models.user import User
from app.schemas.complaints import ComplaintListOut, ComplaintOut
from app.schemas.operations import SupportRequestCreate, WorkerNoteCreate
from app.worker.service import (
    add_note,
    add_resolution_photo,
    add_support_request,
    get_task,
    list_tasks,
    update_task_status,
)

router = APIRouter(prefix="/api/v1/worker", tags=["worker"])


def _raise(exc: ComplaintError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/complaints", response_model=ComplaintListOut)
def tasks(
    worker: User = Depends(require_roles(UserRole.field_worker)),
    db: Session = Depends(get_db),
) -> ComplaintListOut:
    rows = list_tasks(db, worker)
    return ComplaintListOut(
        data=[to_out(db, row, include_timeline=False) for row in rows],
        pagination={"page": 1, "pageSize": len(rows), "totalItems": len(rows), "totalPages": 1},
    )


@router.get("/complaints/{complaint_id}", response_model=ComplaintOut)
def task_detail(
    complaint_id: UUID,
    worker: User = Depends(require_roles(UserRole.field_worker)),
    db: Session = Depends(get_db),
) -> ComplaintOut:
    try:
        return to_out(db, get_task(db, worker, complaint_id), include_timeline=True)
    except ComplaintError as exc:
        _raise(exc)


@router.patch("/complaints/{complaint_id}/status", response_model=ComplaintOut)
def set_task_status(
    complaint_id: UUID,
    status: ComplaintStatus,
    worker: User = Depends(require_roles(UserRole.field_worker)),
    db: Session = Depends(get_db),
) -> ComplaintOut:
    try:
        return to_out(db, update_task_status(db, worker, complaint_id, status), include_timeline=True)
    except ComplaintError as exc:
        _raise(exc)


@router.post("/complaints/{complaint_id}/notes", response_model=ComplaintOut)
def note(
    complaint_id: UUID,
    body: WorkerNoteCreate,
    worker: User = Depends(require_roles(UserRole.field_worker)),
    db: Session = Depends(get_db),
) -> ComplaintOut:
    try:
        return to_out(db, add_note(db, worker, complaint_id, body.note), include_timeline=True)
    except ComplaintError as exc:
        _raise(exc)


@router.post("/complaints/{complaint_id}/support-requests", response_model=ComplaintOut)
def support_request(
    complaint_id: UUID,
    body: SupportRequestCreate,
    worker: User = Depends(require_roles(UserRole.field_worker)),
    db: Session = Depends(get_db),
) -> ComplaintOut:
    try:
        return to_out(
            db,
            add_support_request(db, worker, complaint_id, body.description),
            include_timeline=True,
        )
    except ComplaintError as exc:
        _raise(exc)


@router.post("/complaints/{complaint_id}/resolution-photo", response_model=ComplaintOut)
def resolution_photo(
    complaint_id: UUID,
    photo: UploadFile = File(...),
    latitude: float | None = Form(default=None),
    longitude: float | None = Form(default=None),
    worker: User = Depends(require_roles(UserRole.field_worker)),
    db: Session = Depends(get_db),
) -> ComplaintOut:
    try:
        return to_out(
            db,
            add_resolution_photo(
                db,
                worker,
                complaint_id,
                photo.file.read(),
                photo.filename,
                photo.content_type,
                latitude=latitude,
                longitude=longitude,
            ),
            include_timeline=True,
        )
    except ComplaintError as exc:
        _raise(exc)
