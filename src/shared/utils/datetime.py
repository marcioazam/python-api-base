"""DateTime utilities - re-exports from time module for backward compatibility.

This module provides timezone-aware datetime utilities with ISO 8601 formatting.
"""

from my_app.shared.utils.time import (
    add_duration,
    end_of_day,
    ensure_utc,
    format_datetime,
    from_iso8601,
    from_timestamp,
    now,
    start_of_day,
    to_iso8601,
    to_timestamp,
    utc_now,
)

__all__ = [
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
