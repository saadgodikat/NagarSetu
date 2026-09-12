from app.models.enums import Severity

_HIGH_KEYWORDS = (
    "danger",
    "flooded",
    "collapsed",
    "accident",
    "fire",
    "unsafe",
    "blocked",
    "contaminated",
)


def rule_severity(text: str) -> tuple[Severity, list[str]]:
    blob = (text or "").lower()
    reasons: list[str] = []
    hits = [word for word in _HIGH_KEYWORDS if word in blob]
    if hits:
        reasons.append("public health keyword detected")
    if "day" in blob and any(ch.isdigit() for ch in blob):
        reasons.append("complaint duration")
    if hits:
        return Severity.HIGH, reasons
    if reasons:
        return Severity.MEDIUM, reasons
    return Severity.MEDIUM, ["default severity"]
