"""Dead Letter Queue handler.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 6.6**
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class DLQEntry:
    """Dead letter queue entry."""
    id: str = field(default_factory=lambda: str(uuid4()))
    original_queue: str = ""
    message_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    retry_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "original_queue": self.original_queue,
            "message_id": self.message_id,
            "payload": self.payload,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat(),
        }


class DLQHandler:
    """Handler for dead letter queue operations."""
    
    def __init__(self) -> None:
        self._entries: dict[str, DLQEntry] = {}
    
    async def add(self, entry: DLQEntry) -> None:
        """Add entry to DLQ."""
        self._entries[entry.id] = entry
        logger.warning(f"Added to DLQ: {entry.id} from {entry.original_queue}")
    
    async def get_all(self, limit: int = 100) -> list[DLQEntry]:
        """Get all DLQ entries."""
        entries = list(self._entries.values())
        return sorted(entries, key=lambda e: e.created_at, reverse=True)[:limit]
    
    async def retry(self, entry_id: str) -> DLQEntry | None:
        """Get entry for retry and remove from DLQ."""
        entry = self._entries.pop(entry_id, None)
        if entry:
            logger.info(f"Retrying DLQ entry: {entry_id}")
        return entry
    
    async def delete(self, entry_id: str) -> bool:
        """Delete entry from DLQ."""
        if entry_id in self._entries:
            del self._entries[entry_id]
            logger.info(f"Deleted DLQ entry: {entry_id}")
            return True
        return False
    
    async def count(self) -> int:
        """Count entries in DLQ."""
        return len(self._entries)
