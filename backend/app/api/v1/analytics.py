from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.analytics.service import get_summary
from app.api.deps import get_db, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.analytics import AnalyticsSummaryOut

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])
ANALYTICS_ROLES = (UserRole.officer, UserRole.department_head, UserRole.admin)


class CrisisAlertOut(BaseModel):
    category: str
    ward_id: int | None
    ward_name: str
    current_count: int
    previous_count: int
    pct_increase: float
    open_count: int
    recommendation: str
    severity: str


@router.get("/emerging-crises", response_model=list[CrisisAlertOut])
def emerging_crises(
    window_hours: int = Query(default=24, ge=1, le=168),
    spike_threshold_pct: float = Query(default=100.0, ge=10.0),
    department_id: int | None = Query(default=None, ge=1),
    user: User = Depends(require_roles(*ANALYTICS_ROLES)),
    db: Session = Depends(get_db),
) -> list[CrisisAlertOut]:
    from app.analytics.emerging_crisis import detect_emerging_crises
    if user.role != UserRole.admin:
        department_id = user.department_id
    alerts = detect_emerging_crises(
        db,
        window_hours=window_hours,
        spike_threshold_pct=spike_threshold_pct,
        department_id=department_id,
    )
    return [CrisisAlertOut(**vars(a)) for a in alerts]


@router.get("/summary", response_model=AnalyticsSummaryOut)
def summary(
    department_id: int | None = Query(default=None, ge=1),
    user: User = Depends(require_roles(*ANALYTICS_ROLES)),
    db: Session = Depends(get_db),
) -> AnalyticsSummaryOut:
    if user.role != UserRole.admin and user.department_id is None:
        raise HTTPException(status_code=403, detail="Department access denied")
    return get_summary(db, user, department_id=department_id)
