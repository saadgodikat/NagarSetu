from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import ComplaintCategory, ComplaintStatus, ImageType, Severity


class ImageOut(BaseModel):
    id: UUID
    url: str
    image_type: ImageType
    latitude: float | None = None
    longitude: float | None = None
    captured_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TimelineEventOut(BaseModel):
    action: str
    old_status: str | None
    new_status: str | None
    timestamp: datetime


class ComplaintOut(BaseModel):
    id: UUID
    title: str
    description: str
    category: ComplaintCategory
    category_confidence: float | None
    classification_source: str | None = None
    severity: Severity
    severity_reason: list | None
    priority_score: int | None
    priority_label: str | None
    priority_reasons: list | None
    ward_id: int | None
    ward_name: str | None = None
    zone_id: int | None
    location_lat: float
    location_lng: float
    assigned_department_id: int | None
    assigned_to: UUID | None = None
    assigned_to_name: str | None = None
    status: ComplaintStatus
    sla_deadline: datetime | None = None
    escalated_at: datetime | None = None
    # Phase 3 – SLA breach prediction
    breach_probability: float | None = None
    escalation_level: str | None = None
    sla_predicted_at: datetime | None = None
    # Phase 6 – Resolution verification
    verification_score: float | None = None
    verification_status: str | None = None
    verification_details: dict | None = None
    verified_at: datetime | None = None
    citizen_rating: int | None = None
    citizen_feedback: str | None = None
    created_at: datetime
    images: list[ImageOut] = Field(default_factory=list)
    timeline: list[TimelineEventOut] = Field(default_factory=list)
    related_count: int = 0

    model_config = {"from_attributes": True}


class ComplaintListOut(BaseModel):
    data: list[ComplaintOut]
    pagination: dict


class ClassifyOut(BaseModel):
    category: ComplaintCategory
    confidence: float
    source: str
    severity: Severity
    severity_reason: list[str]
    suggested_department_id: int


class SLAPredictionOut(BaseModel):
    """Response schema for the dedicated SLA prediction endpoint."""
    complaint_id: UUID
    breach_probability: float
    escalation_level: str
    source: str
    confidence_reasons: list[str]
    predicted_at: datetime


class VerificationReportOut(BaseModel):
    """Detailed response schema for multi-signal resolution verification."""
    complaint_id: UUID
    verified: bool
    status: str
    composite_score: float
    signals: dict
    recommendation: str
    flags: list[str]
    evaluated_at: str
    source: str
