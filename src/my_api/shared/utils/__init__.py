"""Shared utilities - DateTime, IDs, password hashing, pagination, sanitization.

**Feature: shared-modules-code-review-fixes, Task 11.1**
**Validates: Requirements 8.1, 8.2**
"""

# DateTime utilities
from .datetime import (
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

# ID generators
from .ids import (
    compare_ulids,
    generate_ulid,
    generate_uuid7,
    is_valid_ulid,
    is_valid_uuid7,
    ulid_from_datetime,
    ulid_to_datetime,
    ULIDStr,
    UUID7Str,
)

# Pagination utilities
from .pagination import (
    CursorPaginationParams,
    CursorPaginationResult,
    decode_cursor,
    encode_cursor,
    OffsetPaginationParams,
    OffsetPaginationResult,
    paginate_list,
    paginate_offset,
)

# Password utilities
from .password import (
    hash_password,
    needs_rehash,
    verify_password,
)

# Sanitization utilities
from .sanitization import (
    get_sanitizer,
    InputSanitizer,
    sanitize_dict,
    sanitize_path,
    sanitize_sql_identifier,
    sanitize_string,
    SanitizationType,
    strip_dangerous_chars,
)

__all__ = [
    # DateTime
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
    # IDs
    "compare_ulids",
    "generate_ulid",
    "generate_uuid7",
    "is_valid_ulid",
    "is_valid_uuid7",
    "ulid_from_datetime",
    "ulid_to_datetime",
    "ULIDStr",
    "UUID7Str",
    # Pagination
    "CursorPaginationParams",
    "CursorPaginationResult",
    "decode_cursor",
    "encode_cursor",
    "OffsetPaginationParams",
    "OffsetPaginationResult",
    "paginate_list",
    "paginate_offset",
    # Password
    "hash_password",
    "needs_rehash",
    "verify_password",
    # Sanitization
    "get_sanitizer",
    "InputSanitizer",
    "sanitize_dict",
    "sanitize_path",
    "sanitize_sql_identifier",
    "sanitize_string",
    "SanitizationType",
    "strip_dangerous_chars",
]
