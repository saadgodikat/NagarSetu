from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.analytics.service import get_summary
from app.api.deps import get_db, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.analytics import AnalyticsSummaryOut

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])
ANALYTICS_ROLES = (UserRole.officer, UserRole.department_head, UserRole.admin)


@router.get("/summary", response_model=AnalyticsSummaryOut)
def summary(
    department_id: int | None = Query(default=None, ge=1),
    user: User = Depends(require_roles(*ANALYTICS_ROLES)),
    db: Session = Depends(get_db),
) -> AnalyticsSummaryOut:
    if user.role != UserRole.admin and user.department_id is None:
        raise HTTPException(status_code=403, detail="Department access denied")
    return get_summary(db, user, department_id=department_id)
