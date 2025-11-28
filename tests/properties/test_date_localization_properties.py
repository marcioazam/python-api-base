"""Property-based tests for Date/Time Localization.

**Feature: api-architecture-analysis, Property: Date localization operations**
**Validates: Requirements 20.4**
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo

from my_api.shared.date_localization import (
    DateTimeFormatter,
    DateFormat,
    TimeFormat,
    ISO8601Parser,
    DateTimeNormalizer,
)


class TestDateTimeFormatterProperties:
    """Property tests for date/time formatter."""

    @given(st.datetimes(min_value=datetime(1970, 1, 1), max_value=datetime(2100, 12, 31)))
    @settings(max_examples=100)
    def test_iso_format_parseable(self, dt: datetime) -> None:
        """ISO format output is parseable."""
        formatter = DateTimeFormatter()
        formatted = formatter.format_date(dt, DateFormat.ISO_8601)

        # Should be parseable
        parsed = date.fromisoformat(formatted)
        assert parsed == dt.date()

    @given(st.datetimes(min_value=datetime(1970, 1, 1), max_value=datetime(2100, 12, 31)))
    @settings(max_examples=100)
    def test_us_format_contains_components(self, dt: datetime) -> None:
        """US format contains all date components."""
        formatter = DateTimeFormatter("en_US")
        formatted = formatter.format_date(dt, DateFormat.US)

        # Should contain month, day, year
        assert str(dt.month).zfill(2) in formatted
        assert str(dt.day).zfill(2) in formatted
        assert str(dt.year) in formatted

    @given(st.datetimes(min_value=datetime(1970, 1, 1), max_value=datetime(2100, 12, 31)))
    @settings(max_examples=100)
    def test_time_format_24h(self, dt: datetime) -> None:
        """24h time format is correct."""
        formatter = DateTimeFormatter()
        formatted = formatter.format_time(dt, TimeFormat.H24)

        # Should contain hour, minute, second
        assert str(dt.hour).zfill(2) in formatted
        assert str(dt.minute).zfill(2) in formatted


class TestISO8601ParserProperties:
    """Property tests for ISO 8601 parser."""

    @given(st.datetimes(min_value=datetime(1970, 1, 1), max_value=datetime(2100, 12, 31)))
    @settings(max_examples=100)
    def test_datetime_round_trip(self, dt: datetime) -> None:
        """Datetime round trip through ISO 8601."""
        iso_str = dt.isoformat()
        parsed = ISO8601Parser.parse_datetime(iso_str)

        assert parsed.year == dt.year
        assert parsed.month == dt.month
        assert parsed.day == dt.day
        assert parsed.hour == dt.hour
        assert parsed.minute == dt.minute
        assert parsed.second == dt.second

    @given(st.dates(min_value=date(1970, 1, 1), max_value=date(2100, 12, 31)))
    @settings(max_examples=100)
    def test_date_round_trip(self, d: date) -> None:
        """Date round trip through ISO 8601."""
        iso_str = d.isoformat()
        parsed = ISO8601Parser.parse_date(iso_str)

        assert parsed == d

    @given(
        st.integers(min_value=0, max_value=30),
        st.integers(min_value=0, max_value=23),
        st.integers(min_value=0, max_value=59),
        st.integers(min_value=0, max_value=59)
    )
    @settings(max_examples=100)
    def test_duration_parsing(
        self,
        days: int,
        hours: int,
        minutes: int,
        seconds: int
    ) -> None:
        """Duration parsing is correct."""
        duration_str = f"P{days}DT{hours}H{minutes}M{seconds}S"
        parsed = ISO8601Parser.parse_duration(duration_str)

        expected = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
        assert parsed == expected


class TestDateTimeNormalizerProperties:
    """Property tests for datetime normalizer."""

    @given(st.datetimes(min_value=datetime(1970, 1, 1), max_value=datetime(2100, 12, 31)))
    @settings(max_examples=100)
    def test_to_utc_idempotent(self, dt: datetime) -> None:
        """Converting to UTC twice is same as once."""
        utc1 = DateTimeNormalizer.to_utc(dt)
        utc2 = DateTimeNormalizer.to_utc(utc1)

        assert utc1 == utc2

    @given(st.datetimes(min_value=datetime(1970, 1, 1), max_value=datetime(2100, 12, 31)))
    @settings(max_examples=100)
    def test_to_iso8601_ends_with_z(self, dt: datetime) -> None:
        """ISO 8601 UTC format ends with Z."""
        iso_str = DateTimeNormalizer.to_iso8601(dt)
        assert iso_str.endswith("Z")

    @given(st.datetimes(min_value=datetime(1970, 1, 1), max_value=datetime(2100, 12, 31)))
    @settings(max_examples=100)
    def test_to_iso8601_parseable(self, dt: datetime) -> None:
        """ISO 8601 output is parseable."""
        iso_str = DateTimeNormalizer.to_iso8601(dt)
        parsed = ISO8601Parser.parse_datetime(iso_str)

        # Should be in UTC
        assert parsed.tzinfo is not None


class TestRelativeTimeProperties:
    """Property tests for relative time formatting."""

    @given(st.integers(min_value=0, max_value=59))
    @settings(max_examples=50)
    def test_recent_shows_just_now_or_minutes(self, seconds: int) -> None:
        """Recent times show 'just now' or minutes."""
        formatter = DateTimeFormatter()
        now = datetime.utcnow()
        dt = now - timedelta(seconds=seconds)

        formatted = formatter.format_relative(dt, now)

        assert "just now" in formatted or "minute" in formatted

    @given(st.integers(min_value=1, max_value=23))
    @settings(max_examples=50)
    def test_hours_ago_shows_hours(self, hours: int) -> None:
        """Hours ago shows hours."""
        formatter = DateTimeFormatter()
        now = datetime.utcnow()
        dt = now - timedelta(hours=hours)

        formatted = formatter.format_relative(dt, now)

        assert "hour" in formatted

    @given(st.integers(min_value=1, max_value=6))
    @settings(max_examples=50)
    def test_days_ago_shows_days(self, days: int) -> None:
        """Days ago shows days."""
        formatter = DateTimeFormatter()
        now = datetime.utcnow()
        dt = now - timedelta(days=days)

        formatted = formatter.format_relative(dt, now)

        assert "day" in formatted
