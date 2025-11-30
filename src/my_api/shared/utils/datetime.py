"""Timezone-aware datetime utilities with ISO 8601 formatting."""

from datetime import datetime, UTC
from typing import overload

import pendulum
from pendulum import DateTime as PendulumDateTime


def utc_now() -> datetime:
    """Get current UTC datetime.

    Returns:
        datetime: Current UTC datetime with timezone info.
    """
    return pendulum.now("UTC")


def ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware UTC.

    If the datetime is naive (no timezone info), it is assumed to be UTC.
    If the datetime has a different timezone, it is converted to UTC.

    Args:
        dt: Datetime to ensure is UTC.

    Returns:
        datetime: Timezone-aware datetime in UTC.

    Example:
        >>> naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        >>> ensure_utc(naive_dt).tzinfo
        datetime.timezone.utc

        >>> aware_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        >>> ensure_utc(aware_dt) == aware_dt
        True
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def now(tz: str = "UTC") -> datetime:
    """Get current datetime in specified timezone.

    Args:
        tz: Timezone string (e.g., "UTC", "America/New_York").

    Returns:
        datetime: Current datetime in specified timezone.
    """
    return pendulum.now(tz)


@overload
def to_iso8601(dt: datetime) -> str: ...


@overload
def to_iso8601(dt: None) -> None: ...


def to_iso8601(dt: datetime | None) -> str | None:
    """Convert datetime to ISO 8601 string.

    Args:
        dt: Datetime to convert.

    Returns:
        str: ISO 8601 formatted string, or None if input is None.
    """
    if dt is None:
        return None

    # Ensure timezone awareness
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    # Convert to pendulum for consistent formatting
    if not isinstance(dt, PendulumDateTime):
        dt = pendulum.instance(dt)

    return dt.to_iso8601_string()


@overload
def from_iso8601(iso_string: str) -> datetime: ...


@overload
def from_iso8601(iso_string: None) -> None: ...


def from_iso8601(iso_string: str | None) -> datetime | None:
    """Parse ISO 8601 string to datetime.

    Args:
        iso_string: ISO 8601 formatted string.

    Returns:
        datetime: Parsed datetime with timezone info, or None if input is None.

    Raises:
        ValueError: If string is not valid ISO 8601 format.
    """
    if iso_string is None:
        return None

    try:
        return pendulum.parse(iso_string)
    except Exception as e:
        raise ValueError(f"Invalid ISO 8601 string: {iso_string}") from e


def to_timestamp(dt: datetime) -> float:
    """Convert datetime to Unix timestamp.

    Args:
        dt: Datetime to convert.

    Returns:
        float: Unix timestamp (seconds since epoch).
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.timestamp()


def from_timestamp(ts: float, tz: str = "UTC") -> datetime:
    """Convert Unix timestamp to datetime.

    Args:
        ts: Unix timestamp (seconds since epoch).
        tz: Target timezone.

    Returns:
        datetime: Datetime in specified timezone.
    """
    return pendulum.from_timestamp(ts, tz=tz)


def format_datetime(dt: datetime, fmt: str = "YYYY-MM-DD HH:mm:ss") -> str:
    """Format datetime using pendulum format string.

    Args:
        dt: Datetime to format.
        fmt: Pendulum format string.

    Returns:
        str: Formatted datetime string.
    """
    if not isinstance(dt, PendulumDateTime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        dt = pendulum.instance(dt)
    return dt.format(fmt)


def add_duration(
    dt: datetime,
    *,
    years: int = 0,
    months: int = 0,
    weeks: int = 0,
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
) -> datetime:
    """Add duration to datetime.

    Args:
        dt: Base datetime.
        years: Years to add.
        months: Months to add.
        weeks: Weeks to add.
        days: Days to add.
        hours: Hours to add.
        minutes: Minutes to add.
        seconds: Seconds to add.

    Returns:
        datetime: New datetime with duration added.
    """
    if not isinstance(dt, PendulumDateTime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        dt = pendulum.instance(dt)

    return dt.add(
        years=years,
        months=months,
        weeks=weeks,
        days=days,
        hours=hours,
        minutes=minutes,
        seconds=seconds,
    )


def start_of_day(dt: datetime) -> datetime:
    """Get start of day for given datetime.

    Args:
        dt: Input datetime.

    Returns:
        datetime: Start of day (00:00:00).
    """
    if not isinstance(dt, PendulumDateTime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        dt = pendulum.instance(dt)
    return dt.start_of("day")


def end_of_day(dt: datetime) -> datetime:
    """Get end of day for given datetime.

    Args:
        dt: Input datetime.

    Returns:
        datetime: End of day (23:59:59.999999).
    """
    if not isinstance(dt, PendulumDateTime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        dt = pendulum.instance(dt)
    return dt.end_of("day")
