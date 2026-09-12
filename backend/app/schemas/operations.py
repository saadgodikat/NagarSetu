from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import ComplaintStatus


class ComplaintStatusUpdate(BaseModel):
    status: ComplaintStatus


class ComplaintAssignment(BaseModel):
    field_worker_id: UUID


class SlaPolicyUpsert(BaseModel):
    department_id: int | None = Field(default=None, ge=1)
    reminder_after_minutes: int = Field(ge=1)
    escalate_after_minutes: int = Field(ge=1)
    enabled: bool = True


class SlaPolicyOut(BaseModel):
    id: UUID
    department_id: int | None
    status: ComplaintStatus
    reminder_after_minutes: int
    escalate_after_minutes: int
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SlaRunOut(BaseModel):
    evaluated_at: datetime
    reminders_created: int
    escalations_created: int


class WorkerNoteCreate(BaseModel):
    note: str = Field(min_length=1, max_length=4000)


class SupportRequestCreate(BaseModel):
    description: str = Field(min_length=1, max_length=4000)


class ResolutionDecision(BaseModel):
    reason: str | None = Field(default=None, max_length=4000)
    rating: int | None = Field(default=None, ge=1, le=5)
    feedback: str | None = Field(default=None, max_length=4000)
