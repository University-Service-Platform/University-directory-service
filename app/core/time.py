from datetime import datetime, timezone


def utc_now() -> datetime:
    """Timezone-aware current UTC time (replaces deprecated datetime.utcnow)."""
    return datetime.now(timezone.utc)
