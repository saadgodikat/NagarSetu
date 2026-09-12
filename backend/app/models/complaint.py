import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import ComplaintCategory, ComplaintStatus, ImageType, Severity


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    citizen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)

    category: Mapped[ComplaintCategory] = mapped_column(
        Enum(ComplaintCategory, name="complaint_category"), default=ComplaintCategory.other
    )
    category_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    severity: Mapped[Severity] = mapped_column(Enum(Severity, name="severity"), default=Severity.MEDIUM)
    severity_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    severity_reason: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    priority_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    priority_reasons: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    ward_id: Mapped[int | None] = mapped_column(ForeignKey("wards.id"), nullable=True)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("zones.id"), nullable=True)
    location_lat: Mapped[float] = mapped_column(Float)
    location_lng: Mapped[float] = mapped_column(Float)

    assigned_department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    status: Mapped[ComplaintStatus] = mapped_column(
        Enum(ComplaintStatus, name="complaint_status"), default=ComplaintStatus.submitted, index=True
    )
    sla_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Phase 3 – SLA breach prediction
    breach_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    escalation_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sla_predicted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Phase 6 – Multi-signal resolution verification
    verification_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    verification_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    verification_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    citizen_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    citizen_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    images: Mapped[list["Image"]] = relationship(back_populates="complaint")


class Image(Base):
    __tablename__ = "images"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complaint_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("complaints.id"), index=True)
    url: Mapped[str] = mapped_column(String(1024))
    image_type: Mapped[ImageType] = mapped_column(Enum(ImageType, name="image_type"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    verification_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    verification_result: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    complaint: Mapped[Complaint] = relationship(back_populates="images")
