"""Time and datetime utilities.

Provides timezone-aware datetime operations with UTC as the standard.

**Feature: core-utils**
"""

from datetime import datetime, timedelta, timezone

# UTC timezone constant
UTC = timezone.utc


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(UTC)


def now(tz: timezone | None = None) -> datetime:
    """Get current datetime in the specified timezone (default: UTC)."""
    return datetime.now(tz or UTC)


def to_timestamp(dt: datetime) -> float:
    """Convert datetime to Unix timestamp."""
    return dt.timestamp()


def from_timestamp(ts: float) -> datetime:
    """Convert Unix timestamp to UTC datetime."""
    return datetime.fromtimestamp(ts, tz=UTC)


def to_iso8601(dt: datetime) -> str:
    """Convert datetime to ISO 8601 string."""
    return dt.isoformat()


def from_iso8601(s: str) -> datetime:
    """Parse ISO 8601 string to datetime."""
    # Handle both with and without timezone
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        # Try replacing Z with +00:00
        if s.endswith("Z"):
            return datetime.fromisoformat(s[:-1] + "+00:00")
        raise


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime to string."""
    return dt.strftime(fmt)


def ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime is in UTC timezone."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def start_of_day(dt: datetime) -> datetime:
    """Get start of day (00:00:00) for given datetime."""
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(dt: datetime) -> datetime:
    """Get end of day (23:59:59.999999) for given datetime."""
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def add_duration(
    dt: datetime,
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
) -> datetime:
    """Add duration to datetime."""
    return dt + timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


__all__ = [
    "UTC",
    "add_duration",
    "end_of_day",
    "ensure_utc",
    "format_datetime",
    "from_iso8601",
    "from_timestamp",
    "now",
    "start_of_day",
    "to_iso8601",
    "to_timestamp",
    "utc_now",
]
