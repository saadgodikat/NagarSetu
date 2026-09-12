from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.assistant.service import AssistantUnsupportedQuestion, query
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.assistant import AssistantAnswerOut, AssistantQueryIn

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])
ASSISTANT_ROLES = (UserRole.officer, UserRole.department_head, UserRole.admin)


@router.post("/query", response_model=AssistantAnswerOut)
def assistant_query(
    body: AssistantQueryIn,
    user: User = Depends(require_roles(*ASSISTANT_ROLES)),
    db: Session = Depends(get_db),
) -> AssistantAnswerOut:
    try:
        return query(db, user, body.question)
    except AssistantUnsupportedQuestion as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
