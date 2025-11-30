"""Timezone handling utilities.

Provides timezone conversion and user timezone management.

**Feature: api-architecture-analysis, Property 6: Timezone handling**
**Validates: Requirements 4.4**
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo


class CommonTimezone(str, Enum):
    """Common timezone identifiers."""

    UTC = "UTC"
    US_EASTERN = "America/New_York"
    US_PACIFIC = "America/Los_Angeles"
    US_CENTRAL = "America/Chicago"
    EUROPE_LONDON = "Europe/London"
    EUROPE_PARIS = "Europe/Paris"
    EUROPE_BERLIN = "Europe/Berlin"
    ASIA_TOKYO = "Asia/Tokyo"
    ASIA_SHANGHAI = "Asia/Shanghai"
    ASIA_SINGAPORE = "Asia/Singapore"
    AUSTRALIA_SYDNEY = "Australia/Sydney"
    BRAZIL_SAO_PAULO = "America/Sao_Paulo"


@dataclass(frozen=True, slots=True)
class TimezoneInfo:
    """Information about a timezone."""

    name: str
    offset: timedelta
    dst_offset: timedelta | None
    abbreviation: str

    @property
    def offset_hours(self) -> float:
        """Get offset in hours."""
        return self.offset.total_seconds() / 3600

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "offset": str(self.offset),
            "offset_hours": self.offset_hours,
            "abbreviation": self.abbreviation,
        }


def get_timezone_info(tz_name: str, dt: datetime | None = None) -> TimezoneInfo:
    """Get information about a timezone."""
    tz = ZoneInfo(tz_name)
    reference_dt = dt or datetime.now(tz)
    offset = reference_dt.utcoffset() or timedelta()
    dst = reference_dt.dst()
    abbr = reference_dt.strftime("%Z")

    return TimezoneInfo(
        name=tz_name,
        offset=offset,
        dst_offset=dst,
        abbreviation=abbr,
    )


def convert_timezone(
    dt: datetime,
    from_tz: str | ZoneInfo,
    to_tz: str | ZoneInfo,
) -> datetime:
    """Convert datetime from one timezone to another."""
    if isinstance(from_tz, str):
        from_tz = ZoneInfo(from_tz)
    if isinstance(to_tz, str):
        to_tz = ZoneInfo(to_tz)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=from_tz)
    else:
        dt = dt.astimezone(from_tz)

    return dt.astimezone(to_tz)


def to_utc(dt: datetime, source_tz: str | ZoneInfo | None = None) -> datetime:
    """Convert datetime to UTC."""
    if dt.tzinfo is None:
        if source_tz is None:
            dt = dt.replace(tzinfo=UTC)
        else:
            if isinstance(source_tz, str):
                source_tz = ZoneInfo(source_tz)
            dt = dt.replace(tzinfo=source_tz)
    return dt.astimezone(UTC)


def from_utc(dt: datetime, target_tz: str | ZoneInfo) -> datetime:
    """Convert UTC datetime to target timezone."""
    if isinstance(target_tz, str):
        target_tz = ZoneInfo(target_tz)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    return dt.astimezone(target_tz)


def now_in_timezone(tz: str | ZoneInfo) -> datetime:
    """Get current time in specified timezone."""
    if isinstance(tz, str):
        tz = ZoneInfo(tz)
    return datetime.now(tz)


def format_datetime(
    dt: datetime,
    fmt: str = "%Y-%m-%d %H:%M:%S %Z",
    tz: str | ZoneInfo | None = None,
) -> str:
    """Format datetime with optional timezone conversion."""
    if tz is not None:
        if isinstance(tz, str):
            tz = ZoneInfo(tz)
        dt = dt.astimezone(tz)
    return dt.strftime(fmt)


def parse_datetime(
    s: str,
    fmt: str = "%Y-%m-%dT%H:%M:%S",
    tz: str | ZoneInfo | None = None,
) -> datetime:
    """Parse datetime string with optional timezone."""
    dt = datetime.strptime(s, fmt)
    if tz is not None:
        if isinstance(tz, str):
            tz = ZoneInfo(tz)
        dt = dt.replace(tzinfo=tz)
    return dt


def is_dst(dt: datetime, tz: str | ZoneInfo) -> bool:
    """Check if datetime is in DST for the given timezone."""
    if isinstance(tz, str):
        tz = ZoneInfo(tz)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    else:
        dt = dt.astimezone(tz)
    dst = dt.dst()
    return dst is not None and dst.total_seconds() > 0


class TimezoneService:
    """Service for managing user timezones."""

    def __init__(self, default_tz: str = "UTC"):
        self._default_tz = ZoneInfo(default_tz)
        self._user_timezones: dict[str, ZoneInfo] = {}

    def set_user_timezone(self, user_id: str, tz: str) -> None:
        """Set timezone for a user."""
        self._user_timezones[user_id] = ZoneInfo(tz)

    def get_user_timezone(self, user_id: str) -> ZoneInfo:
        """Get timezone for a user."""
        return self._user_timezones.get(user_id, self._default_tz)

    def convert_for_user(self, dt: datetime, user_id: str) -> datetime:
        """Convert datetime to user's timezone."""
        user_tz = self.get_user_timezone(user_id)
        return from_utc(dt, user_tz)

    def convert_from_user(self, dt: datetime, user_id: str) -> datetime:
        """Convert datetime from user's timezone to UTC."""
        user_tz = self.get_user_timezone(user_id)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=user_tz)
        return to_utc(dt)

    def now_for_user(self, user_id: str) -> datetime:
        """Get current time in user's timezone."""
        user_tz = self.get_user_timezone(user_id)
        return now_in_timezone(user_tz)

    def list_common_timezones(self) -> list[dict[str, Any]]:
        """List common timezones with info."""
        return [get_timezone_info(tz.value).to_dict() for tz in CommonTimezone]
