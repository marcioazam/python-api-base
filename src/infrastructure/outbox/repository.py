"""SQLAlchemy implementation of Outbox repository.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 6.4**
"""

from datetime import datetime
from typing import Any

from sqlalchemy import select, delete, String, DateTime, Integer, Text, JSON, Enum as SQLEnum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from my_app.infrastructure.db.models.read_models import Base
from my_app.infrastructure.outbox.models import OutboxEntry, OutboxStatus, OutboxRepository


class OutboxModel(Base):
    """SQLAlchemy model for outbox entries."""
    
    __tablename__ = "outbox"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    aggregate_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    def to_entry(self) -> OutboxEntry:
        """Convert to OutboxEntry domain object."""
        return OutboxEntry(
            id=self.id,
            aggregate_type=self.aggregate_type,
            aggregate_id=self.aggregate_id,
            event_type=self.event_type,
            payload=self.payload,
            status=OutboxStatus(self.status),
            created_at=self.created_at,
            processed_at=self.processed_at,
            retry_count=self.retry_count,
            max_retries=self.max_retries,
            error_message=self.error_message,
        )
    
    @classmethod
    def from_entry(cls, entry: OutboxEntry) -> "OutboxModel":
        """Create from OutboxEntry domain object."""
        return cls(
            id=entry.id,
            aggregate_type=entry.aggregate_type,
            aggregate_id=entry.aggregate_id,
            event_type=entry.event_type,
            payload=entry.payload,
            status=entry.status.value,
            created_at=entry.created_at,
            processed_at=entry.processed_at,
            retry_count=entry.retry_count,
            max_retries=entry.max_retries,
            error_message=entry.error_message,
        )


class SQLAlchemyOutboxRepository:
    """SQLAlchemy implementation of OutboxRepository."""
    
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
    
    async def save(self, entry: OutboxEntry) -> None:
        """Save an outbox entry."""
        model = OutboxModel.from_entry(entry)
        self._session.add(model)
        await self._session.flush()
    
    async def get_pending(self, limit: int = 100) -> list[OutboxEntry]:
        """Get pending entries ordered by creation time."""
        stmt = (
            select(OutboxModel)
            .where(OutboxModel.status == OutboxStatus.PENDING.value)
            .order_by(OutboxModel.created_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [m.to_entry() for m in models]
    
    async def update(self, entry: OutboxEntry) -> None:
        """Update an outbox entry."""
        model = await self._session.get(OutboxModel, entry.id)
        if model:
            model.status = entry.status.value
            model.processed_at = entry.processed_at
            model.retry_count = entry.retry_count
            model.error_message = entry.error_message
            await self._session.flush()
    
    async def delete_published(self, older_than: datetime) -> int:
        """Delete published entries older than given date."""
        stmt = (
            delete(OutboxModel)
            .where(OutboxModel.status == OutboxStatus.PUBLISHED.value)
            .where(OutboxModel.processed_at < older_than)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount
    
    async def get_by_id(self, entry_id: str) -> OutboxEntry | None:
        """Get an outbox entry by ID."""
        model = await self._session.get(OutboxModel, entry_id)
        return model.to_entry() if model else None
    
    async def get_failed(self, limit: int = 100) -> list[OutboxEntry]:
        """Get failed entries for inspection."""
        stmt = (
            select(OutboxModel)
            .where(OutboxModel.status == OutboxStatus.FAILED.value)
            .order_by(OutboxModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [m.to_entry() for m in models]
