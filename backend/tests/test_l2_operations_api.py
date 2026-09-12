from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app import models as _models  # noqa: F401
from app.auth.security import hash_password
from app.db import Base, SessionLocal, engine
from app.main import app
from app.models.enums import UserRole
from app.models.org import Ward
from app.models.ops import AuditLog, SlaAudit
from app.models.user import User
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


def _token(email: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_complaint(token: str) -> str:
    response = client.post(
        "/api/v1/complaints",
        headers=_auth(token),
        data={
            "title": "Garbage queue for triage",
            "description": "Garbage has not been collected and is unsafe.",
            "latitude": "17.6599",
            "longitude": "75.9064",
        },
        files={"photo": ("dump.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_officer_can_review_and_assign_department_worker() -> None:
    _setup()
    citizen_email, citizen_password, _ = _user(UserRole.citizen)
    officer_email, officer_password, _ = _user(UserRole.officer, department_id=1)
    worker_email, worker_password, worker_id = _user(UserRole.field_worker, department_id=1)
    complaint_id = _create_complaint(_token(citizen_email, citizen_password))
    officer_token = _token(officer_email, officer_password)

    queue = client.get("/api/v1/operations/complaints", headers=_auth(officer_token))
    assert queue.status_code == 200
    assert any(item["id"] == complaint_id for item in queue.json()["data"])

    reviewed = client.patch(
        f"/api/v1/operations/complaints/{complaint_id}/status",
        headers=_auth(officer_token),
        json={"status": "under_review"},
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["status"] == "under_review"

    assigned = client.post(
        f"/api/v1/operations/complaints/{complaint_id}/assign",
        headers=_auth(officer_token),
        json={"field_worker_id": worker_id},
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["status"] == "assigned"
    assert assigned.json()["assigned_to"] == worker_id
    assert any(event["action"] == "complaint_assigned" for event in assigned.json()["timeline"])


def test_officer_cannot_view_other_department_queue() -> None:
    _setup()
    citizen_email, citizen_password, _ = _user(UserRole.citizen)
    officer_email, officer_password, _ = _user(UserRole.officer, department_id=2)
    complaint_id = _create_complaint(_token(citizen_email, citizen_password))
    officer_token = _token(officer_email, officer_password)

    detail = client.get(
        f"/api/v1/operations/complaints/{complaint_id}",
        headers=_auth(officer_token),
    )
    assert detail.status_code == 403


def test_department_can_configure_and_run_sla_without_duplicate_alerts() -> None:
    _setup()
    citizen_email, citizen_password, _ = _user(UserRole.citizen)
    officer_email, officer_password, _ = _user(UserRole.officer, department_id=1)
    complaint_id = _create_complaint(_token(citizen_email, citizen_password))
    officer_token = _token(officer_email, officer_password)

    policy = client.put(
        "/api/v1/operations/sla/policies/submitted",
        headers=_auth(officer_token),
        json={
            "department_id": 1,
            "reminder_after_minutes": 1,
            "escalate_after_minutes": 2,
            "enabled": True,
        },
    )
    assert policy.status_code == 200, policy.text
    assert policy.json()["department_id"] == 1

    db = SessionLocal()
    try:
        submitted_at = datetime.now(timezone.utc) - timedelta(minutes=3)
        db.query(AuditLog).filter(
            AuditLog.complaint_id == complaint_id,
            AuditLog.action == "complaint_submitted",
        ).update({"timestamp": submitted_at})
        db.commit()
    finally:
        db.close()

    first_run = client.post("/api/v1/operations/sla/run", headers=_auth(officer_token))
    assert first_run.status_code == 200, first_run.text
    assert first_run.json()["reminders_created"] >= 1
    assert first_run.json()["escalations_created"] >= 1

    second_run = client.post("/api/v1/operations/sla/run", headers=_auth(officer_token))
    assert second_run.status_code == 200, second_run.text
    assert second_run.json()["reminders_created"] == 0
    assert second_run.json()["escalations_created"] == 0

    db = SessionLocal()
    try:
        audits = db.scalars(select(SlaAudit).where(SlaAudit.complaint_id == complaint_id)).all()
        assert {audit.sla_type for audit in audits} == {"reminder", "escalation"}
    finally:
        db.close()
