import re
from collections import Counter
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.service import TERMINAL_STATUSES
from app.models.complaint import Complaint
from app.models.enums import ComplaintStatus
from app.models.org import Department, Ward
from app.models.user import User
from app.schemas.assistant import AssistantAnswerOut

SUPPORTED_QUESTIONS = [
    "What are the major unresolved problems in Ward 1?",
    "Which department has the highest workload?",
    "Which wards have the most complaints?",
    "Why is this complaint high priority?",
    "Generate today's operational summary.",
]

QUESTION_PATTERNS = {
    "ward_problems": re.compile(r"\b(major|unresolved|problems|issues).*\bward\s*1\b", re.I),
    "highest_department_workload": re.compile(r"\bdepartment\b.*\b(highest|most|workload)\b", re.I),
    "top_wards": re.compile(r"\bwards?\b.*\b(most|highest|complaints)\b", re.I),
    "priority_explanation": re.compile(r"\bwhy\b.*\bcomplaint\b.*\b(priority|prioritized)\b", re.I),
    "operational_summary": re.compile(r"\b(today|operational summary|daily summary)\b", re.I),
}


class AssistantUnsupportedQuestion(Exception):
    pass


def _scope(user: User) -> int | None:
    return None if user.role.value == "admin" else user.department_id


def _complaints(db: Session, user: User) -> list[Complaint]:
    department_id = _scope(user)
    filters = [Complaint.assigned_department_id == department_id] if department_id is not None else []
    return list(db.scalars(select(Complaint).where(*filters)).all())


def _answer(question: str, intent: str, answer: str, data: dict) -> AssistantAnswerOut:
    return AssistantAnswerOut(
        question=question,
        intent=intent,
        answer=answer,
        data=data,
        supported_questions=SUPPORTED_QUESTIONS,
    )


def query(db: Session, user: User, question: str) -> AssistantAnswerOut:
    normalized = " ".join(question.split())
    intent = next(
        (name for name, pattern in QUESTION_PATTERNS.items() if pattern.search(normalized)),
        None,
    )
    if intent is None:
        raise AssistantUnsupportedQuestion(
            "I can answer only the supported operational questions shown in the response."
        )

    complaints = _complaints(db, user)
    if intent == "ward_problems":
        rows = [
            item for item in complaints
            if item.ward_id == 1 and item.status not in TERMINAL_STATUSES
        ]
        categories = Counter(item.category.value for item in rows)
        data = {
            "ward_id": 1,
            "unresolved_count": len(rows),
            "category_counts": dict(categories),
            "complaints": [{"id": str(item.id), "title": item.title, "status": item.status.value} for item in rows[:10]],
        }
        return _answer(
            normalized,
            intent,
            f"Ward 1 has {len(rows)} unresolved complaint(s), led by "
            f"{categories.most_common(1)[0][0] if categories else 'no recorded category'}.",
            data,
        )

    if intent in {"highest_department_workload", "top_wards"}:
        counts = Counter(
            item.assigned_department_id if intent == "highest_department_workload" else item.ward_id
            for item in complaints
        )
        winner = counts.most_common(1)[0] if counts else (None, 0)
        if intent == "highest_department_workload":
            department = db.get(Department, winner[0]) if winner[0] is not None else None
            data = {"department_id": winner[0], "department_name": department.name if department else "Unassigned", "total": winner[1]}
            return _answer(normalized, intent, f"{data['department_name']} has the highest workload with {winner[1]} complaint(s).", data)
        ward = db.get(Ward, winner[0]) if winner[0] is not None else None
        data = {"ward_id": winner[0], "ward_name": ward.ward_name if ward else "Ward not mapped", "total": winner[1]}
        return _answer(normalized, intent, f"{data['ward_name']} has the most complaints with {winner[1]}.", data)

    if intent == "priority_explanation":
        match = re.search(r"\b[0-9a-f]{8}-[0-9a-f-]{27,}\b", normalized, re.I)
        if match is None:
            raise AssistantUnsupportedQuestion("Include the complaint UUID to explain its priority.")
        complaint = db.get(Complaint, UUID(match.group(0)))
        if complaint is None or (_scope(user) is not None and complaint.assigned_department_id != _scope(user)):
            raise AssistantUnsupportedQuestion("That complaint is not available in your operational scope.")
        reasons = complaint.priority_reasons or []
        data = {"complaint_id": str(complaint.id), "priority_score": complaint.priority_score, "priority_label": complaint.priority_label, "reasons": reasons}
        return _answer(normalized, intent, f"Priority is {complaint.priority_label or 'not set'} ({complaint.priority_score or 0}) because " + (", ".join(map(str, reasons)) if reasons else "no reasons were recorded") + ".", data)

    open_rows = [item for item in complaints if item.status not in TERMINAL_STATUSES]
    overdue = [item for item in open_rows if item.sla_deadline and item.sla_deadline < datetime.now(timezone.utc)]
    data = {"total": len(complaints), "open": len(open_rows), "overdue": len(overdue), "unassigned": sum(item.assigned_to is None for item in open_rows)}
    return _answer(normalized, intent, f"There are {data['open']} open complaint(s), {data['overdue']} overdue, and {data['unassigned']} unassigned.", data)
