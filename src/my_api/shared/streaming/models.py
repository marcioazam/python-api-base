"""streaming models.

**Feature: shared-modules-code-review-fixes, Task 10.3**
**Validates: Requirements 3.4**
"""

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class SSEEvent:
    """Server-Sent Event.

    Attributes:
        data: Event data.
        event: Event type/name.
        id: Event ID for reconnection.
        retry: Reconnection time in milliseconds.
    """

    data: str | dict[str, Any]
    event: str | None = None
    id: str | None = None
    retry: int | None = None

    def to_string(self) -> str:
        """Convert to SSE format string.

        Returns:
            SSE formatted string.
        """
        lines = []

        if self.id is not None:
            lines.append(f"id: {self.id}")

        if self.event is not None:
            lines.append(f"event: {self.event}")

        if self.retry is not None:
            lines.append(f"retry: {self.retry}")

        # Handle data
        data_str = json.dumps(self.data) if isinstance(self.data, dict) else str(self.data)
        for line in data_str.split("\n"):
            lines.append(f"data: {line}")

        lines.append("")  # Empty line to end event
        return "\n".join(lines) + "\n"
