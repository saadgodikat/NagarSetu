from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.geo.lookup import lookup_ward_id
from app.models.org import Department, Ward, Zone
from app.models.user import User
from app.schemas.common import DepartmentOut, UserOut, WardOut, ZoneOut

users_router = APIRouter(prefix="/api/v1/users", tags=["users"])
wards_router = APIRouter(prefix="/api/v1/wards", tags=["geo"])
zones_router = APIRouter(prefix="/api/v1/zones", tags=["geo"])
departments_router = APIRouter(prefix="/api/v1/departments", tags=["org"])


@users_router.get("/me", response_model=UserOut)
def users_me(user: User = Depends(get_current_user)) -> User:
    return user


@wards_router.get("/lookup")
def lookup_ward(
    lat: float = Query(...),
    lng: float = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    ward_id = lookup_ward_id(db, lng, lat)
    if ward_id is None:
        raise HTTPException(status_code=404, detail="No ward polygon contains this point")
    ward = db.get(Ward, ward_id)
    assert ward is not None
    return {"ward_id": ward.id, "ward_name": ward.ward_name, "zone_id": ward.zone_id}


@wards_router.get("", response_model=list[WardOut])
def list_wards(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[WardOut]:
    wards = db.scalars(select(Ward).order_by(Ward.id)).all()
    return [
        WardOut(
            id=w.id,
            ward_name=w.ward_name,
            zone_id=w.zone_id,
            population=w.population,
            sc_population=w.sc_population,
            st_population=w.st_population,
            has_boundary=w.boundary is not None,
        )
        for w in wards
    ]


@zones_router.get("", response_model=list[ZoneOut])
def list_zones(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[Zone]:
    return list(db.scalars(select(Zone).order_by(Zone.id)).all())


@departments_router.get("", response_model=list[DepartmentOut])
def list_departments(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[Department]:
    return list(db.scalars(select(Department).order_by(Department.id)).all())
