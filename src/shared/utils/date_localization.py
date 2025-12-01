"""Date/Time localization with ISO 8601 standardization."""

from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from enum import Enum
from zoneinfo import ZoneInfo


class DateFormat(Enum):
    """Date format patterns."""
    ISO_8601 = "iso_8601"
    US = "us"
    EU = "eu"
    LONG = "long"
    SHORT = "short"


class TimeFormat(Enum):
    """Time format patterns."""
    H24 = "24h"
    H12 = "12h"
    ISO = "iso"


@dataclass
class DateTimeLocale:
    """Locale configuration for date/time."""
    date_format: DateFormat = DateFormat.ISO_8601
    time_format: TimeFormat = TimeFormat.H24
    first_day_of_week: int = 0  # 0=Monday, 6=Sunday
    month_names: list[str] | None = None
    day_names: list[str] | None = None
    am_pm: tuple[str, str] = ("AM", "PM")


# Predefined locales
LOCALES: dict[str, DateTimeLocale] = {
    "en_US": DateTimeLocale(
        date_format=DateFormat.US,
        time_format=TimeFormat.H12,
        first_day_of_week=6,
        month_names=["January", "February", "March", "April", "May", "June",
                     "July", "August", "September", "October", "November", "December"],
        day_names=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    ),
    "pt_BR": DateTimeLocale(
        date_format=DateFormat.EU,
        time_format=TimeFormat.H24,
        first_day_of_week=0,
        month_names=["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                     "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"],
        day_names=["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    ),
    "de_DE": DateTimeLocale(
        date_format=DateFormat.EU,
        time_format=TimeFormat.H24,
        first_day_of_week=0,
        month_names=["Januar", "Februar", "März", "April", "Mai", "Juni",
                     "Juli", "August", "September", "Oktober", "November", "Dezember"],
        day_names=["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    ),
}


class DateTimeFormatter:
    """Format dates and times for display."""

    def __init__(self, locale: str = "en_US") -> None:
        self._locale = LOCALES.get(locale, DateTimeLocale())

    def format_date(self, dt: datetime | date, format: DateFormat | None = None) -> str:
        """Format a date."""
        fmt = format or self._locale.date_format
        if isinstance(dt, datetime):
            d = dt.date()
        else:
            d = dt

        if fmt == DateFormat.ISO_8601:
            return d.isoformat()
        elif fmt == DateFormat.US:
            return f"{d.month:02d}/{d.day:02d}/{d.year}"
        elif fmt == DateFormat.EU:
            return f"{d.day:02d}/{d.month:02d}/{d.year}"
        elif fmt == DateFormat.LONG:
            month = self._locale.month_names[d.month - 1] if self._locale.month_names else str(d.month)
            return f"{month} {d.day}, {d.year}"
        elif fmt == DateFormat.SHORT:
            return f"{d.day}/{d.month}"
        return d.isoformat()

    def format_time(self, dt: datetime | time, format: TimeFormat | None = None) -> str:
        """Format a time."""
        fmt = format or self._locale.time_format
        if isinstance(dt, datetime):
            t = dt.time()
        else:
            t = dt

        if fmt == TimeFormat.ISO:
            return t.isoformat()
        elif fmt == TimeFormat.H24:
            return f"{t.hour:02d}:{t.minute:02d}:{t.second:02d}"
        elif fmt == TimeFormat.H12:
            hour = t.hour % 12 or 12
            period = self._locale.am_pm[0] if t.hour < 12 else self._locale.am_pm[1]
            return f"{hour}:{t.minute:02d} {period}"
        return t.isoformat()

    def format_datetime(
        self,
        dt: datetime,
        date_format: DateFormat | None = None,
        time_format: TimeFormat | None = None
    ) -> str:
        """Format a datetime."""
        date_str = self.format_date(dt, date_format)
        time_str = self.format_time(dt, time_format)
        return f"{date_str} {time_str}"

    def format_relative(self, dt: datetime, now: datetime | None = None) -> str:
        """Format as relative time (e.g., '2 hours ago')."""
        if now is None:
            now = datetime.now(timezone.utc)

        diff = now - dt
        seconds = diff.total_seconds()

        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
        else:
            return self.format_date(dt)


class ISO8601Parser:
    """Parse ISO 8601 date/time strings."""

    @staticmethod
    def parse_datetime(value: str) -> datetime:
        """Parse ISO 8601 datetime string."""
        value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)

    @staticmethod
    def parse_date(value: str) -> date:
        """Parse ISO 8601 date string."""
        return date.fromisoformat(value)

    @staticmethod
    def parse_time(value: str) -> time:
        """Parse ISO 8601 time string."""
        return time.fromisoformat(value)

    @staticmethod
    def parse_duration(value: str) -> timedelta:
        """Parse ISO 8601 duration string (e.g., PT1H30M)."""
        if not value.startswith("P"):
            raise ValueError("Duration must start with P")

        value = value[1:]
        days = hours = minutes = seconds = 0

        if "T" in value:
            date_part, time_part = value.split("T")
        else:
            date_part, time_part = value, ""

        # Parse date part
        if "D" in date_part:
            days_str, date_part = date_part.split("D")
            days = int(days_str)

        # Parse time part
        if "H" in time_part:
            hours_str, time_part = time_part.split("H")
            hours = int(hours_str)
        if "M" in time_part:
            minutes_str, time_part = time_part.split("M")
            minutes = int(minutes_str)
        if "S" in time_part:
            seconds_str, _ = time_part.split("S")
            seconds = int(float(seconds_str))

        return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


class DateTimeNormalizer:
    """Normalize dates to UTC and ISO 8601."""

    @staticmethod
    def to_utc(dt: datetime, source_tz: str | None = None) -> datetime:
        """Convert datetime to UTC."""
        if dt.tzinfo is None and source_tz:
            dt = dt.replace(tzinfo=ZoneInfo(source_tz))
        elif dt.tzinfo is None:
            return dt.replace(tzinfo=ZoneInfo("UTC"))

        return dt.astimezone(ZoneInfo("UTC"))

    @staticmethod
    def to_iso8601(dt: datetime) -> str:
        """Convert datetime to ISO 8601 string."""
        utc_dt = DateTimeNormalizer.to_utc(dt)
        return utc_dt.isoformat().replace("+00:00", "Z")

    @staticmethod
    def from_user_input(
        value: str,
        user_timezone: str = "UTC"
    ) -> datetime:
        """Parse user input and convert to UTC."""
        dt = ISO8601Parser.parse_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo(user_timezone))
        return DateTimeNormalizer.to_utc(dt)
