import enum


class UserRole(str, enum.Enum):
    citizen = "citizen"
    field_worker = "field_worker"
    officer = "officer"
    department_head = "department_head"
    admin = "admin"


class ComplaintStatus(str, enum.Enum):
    submitted = "submitted"
    under_review = "under_review"
    assigned = "assigned"
    in_progress = "in_progress"
    resolution_submitted = "resolution_submitted"
    verified = "verified"
    closed = "closed"
    rejected = "rejected"
    reopened = "reopened"


class ComplaintCategory(str, enum.Enum):
    pothole = "pothole"
    garbage = "garbage"
    drainage = "drainage"
    streetlight = "streetlight"
    water_leakage = "water_leakage"
    other = "other"


class Severity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ImageType(str, enum.Enum):
    before = "before"
    progress = "progress"
    after = "after"


class SupportRequestStatus(str, enum.Enum):
    requested = "requested"
    approved = "approved"
    rejected = "rejected"
    fulfilled = "fulfilled"


class RelationType(str, enum.Enum):
    possible_duplicate = "possible_duplicate"
    duplicate = "duplicate"
    related = "related"
    merged = "merged"


class NotificationChannel(str, enum.Enum):
    in_app = "in_app"
    push = "push"


class NotificationStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"
