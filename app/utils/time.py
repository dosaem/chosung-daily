from datetime import UTC, datetime


def utcnow() -> datetime:
    """DB에는 naive UTC로 저장한다 (MySQL DATETIME은 타임존을 안 들고 있음)."""
    return datetime.now(UTC).replace(tzinfo=None)
