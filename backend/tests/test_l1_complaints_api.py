from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth.security import hash_password
from app.config import settings
from app.db import SessionLocal, engine
from app.geo.lookup import apply_geometry, demo_ward1_polygon
from app.main import app
from app.models.enums import UserRole
from app.models.org import Ward
from app.models.user import User
from seeds.seed import seed_catalog
from app.db import Base
from app import models as _models  # noqa: F401

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def postgres_ready() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            conn.commit()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not postgres_ready(), reason="PostgreSQL/PostGIS is not running")

client = TestClient(app)


def _ensure_schema_and_geo() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_catalog(db)
        ward = db.get(Ward, 1)
        if ward and ward.boundary is None:
            apply_geometry(db, ward, demo_ward1_polygon())
            db.commit()
    finally:
        db.close()


def _user(role: UserRole, department_id: int | None = None) -> tuple[str, str]:
    email = f"{role.value}-{uuid4().hex[:8]}@demo.solapur"
    password = "Demo@1234"
    db = SessionLocal()
    try:
        db.add(
            User(
                name=f"{role.value} tester",
                email=email,
                phone=None,
                password_hash=hash_password(password),
                role=role,
                department_id=department_id,
            )
        )
        db.commit()
    finally:
        db.close()
    return email, password


def _token(email: str, password: str) -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_citizen_submits_and_reads_timeline() -> None:
    _ensure_schema_and_geo()
    email, password = _user(UserRole.citizen)
    officer_email, officer_password = _user(UserRole.officer, department_id=1)
    token = _token(email, password)
    _token(officer_email, officer_password)

    res = client.post(
        "/api/v1/complaints",
        headers=_auth(token),
        data={
            "title": "Garbage not collected for 4 days",
            "description": "Garbage has not been collected for 4 days near Tuljapur Naka. It's unsafe.",
            "latitude": "17.6599",
            "longitude": "75.9064",
        },
        files={"photo": ("dump.png", PNG, "image/png")},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "submitted"
    assert body["category"] == "garbage"
    assert body["ward_id"] == 1
    assert body["assigned_department_id"] == 1
    assert body["images"]
    assert body["timeline"]
    assert body["timeline"][0]["action"] == "complaint_submitted"
    complaint_id = body["id"]

    listed = client.get("/api/v1/complaints", headers=_auth(token))
    assert listed.status_code == 200
    assert listed.json()["pagination"]["totalItems"] >= 1
    assert any(item["id"] == complaint_id for item in listed.json()["data"])

    detail = client.get(f"/api/v1/complaints/{complaint_id}", headers=_auth(token))
    assert detail.status_code == 200
    assert detail.json()["timeline"][0]["new_status"] == "submitted"


def test_citizen_cannot_read_another_citizens_complaint() -> None:
    _ensure_schema_and_geo()
    a_email, a_pass = _user(UserRole.citizen)
    b_email, b_pass = _user(UserRole.citizen)
    a_token, b_token = _token(a_email, a_pass), _token(b_email, b_pass)
    created = client.post(
        "/api/v1/complaints",
        headers=_auth(a_token),
        data={
            "title": "Pothole",
            "description": "Deep pothole near City Mall entrance",
            "latitude": "17.6700",
            "longitude": "75.9100",
        },
        files={"photo": ("hole.png", PNG, "image/png")},
    )
    assert created.status_code == 201, created.text
    cid = created.json()["id"]
    peek = client.get(f"/api/v1/complaints/{cid}", headers=_auth(b_token))
    assert peek.status_code == 404


def test_field_worker_cannot_submit_complaint() -> None:
    _ensure_schema_and_geo()
    email, password = _user(UserRole.field_worker, department_id=1)
    token = _token(email, password)
    res = client.post(
        "/api/v1/complaints",
        headers=_auth(token),
        data={
            "title": "Nope",
            "description": "Workers should not open citizen tickets",
            "latitude": "17.6599",
            "longitude": "75.9064",
        },
        files={"photo": ("x.png", PNG, "image/png")},
    )
    assert res.status_code == 403


def test_unauthenticated_submit_is_rejected() -> None:
    res = client.post(
        "/api/v1/complaints",
        data={
            "title": "Nope",
            "description": "Missing auth",
            "latitude": "17.6599",
            "longitude": "75.9064",
        },
        files={"photo": ("x.png", PNG, "image/png")},
    )
    assert res.status_code == 401


def test_rejects_non_image_upload() -> None:
    _ensure_schema_and_geo()
    email, password = _user(UserRole.citizen)
    token = _token(email, password)
    res = client.post(
        "/api/v1/complaints",
        headers=_auth(token),
        data={
            "title": "Bad file",
            "description": "Garbage pile",
            "latitude": "17.6599",
            "longitude": "75.9064",
        },
        files={"photo": ("note.txt", b"hello", "text/plain")},
    )
    assert res.status_code == 422


def test_outside_polygon_still_creates_without_invented_ward() -> None:
    _ensure_schema_and_geo()
    email, password = _user(UserRole.citizen)
    token = _token(email, password)
    res = client.post(
        "/api/v1/complaints",
        headers=_auth(token),
        data={
            "title": "Far away",
            "description": "Garbage dumped far from Solapur",
            "latitude": "0.0",
            "longitude": "0.0",
        },
        files={"photo": ("g.png", PNG, "image/png")},
    )
    assert res.status_code == 201, res.text
    assert res.json()["ward_id"] is None
