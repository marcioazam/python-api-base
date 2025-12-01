"""Outbox dispatcher for publishing events to message brokers.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 6.4**
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol

from my_app.infrastructure.outbox.models import (
    OutboxEntry,
    OutboxStatus,
    OutboxRepository,
    EventPublisher,
)

logger = logging.getLogger(__name__)


class OutboxDispatcher:
    """Dispatches pending outbox entries to message broker.
    
    Reads pending entries from the outbox table and publishes
    them to the configured message broker.
    """
    
    def __init__(
        self,
        repository: OutboxRepository,
        publisher: EventPublisher,
        batch_size: int = 100,
        retry_delay_seconds: float = 1.0,
    ) -> None:
        self._repository = repository
        self._publisher = publisher
        self._batch_size = batch_size
        self._retry_delay = retry_delay_seconds
        self._running = False
    
    async def dispatch_pending(self) -> tuple[int, int]:
        """Dispatch all pending outbox entries.
        
        Returns:
            Tuple of (success_count, failure_count).
        """
        entries = await self._repository.get_pending(self._batch_size)
        success_count = 0
        failure_count = 0
        
        for entry in entries:
            try:
                entry.mark_processing()
                await self._repository.update(entry)
                
                published = await self._publisher.publish(
                    entry.event_type,
                    entry.payload,
                )
                
                if published:
                    entry.mark_published()
                    success_count += 1
                    logger.debug(
                        f"Published event {entry.event_type}",
                        extra={
                            "entry_id": entry.id,
                            "aggregate_type": entry.aggregate_type,
                            "aggregate_id": entry.aggregate_id,
                        },
                    )
                else:
                    entry.mark_failed("Publisher returned False")
                    failure_count += 1
                    logger.warning(
                        f"Failed to publish event {entry.event_type}",
                        extra={"entry_id": entry.id},
                    )
                
            except Exception as e:
                entry.mark_failed(str(e))
                failure_count += 1
                logger.error(
                    f"Error publishing event: {e}",
                    extra={"entry_id": entry.id},
                    exc_info=True,
                )
            
            await self._repository.update(entry)
        
        return success_count, failure_count
    
    async def start_polling(
        self,
        interval_seconds: float = 5.0,
    ) -> None:
        """Start polling for pending entries.
        
        Args:
            interval_seconds: Time between polling cycles.
        """
        self._running = True
        logger.info(f"Starting outbox dispatcher with {interval_seconds}s interval")
        
        while self._running:
            try:
                success, failed = await self.dispatch_pending()
                if success > 0 or failed > 0:
                    logger.info(
                        f"Outbox dispatch cycle: {success} success, {failed} failed"
                    )
            except Exception as e:
                logger.error(f"Outbox dispatch error: {e}", exc_info=True)
            
            await asyncio.sleep(interval_seconds)
    
    def stop_polling(self) -> None:
        """Stop the polling loop."""
        self._running = False
        logger.info("Stopping outbox dispatcher")
    
    async def cleanup_old_entries(
        self,
        retention_days: int = 7,
    ) -> int:
        """Clean up old published entries.
        
        Args:
            retention_days: Number of days to retain published entries.
            
        Returns:
            Number of entries deleted.
        """
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        deleted = await self._repository.delete_published(cutoff)
        logger.info(f"Cleaned up {deleted} old outbox entries")
        return deleted


@dataclass
class DispatcherConfig:
    """Configuration for outbox dispatcher."""
    
    batch_size: int = 100
    poll_interval_seconds: float = 5.0
    retry_delay_seconds: float = 1.0
    cleanup_retention_days: int = 7
    cleanup_interval_hours: int = 24


class OutboxDispatcherService:
    """Service that manages outbox dispatcher lifecycle."""
    
    def __init__(
        self,
        dispatcher: OutboxDispatcher,
        config: DispatcherConfig | None = None,
    ) -> None:
        self._dispatcher = dispatcher
        self._config = config or DispatcherConfig()
        self._dispatch_task: asyncio.Task | None = None
        self._cleanup_task: asyncio.Task | None = None
    
    async def start(self) -> None:
        """Start the dispatcher service."""
        self._dispatch_task = asyncio.create_task(
            self._dispatcher.start_polling(self._config.poll_interval_seconds)
        )
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Outbox dispatcher service started")
    
    async def stop(self) -> None:
        """Stop the dispatcher service."""
        self._dispatcher.stop_polling()
        
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Outbox dispatcher service stopped")
    
    async def _cleanup_loop(self) -> None:
        """Periodic cleanup of old entries."""
        interval = self._config.cleanup_interval_hours * 3600
        
        while True:
            await asyncio.sleep(interval)
            try:
                await self._dispatcher.cleanup_old_entries(
                    self._config.cleanup_retention_days
                )
            except Exception as e:
                logger.error(f"Cleanup error: {e}", exc_info=True)
