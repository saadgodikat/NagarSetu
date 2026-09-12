from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import models as _models  # noqa: F401
from app.auth.security import hash_password
from app.db import Base, SessionLocal, engine
from app.geo.lookup import apply_geometry, demo_ward1_polygon
from app.main import app
from app.models.enums import UserRole
from app.models.org import Ward
from seeds.seed import seed_catalog


def postgres_ready() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not postgres_ready(), reason="PostgreSQL is not running")
client = TestClient(app)


def _setup() -> None:
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
        from app.models.user import User

        db.add(
            User(
                name=f"{role.value} analytics tester",
                email=email,
                password_hash=hash_password(password),
                role=role,
                department_id=department_id,
            )
        )
        db.commit()
        return email, password
    finally:
        db.close()


def _token(email: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _complaint(token: str, title: str) -> None:
    response = client.post(
        "/api/v1/complaints",
        headers=_auth(token),
        data={
            "title": title,
            "description": "Garbage collection issue needs attention.",
            "latitude": "17.6599",
            "longitude": "75.9064",
        },
        files={"photo": ("issue.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )
    assert response.status_code == 201, response.text


def test_admin_can_view_citywide_analytics_and_citizen_cannot() -> None:
    _setup()
    citizen_email, citizen_password = _user(UserRole.citizen)
    admin_email, admin_password = _user(UserRole.admin)
    citizen_token = _token(citizen_email, citizen_password)
    _complaint(citizen_token, "Analytics complaint")

    admin_response = client.get(
        "/api/v1/analytics/summary",
        headers=_auth(_token(admin_email, admin_password)),
    )
    assert admin_response.status_code == 200, admin_response.text
    body = admin_response.json()
    assert body["total_complaints"] >= 1
    assert body["open_complaints"] >= 1
    assert body["status_breakdown"]["submitted"] >= 1
    assert any(item["category"] == "garbage" for item in body["emerging_issues"])
    assert any(item["ward_id"] == 1 for item in body["ward_distribution"])

    denied = client.get("/api/v1/analytics/summary", headers=_auth(citizen_token))
    assert denied.status_code == 403


def test_officer_analytics_are_department_scoped() -> None:
    _setup()
    citizen_email, citizen_password = _user(UserRole.citizen)
    officer_email, officer_password = _user(UserRole.officer, department_id=1)
    _complaint(_token(citizen_email, citizen_password), "Department analytics complaint")

    response = client.get(
        "/api/v1/analytics/summary",
        headers=_auth(_token(officer_email, officer_password)),
    )
    assert response.status_code == 200, response.text
    assert all(
        item["department_id"] == 1
        for item in response.json()["department_workload"]
    )
