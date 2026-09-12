from app.models.enums import Severity

_SEV_POINTS = {
    Severity.LOW: 10,
    Severity.MEDIUM: 20,
    Severity.HIGH: 40,
    Severity.CRITICAL: 40,
}


def score_priority(
    *,
    severity: Severity,
    related_count: int,
    duration_days: int,
    safety_risk: bool,
) -> tuple[int, str, list[str]]:
    reasons: list[str] = []
    sev = _SEV_POINTS[severity]
    if severity in (Severity.HIGH, Severity.CRITICAL):
        reasons.append("High severity")
    dur = 20 if duration_days >= 4 else 10 if duration_days >= 2 else 0
    if duration_days >= 4:
        reasons.append(f"{duration_days} days unresolved")
    dup = 15 if related_count >= 3 else 8 if related_count >= 1 else 0
    if related_count >= 3:
        reasons.append(f"{related_count} related complaints")
    safety = 25 if safety_risk else 0
    if safety_risk:
        reasons.append("Public health risk")
    score = min(100, sev + dur + dup + safety)
    if score >= 80:
        label = "critical"
    elif score >= 50:
        label = "high"
    elif score >= 25:
        label = "medium"
    else:
        label = "low"
    return score, label, reasons
