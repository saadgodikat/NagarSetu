import uuid
from pathlib import Path

from app.config import settings

ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_BYTES = 5 * 1024 * 1024
_MAGIC = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"RIFF", "image/webp"),
)


def validate_image(content: bytes, filename: str | None, content_type: str | None) -> tuple[bool, str]:
    if not content:
        return False, "empty file"
    if len(content) > MAX_BYTES:
        return False, "file too large"
    sniffed = _sniff(content)
    declared = (content_type or "").split(";")[0].strip().lower()
    if sniffed is None:
        return False, "unsupported image type"
    if declared and declared not in ALLOWED_TYPES and declared != "application/octet-stream":
        return False, "unsupported image type"
    if declared in ALLOWED_TYPES and declared != sniffed:
        return False, "content type does not match file"
    return True, sniffed


def _sniff(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"RIFF") and b"WEBP" in content[:16]:
        return "image/webp"
    return None


def save_image(content: bytes, content_type: str) -> str:
    ext = ALLOWED_TYPES[content_type]
    upload_root = Path(settings.upload_dir).resolve()
    upload_root.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    path = upload_root / name
    path.write_bytes(content)
    return f"/uploads/{name}"
