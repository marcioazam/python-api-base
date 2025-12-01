"""ID generators with ULID and UUID7 support for sortable IDs."""

from datetime import datetime
from typing import NewType

from ulid import ULID
from uuid6 import uuid7

# Type-safe ID wrappers
ULIDStr = NewType("ULIDStr", str)
UUID7Str = NewType("UUID7Str", str)


def generate_ulid() -> ULIDStr:
    """Generate a new ULID.

    ULIDs are:
    - 128-bit compatible with UUID
    - Lexicographically sortable
    - Monotonically increasing within millisecond
    - URL-safe (26 characters, Crockford Base32)

    Returns:
        ULIDStr: New ULID as string.
    """
    return ULIDStr(str(ULID()))


def generate_uuid7() -> UUID7Str:
    """Generate a new UUID v7.

    UUID v7 is:
    - Time-ordered (sortable by creation time)
    - Compatible with standard UUID format
    - 36 characters with hyphens

    Returns:
        UUID7Str: New UUID v7 as string.
    """
    return UUID7Str(str(uuid7()))


def ulid_from_datetime(dt: datetime) -> ULIDStr:
    """Generate ULID from specific datetime.

    Args:
        dt: Datetime to use for ULID timestamp.

    Returns:
        ULIDStr: ULID with specified timestamp.
    """
    return ULIDStr(str(ULID.from_datetime(dt)))


def ulid_to_datetime(ulid_str: str) -> datetime:
    """Extract datetime from ULID.

    Args:
        ulid_str: ULID string.

    Returns:
        datetime: Datetime encoded in ULID.
    """
    return ULID.from_str(ulid_str).datetime


def is_valid_ulid(value: str) -> bool:
    """Check if string is a valid ULID.

    Args:
        value: String to validate.

    Returns:
        bool: True if valid ULID.
    """
    if not value or len(value) != 26:
        return False
    try:
        ULID.from_str(value)
        return True
    except (ValueError, TypeError):
        return False


def is_valid_uuid7(value: str) -> bool:
    """Check if string is a valid UUID v7.

    Args:
        value: String to validate.

    Returns:
        bool: True if valid UUID v7.
    """
    if not value or len(value) != 36:
        return False
    try:
        from uuid import UUID

        parsed = UUID(value)
        # UUID v7 has version 7
        return parsed.version == 7
    except (ValueError, TypeError):
        return False


def compare_ulids(ulid1: str, ulid2: str) -> int:
    """Compare two ULIDs.

    Args:
        ulid1: First ULID.
        ulid2: Second ULID.

    Returns:
        int: -1 if ulid1 < ulid2, 0 if equal, 1 if ulid1 > ulid2.
    """
    if ulid1 < ulid2:
        return -1
    elif ulid1 > ulid2:
        return 1
    return 0
