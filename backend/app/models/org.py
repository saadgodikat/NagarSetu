from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zone_name: Mapped[str] = mapped_column(String(120), unique=True)
    jurisdiction_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    wards: Mapped[list["Ward"]] = relationship(back_populates="zone")


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class Ward(Base):
    __tablename__ = "wards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ward_name: Mapped[str] = mapped_column(String(255))
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"))
    population: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sc_population: Mapped[int | None] = mapped_column(Integer, nullable=True)
    st_population: Mapped[int | None] = mapped_column(Integer, nullable=True)
    boundary_geojson: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    boundary: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    zone: Mapped[Zone] = relationship(back_populates="wards")
