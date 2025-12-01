"""Property-based tests for timezone handling.

**Feature: api-architecture-analysis, Property 6: Timezone handling**
**Validates: Requirements 4.4**
"""

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from hypothesis import given, settings, strategies as st

from my_app.shared.timezone import (
    CommonTimezone,
    TimezoneInfo,
    TimezoneService,
    convert_timezone,
    format_datetime,
    from_utc,
    get_timezone_info,
    is_dst,
    now_in_timezone,
    parse_datetime,
    to_utc,
)


tz_strategy = st.sampled_from([tz.value for tz in CommonTimezone])
datetime_strategy = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 12, 31),
)


class TestTimezoneInfo:
    """Tests for TimezoneInfo."""

    def test_offset_hours_calculation(self):
        """offset_hours should calculate correctly."""
        info = TimezoneInfo(
            name="Test",
            offset=timedelta(hours=5, minutes=30),
            dst_offset=None,
            abbreviation="TST",
        )
        assert info.offset_hours == 5.5

    def test_to_dict_contains_fields(self):
        """to_dict should contain all fields."""
        info = TimezoneInfo(
            name="Test",
            offset=timedelta(hours=2),
            dst_offset=None,
            abbreviation="TST",
        )
        d = info.to_dict()
        assert d["name"] == "Test"
        assert d["abbreviation"] == "TST"
        assert "offset_hours" in d


class TestGetTimezoneInfo:
    """Tests for get_timezone_info."""

    @given(tz=tz_strategy)
    @settings(max_examples=20)
    def test_returns_valid_info(self, tz: str):
        """Should return valid timezone info."""
        info = get_timezone_info(tz)
        assert info.name == tz
        assert info.abbreviation is not None


class TestConvertTimezone:
    """Tests for convert_timezone."""

    @given(dt=datetime_strategy, from_tz=tz_strategy, to_tz=tz_strategy)
    @settings(max_examples=50)
    def test_round_trip_preserves_instant(
        self, dt: datetime, from_tz: str, to_tz: str
    ):
        """Converting back and forth should preserve the instant."""
        converted = convert_timezone(dt, from_tz, to_tz)
        back = convert_timezone(converted, to_tz, from_tz)
        assert abs((back - dt.replace(tzinfo=ZoneInfo(from_tz))).total_seconds()) < 1

    @given(dt=datetime_strategy, tz=tz_strategy)
    @settings(max_examples=50)
    def test_same_timezone_no_change(self, dt: datetime, tz: str):
        """Converting to same timezone should not change time."""
        result = convert_timezone(dt, tz, tz)
        original = dt.replace(tzinfo=ZoneInfo(tz))
        assert result == original


class TestToUtc:
    """Tests for to_utc."""

    @given(dt=datetime_strategy, tz=tz_strategy)
    @settings(max_examples=50)
    def test_result_is_utc(self, dt: datetime, tz: str):
        """Result should be in UTC."""
        result = to_utc(dt, tz)
        assert result.tzinfo == timezone.utc

    def test_naive_datetime_with_source_tz(self):
        """Should handle naive datetime with source timezone."""
        dt = datetime(2024, 1, 15, 12, 0, 0)
        result = to_utc(dt, "America/New_York")
        assert result.tzinfo == timezone.utc


class TestFromUtc:
    """Tests for from_utc."""

    @given(dt=datetime_strategy, tz=tz_strategy)
    @settings(max_examples=50)
    def test_result_has_target_timezone(self, dt: datetime, tz: str):
        """Result should have target timezone."""
        utc_dt = dt.replace(tzinfo=timezone.utc)
        result = from_utc(utc_dt, tz)
        assert result.tzinfo is not None


class TestNowInTimezone:
    """Tests for now_in_timezone."""

    @given(tz=tz_strategy)
    @settings(max_examples=20)
    def test_returns_aware_datetime(self, tz: str):
        """Should return timezone-aware datetime."""
        result = now_in_timezone(tz)
        assert result.tzinfo is not None


class TestFormatDatetime:
    """Tests for format_datetime."""

    def test_default_format(self):
        """Should format with default format."""
        dt = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        result = format_datetime(dt)
        assert "2024-01-15" in result
        assert "12:30:45" in result

    @given(dt=datetime_strategy, tz=tz_strategy)
    @settings(max_examples=50)
    def test_with_timezone_conversion(self, dt: datetime, tz: str):
        """Should convert to timezone before formatting."""
        utc_dt = dt.replace(tzinfo=timezone.utc)
        result = format_datetime(utc_dt, tz=tz)
        assert isinstance(result, str)


class TestParseDatetime:
    """Tests for parse_datetime."""

    def test_parse_iso_format(self):
        """Should parse ISO format."""
        result = parse_datetime("2024-01-15T12:30:45")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    @given(tz=tz_strategy)
    @settings(max_examples=20)
    def test_parse_with_timezone(self, tz: str):
        """Should attach timezone to parsed datetime."""
        result = parse_datetime("2024-01-15T12:30:45", tz=tz)
        assert result.tzinfo is not None


class TestIsDst:
    """Tests for is_dst."""

    def test_summer_in_new_york(self):
        """July should be DST in New York."""
        dt = datetime(2024, 7, 15, 12, 0, 0)
        result = is_dst(dt, "America/New_York")
        assert result is True

    def test_winter_in_new_york(self):
        """January should not be DST in New York."""
        dt = datetime(2024, 1, 15, 12, 0, 0)
        result = is_dst(dt, "America/New_York")
        assert result is False


class TestTimezoneService:
    """Tests for TimezoneService."""

    def test_set_and_get_user_timezone(self):
        """Should store and retrieve user timezone."""
        service = TimezoneService()
        service.set_user_timezone("user1", "America/New_York")
        tz = service.get_user_timezone("user1")
        assert str(tz) == "America/New_York"

    def test_default_timezone_for_unknown_user(self):
        """Should return default for unknown user."""
        service = TimezoneService(default_tz="Europe/London")
        tz = service.get_user_timezone("unknown")
        assert str(tz) == "Europe/London"

    def test_convert_for_user(self):
        """Should convert datetime to user's timezone."""
        service = TimezoneService()
        service.set_user_timezone("user1", "America/New_York")
        utc_dt = datetime(2024, 1, 15, 17, 0, 0, tzinfo=timezone.utc)
        result = service.convert_for_user(utc_dt, "user1")
        assert result.hour == 12  # EST is UTC-5

    def test_now_for_user(self):
        """Should return current time in user's timezone."""
        service = TimezoneService()
        service.set_user_timezone("user1", "Asia/Tokyo")
        result = service.now_for_user("user1")
        assert result.tzinfo is not None

    def test_list_common_timezones(self):
        """Should list common timezones."""
        service = TimezoneService()
        result = service.list_common_timezones()
        assert len(result) > 0
        assert all("name" in tz for tz in result)
