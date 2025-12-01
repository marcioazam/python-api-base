"""Cursor-based pagination utilities.

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.

**Feature: python-api-base-2025-state-of-art**
**Validates: Requirements 1.1**
"""

import base64
import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CursorPage[T, CursorT]:
    """Result of cursor-based pagination.

    Type Parameters:
        T: Entity type.
        CursorT: Cursor type for pagination.

    **Feature: python-api-base-2025-state-of-art**
    **Validates: Requirements 1.1**
    """

    items: Sequence[T]
    next_cursor: CursorT | None
    prev_cursor: CursorT | None
    has_more: bool


class CursorPagination[T, CursorT]:
    """Cursor-based pagination helper with encode/decode.

    Provides opaque cursor encoding using base64-encoded JSON for secure
    and efficient pagination without exposing internal database details.

    Type Parameters:
        T: Entity type.
        CursorT: Cursor type (typically dict with field values).

    **Feature: python-api-base-2025-state-of-art**
    **Validates: Requirements 1.1**
    """

    def __init__(
        self,
        cursor_fields: list[str],
        default_limit: int = 20,
    ) -> None:
        """Initialize cursor pagination.

        Args:
            cursor_fields: Fields to use for cursor (e.g., ['created_at', 'id']).
            default_limit: Default page size.
        """
        self._cursor_fields = cursor_fields
        self._default_limit = default_limit

    def encode_cursor(self, entity: T) -> str:
        """Encode entity fields into opaque cursor string.

        Args:
            entity: Entity to create cursor from.

        Returns:
            Base64-encoded cursor string.
        """
        cursor_data = {}
        for field in self._cursor_fields:
            value = getattr(entity, field, None)
            if value is not None:
                cursor_data[field] = str(value)
        return base64.urlsafe_b64encode(json.dumps(cursor_data).encode()).decode()

    def decode_cursor(self, cursor: str) -> CursorT:
        """Decode cursor string back to field values.

        Args:
            cursor: Base64-encoded cursor string.

        Returns:
            Dictionary of cursor field values. Returns empty dict if invalid.
        """
        try:
            decoded_bytes = base64.urlsafe_b64decode(cursor.encode())
            data = json.loads(decoded_bytes)
            return data  # type: ignore
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(
                f"Invalid cursor decode: {e}",
                extra={
                    "operation": "CURSOR_DECODE",
                    "error_type": type(e).__name__,
                },
            )
            return {}  # type: ignore
        except Exception as e:
            logger.error(
                f"Unexpected error decoding cursor: {e}",
                exc_info=True,
                extra={"operation": "CURSOR_DECODE"},
            )
            return {}  # type: ignore
