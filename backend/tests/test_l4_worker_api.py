from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import models as _models  # noqa: F401
from app.auth.security import hash_password
from app.db import Base, SessionLocal, engine
from app.main import app
from app.models.enums import UserRole
from app.models.org import Ward
from app.geo.lookup import apply_geometry, demo_ward1_polygon
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


def _user(role: UserRole, department_id: int | None = None) -> tuple[str, str, str]:
    email = f"{role.value}-{uuid4().hex[:8]}@demo.solapur"
    password = "Demo@1234"
    db = SessionLocal()
    try:
        from app.models.user import User

        user = User(
            name=f"{role.value} tester",
            email=email,
            password_hash=hash_password(password),
            role=role,
            department_id=department_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return email, password, str(user.id)
    finally:
        db.close()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + token}


def _token(email: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_worker_can_update_assigned_task_and_submit_resolution_photo() -> None:
    _setup()
    citizen_email, citizen_password, _ = _user(UserRole.citizen)
    officer_email, officer_password, _ = _user(UserRole.officer, department_id=1)
    worker_email, worker_password, worker_id = _user(UserRole.field_worker, department_id=1)
    citizen_token = _token(citizen_email, citizen_password)
    complaint = client.post(
        "/api/v1/complaints",
        headers=_auth(citizen_token),
        data={
            "title": "Worker task",
            "description": "Garbage needs field work.",
            "latitude": "17.6599",
            "longitude": "75.9064",
        },
        files={"photo": ("before.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )
    assert complaint.status_code == 201, complaint.text
    complaint_id = complaint.json()["id"]
    officer_token = _token(officer_email, officer_password)
    assert client.patch(
        f"/api/v1/operations/complaints/{complaint_id}/status",
        headers=_auth(officer_token),
        json={"status": "under_review"},
    ).status_code == 200
    assert client.post(
        f"/api/v1/operations/complaints/{complaint_id}/assign",
        headers=_auth(officer_token),
        json={"field_worker_id": worker_id},
    ).status_code == 200

    worker_token = _token(worker_email, worker_password)
    queue = client.get("/api/v1/worker/complaints", headers=_auth(worker_token))
    assert queue.status_code == 200
    assert [item["id"] for item in queue.json()["data"]] == [complaint_id]

    started = client.patch(
        f"/api/v1/worker/complaints/{complaint_id}/status?status=in_progress",
        headers=_auth(worker_token),
    )
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "in_progress"

    noted = client.post(
        f"/api/v1/worker/complaints/{complaint_id}/notes",
        headers=_auth(worker_token),
        json={"note": "Arrived at site and started work."},
    )
    assert noted.status_code == 200, noted.text

    resolved = client.post(
        f"/api/v1/worker/complaints/{complaint_id}/resolution-photo",
        headers=_auth(worker_token),
        files={"photo": ("after.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "in_progress"
    assert any(image["image_type"] == "after" for image in resolved.json()["images"])

    completed = client.patch(
        f"/api/v1/worker/complaints/{complaint_id}/status?status=resolution_submitted",
        headers=_auth(worker_token),
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "resolution_submitted"

    confirmed = client.post(
        f"/api/v1/complaints/{complaint_id}/resolution/confirm",
        headers=_auth(citizen_token),
        json={},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "closed"
    assert any(event["action"] == "resolution_confirmed" for event in confirmed.json()["timeline"])


def test_worker_cannot_access_another_workers_task() -> None:
    _setup()
    citizen_email, citizen_password, _ = _user(UserRole.citizen)
    officer_email, officer_password, _ = _user(UserRole.officer, department_id=1)
    worker_email, worker_password, worker_id = _user(UserRole.field_worker, department_id=1)
    other_email, other_password, _ = _user(UserRole.field_worker, department_id=1)
    complaint = client.post(
        "/api/v1/complaints",
        headers=_auth(_token(citizen_email, citizen_password)),
        data={
            "title": "Private worker task",
            "description": "Garbage needs assigned work.",
            "latitude": "17.6599",
            "longitude": "75.9064",
        },
        files={"photo": ("before.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )
    complaint_id = complaint.json()["id"]
    officer_token = _token(officer_email, officer_password)
    client.patch(
        f"/api/v1/operations/complaints/{complaint_id}/status",
        headers=_auth(officer_token),
        json={"status": "under_review"},
    )
    client.post(
        f"/api/v1/operations/complaints/{complaint_id}/assign",
        headers=_auth(officer_token),
        json={"field_worker_id": worker_id},
    )

    other_token = _token(other_email, other_password)
    detail = client.get(
        f"/api/v1/worker/complaints/{complaint_id}",
        headers=_auth(other_token),
    )
    assert detail.status_code == 404
