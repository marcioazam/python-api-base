# Batch Transaction Consistency

**Feature:** application-layer-improvements-2025
**Status:** Documented
**Date:** 2025-01-02

## Overview

Comprehensive guide for maintaining transactional consistency in batch operations, ensuring atomicity, error handling, and performance optimization for bulk data processing.

## Problem Statement

Batch operations present unique challenges:
- **Atomicity** - All-or-nothing execution for related operations
- **Partial failures** - Some items succeed, others fail
- **Transaction size** - Large batches may exceed database limits
- **Performance** - Balancing throughput with resource usage
- **Error recovery** - Rollback strategies for failed batches
- **Observability** - Tracking progress and failures

Without proper consistency patterns:
- Data corruption from partial updates
- Difficult error recovery and debugging
- Poor performance from inefficient batching
- Lost or duplicated data

## Solution

Implement batch transaction patterns:
1. **Single transaction** - Atomic batch (small batches)
2. **Chunked transactions** - Split large batches
3. **Savepoint rollback** - Partial rollback within transaction
4. **Two-phase commit** - Distributed transactions
5. **Idempotent operations** - Safe retry of failed batches

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Batch Transaction Consistency Patterns                      │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Single Transaction (Small Batches < 1000 items)         │
│     └─> BEGIN TRANSACTION                                    │
│         ├─> Process item 1                                   │
│         ├─> Process item 2                                   │
│         ├─> ...                                               │
│         ├─> Process item N                                   │
│         └─> COMMIT (or ROLLBACK on error)                    │
│                                                               │
│  2. Chunked Transactions (Large Batches > 1000 items)       │
│     └─> Split batch into chunks                             │
│         ├─> Chunk 1: BEGIN → Process → COMMIT              │
│         ├─> Chunk 2: BEGIN → Process → COMMIT              │
│         └─> Chunk N: BEGIN → Process → COMMIT              │
│                                                               │
│  3. Savepoint Rollback (Partial Rollback)                   │
│     └─> BEGIN TRANSACTION                                    │
│         ├─> SAVEPOINT sp1                                    │
│         │   ├─> Process item 1 ✅                            │
│         │   └─> RELEASE SAVEPOINT sp1                        │
│         ├─> SAVEPOINT sp2                                    │
│         │   ├─> Process item 2 ❌ (error)                    │
│         │   └─> ROLLBACK TO SAVEPOINT sp2                   │
│         └─> COMMIT (partial success)                         │
│                                                               │
│  4. Idempotent with Retry (Eventual Consistency)            │
│     └─> Process batch (may fail partially)                  │
│         └─> Retry failed items (idempotent)                 │
│             └─> Eventually all succeed                       │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Batch Transaction Patterns

### 1. Single Transaction (All-or-Nothing)

**Use case:** Small batches (<1000 items), strong consistency required

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class BatchResult:
    """Result of batch processing."""
    total: int
    succeeded: int
    failed: int
    errors: list[tuple[int, Exception]] = field(default_factory=list)


class SingleTransactionBatchProcessor:
    """Process batch in single transaction (all-or-nothing)."""

    def __init__(self, repository: Any, uow: UnitOfWork):
        self._repository = repository
        self._uow = uow

    async def process_batch(self, items: list[Any]) -> BatchResult:
        """Process all items in single transaction.

        Args:
            items: Items to process.

        Returns:
            Batch result with success/failure counts.

        Raises:
            Exception: If any item fails (rolls back entire batch).
        """
        if len(items) > 1000:
            logger.warning(
                "large_batch_in_single_transaction",
                extra={"count": len(items), "recommended_max": 1000}
            )

        result = BatchResult(total=len(items), succeeded=0, failed=0)

        async with self._uow:
            try:
                for idx, item in enumerate(items):
                    try:
                        await self._process_item(item)
                        result.succeeded += 1

                    except Exception as e:
                        logger.error(
                            "batch_item_failed",
                            exc_info=True,
                            extra={"item_index": idx, "total": len(items)}
                        )
                        result.failed += 1
                        result.errors.append((idx, e))
                        raise  # Fail fast, rollback entire batch

                # All items succeeded, commit
                await self._uow.commit()

                logger.info(
                    "batch_committed",
                    extra={
                        "total": result.total,
                        "succeeded": result.succeeded,
                    }
                )

            except Exception as e:
                # Rollback entire batch
                logger.error(
                    "batch_rolled_back",
                    exc_info=True,
                    extra={
                        "total": result.total,
                        "succeeded_before_error": result.succeeded,
                    }
                )
                raise

        return result

    async def _process_item(self, item: Any) -> None:
        """Process single item."""
        await self._repository.save(item)
```

### 2. Chunked Transactions (Large Batches)

**Use case:** Large batches (>1000 items), acceptable partial consistency

```python
class ChunkedTransactionBatchProcessor:
    """Process batch in chunks with separate transactions."""

    def __init__(
        self,
        repository: Any,
        uow_factory: Callable[[], UnitOfWork],
        chunk_size: int = 500,
    ):
        self._repository = repository
        self._uow_factory = uow_factory
        self._chunk_size = chunk_size

    async def process_batch(
        self,
        items: list[Any],
        continue_on_error: bool = False,
    ) -> BatchResult:
        """Process batch in chunks.

        Args:
            items: Items to process.
            continue_on_error: If True, continue processing after chunk failure.

        Returns:
            Batch result with success/failure counts per chunk.
        """
        result = BatchResult(total=len(items), succeeded=0, failed=0)

        # Split into chunks
        chunks = self._split_into_chunks(items)

        logger.info(
            "batch_processing_started",
            extra={
                "total_items": len(items),
                "chunks": len(chunks),
                "chunk_size": self._chunk_size,
            }
        )

        for chunk_idx, chunk in enumerate(chunks):
            chunk_result = await self._process_chunk(chunk_idx, chunk)

            result.succeeded += chunk_result.succeeded
            result.failed += chunk_result.failed
            result.errors.extend(chunk_result.errors)

            # Stop on first chunk failure if continue_on_error=False
            if chunk_result.failed > 0 and not continue_on_error:
                logger.error(
                    "batch_stopped_on_chunk_failure",
                    extra={
                        "chunk": chunk_idx + 1,
                        "total_chunks": len(chunks),
                        "succeeded_items": result.succeeded,
                        "failed_items": result.failed,
                    }
                )
                break

        logger.info(
            "batch_processing_completed",
            extra={
                "total": result.total,
                "succeeded": result.succeeded,
                "failed": result.failed,
            }
        )

        return result

    async def _process_chunk(
        self,
        chunk_idx: int,
        chunk: list[Any],
    ) -> BatchResult:
        """Process single chunk in transaction."""
        chunk_result = BatchResult(total=len(chunk), succeeded=0, failed=0)

        uow = self._uow_factory()

        try:
            async with uow:
                for item in chunk:
                    await self._repository.save(item)
                    chunk_result.succeeded += 1

                await uow.commit()

                logger.debug(
                    "chunk_committed",
                    extra={
                        "chunk": chunk_idx + 1,
                        "items": len(chunk),
                    }
                )

        except Exception as e:
            chunk_result.failed = len(chunk)
            chunk_result.errors.append((chunk_idx, e))

            logger.error(
                "chunk_failed",
                exc_info=True,
                extra={
                    "chunk": chunk_idx + 1,
                    "items": len(chunk),
                }
            )

        return chunk_result

    def _split_into_chunks(self, items: list[Any]) -> list[list[Any]]:
        """Split items into chunks."""
        return [
            items[i:i + self._chunk_size]
            for i in range(0, len(items), self._chunk_size)
        ]
```

### 3. Savepoint Rollback (Partial Rollback)

**Use case:** Continue processing after individual failures, PostgreSQL/Oracle

```python
class SavepointBatchProcessor:
    """Process batch with per-item savepoints (PostgreSQL/Oracle)."""

    def __init__(self, repository: Any, uow: UnitOfWork):
        self._repository = repository
        self._uow = uow

    async def process_batch(
        self,
        items: list[Any],
        skip_failures: bool = True,
    ) -> BatchResult:
        """Process batch with savepoint per item.

        Args:
            items: Items to process.
            skip_failures: If True, skip failed items and continue.

        Returns:
            Batch result with partial success.
        """
        result = BatchResult(total=len(items), succeeded=0, failed=0)

        async with self._uow:
            for idx, item in enumerate(items):
                savepoint_name = f"sp_{idx}"

                try:
                    # Create savepoint
                    await self._uow.savepoint(savepoint_name)

                    # Process item
                    await self._process_item(item)
                    result.succeeded += 1

                    # Release savepoint (optional optimization)
                    await self._uow.release_savepoint(savepoint_name)

                    logger.debug(
                        "item_processed",
                        extra={"item_index": idx, "total": len(items)}
                    )

                except Exception as e:
                    result.failed += 1
                    result.errors.append((idx, e))

                    # Rollback to savepoint (undo this item only)
                    await self._uow.rollback_to_savepoint(savepoint_name)

                    logger.warning(
                        "item_failed_rolled_back_to_savepoint",
                        extra={
                            "item_index": idx,
                            "error": str(e),
                            "skip_failures": skip_failures,
                        }
                    )

                    if not skip_failures:
                        raise  # Stop processing

            # Commit transaction with partial success
            await self._uow.commit()

            logger.info(
                "batch_partially_committed",
                extra={
                    "total": result.total,
                    "succeeded": result.succeeded,
                    "failed": result.failed,
                }
            )

        return result

    async def _process_item(self, item: Any) -> None:
        """Process single item."""
        await self._repository.save(item)
```

### 4. Idempotent Retry Pattern

**Use case:** Eventually consistent, retry-safe operations

```python
from dataclasses import dataclass, field

@dataclass
class BatchItem:
    """Item in batch with tracking."""
    id: str
    data: Any
    attempts: int = 0
    last_error: str | None = None
    succeeded: bool = False


class IdempotentBatchProcessor:
    """Process batch with idempotent retry."""

    def __init__(
        self,
        repository: Any,
        uow_factory: Callable[[], UnitOfWork],
        max_attempts: int = 3,
    ):
        self._repository = repository
        self._uow_factory = uow_factory
        self._max_attempts = max_attempts

    async def process_batch(
        self,
        items: list[Any],
    ) -> BatchResult:
        """Process batch with idempotent retry.

        Args:
            items: Items to process (must be idempotent).

        Returns:
            Batch result after all retries.
        """
        # Wrap items for tracking
        batch_items = [
            BatchItem(id=self._get_item_id(item), data=item)
            for item in items
        ]

        result = BatchResult(total=len(items), succeeded=0, failed=0)

        # Process until all succeed or max attempts reached
        attempt = 1
        while attempt <= self._max_attempts:
            pending = [item for item in batch_items if not item.succeeded]

            if not pending:
                break  # All succeeded

            logger.info(
                "batch_attempt",
                extra={
                    "attempt": attempt,
                    "max_attempts": self._max_attempts,
                    "pending_items": len(pending),
                }
            )

            await self._process_items(pending)

            attempt += 1

        # Calculate final results
        for item in batch_items:
            if item.succeeded:
                result.succeeded += 1
            else:
                result.failed += 1
                result.errors.append((item.id, Exception(item.last_error)))

        logger.info(
            "batch_completed",
            extra={
                "total": result.total,
                "succeeded": result.succeeded,
                "failed": result.failed,
                "attempts": attempt - 1,
            }
        )

        return result

    async def _process_items(self, items: list[BatchItem]) -> None:
        """Process batch items (single transaction)."""
        uow = self._uow_factory()

        async with uow:
            for item in items:
                try:
                    await self._process_item_idempotent(item.data)
                    item.succeeded = True
                    item.last_error = None

                except Exception as e:
                    item.attempts += 1
                    item.last_error = str(e)

                    logger.warning(
                        "item_failed_will_retry",
                        extra={
                            "item_id": item.id,
                            "attempt": item.attempts,
                            "error": str(e),
                        }
                    )

            # Commit partial success
            await uow.commit()

    async def _process_item_idempotent(self, item: Any) -> None:
        """Process item idempotently (safe to retry)."""
        # Check if already processed
        existing = await self._repository.get_by_id(self._get_item_id(item))
        if existing:
            return  # Already processed, skip

        await self._repository.save(item)

    def _get_item_id(self, item: Any) -> str:
        """Extract item ID for idempotency."""
        if hasattr(item, "id"):
            return item.id
        return str(hash(str(item)))
```

---

## Batch Operation Use Cases

### Use Case 1: Bulk User Import

```python
@dataclass
class ImportUsersCommand(BaseCommand):
    """Import multiple users from CSV."""
    users: list[dict[str, Any]]

    @property
    def transaction_config(self) -> TransactionConfig:
        """Long timeout for large import."""
        return TransactionConfig(
            enabled=True,
            timeout_seconds=600,  # 10 minutes
        )


class ImportUsersHandler:
    """Handler for bulk user import."""

    def __init__(
        self,
        user_repository: IUserRepository,
        uow_factory: Callable[[], UnitOfWork],
    ):
        self._repository = user_repository
        self._processor = ChunkedTransactionBatchProcessor(
            repository=user_repository,
            uow_factory=uow_factory,
            chunk_size=100,  # 100 users per transaction
        )

    async def handle(self, command: ImportUsersCommand) -> BatchResult:
        """Import users in chunks."""
        logger.info(
            "import_users_started",
            extra={"total_users": len(command.users)}
        )

        # Convert to domain entities
        users = [
            UserAggregate.create(**user_data)
            for user_data in command.users
        ]

        # Process in chunks
        result = await self._processor.process_batch(
            items=users,
            continue_on_error=True,  # Continue on chunk failure
        )

        logger.info(
            "import_users_completed",
            extra={
                "total": result.total,
                "succeeded": result.succeeded,
                "failed": result.failed,
            }
        )

        return result
```

### Use Case 2: Batch Email Sending

```python
@dataclass
class SendBulkEmailsCommand(BaseCommand):
    """Send emails to multiple users."""
    user_ids: list[str]
    subject: str
    body: str


class SendBulkEmailsHandler:
    """Handler for bulk email sending."""

    def __init__(
        self,
        email_service: EmailService,
        user_repository: IUserRepository,
    ):
        self._email_service = email_service
        self._user_repository = user_repository

    async def handle(self, command: SendBulkEmailsCommand) -> BatchResult:
        """Send emails in batches (no transaction needed)."""
        result = BatchResult(
            total=len(command.user_ids),
            succeeded=0,
            failed=0
        )

        # Fetch users
        users = await self._user_repository.find_by_ids(command.user_ids)

        # Send emails (idempotent, no transaction)
        for user in users:
            try:
                await self._email_service.send(
                    to=user.email,
                    subject=command.subject,
                    body=command.body,
                    idempotency_key=f"bulk_email:{command.subject}:{user.id}"
                )
                result.succeeded += 1

            except Exception as e:
                result.failed += 1
                result.errors.append((user.id, e))

                logger.warning(
                    "email_send_failed",
                    extra={"user_id": user.id, "error": str(e)}
                )

        return result
```

### Use Case 3: Batch Data Update with Validation

```python
class UpdateMultipleUsersHandler:
    """Update multiple users with validation."""

    def __init__(
        self,
        user_repository: IUserRepository,
        user_service: UserDomainService,
        uow: UnitOfWork,
    ):
        self._repository = user_repository
        self._service = user_service
        self._processor = SavepointBatchProcessor(
            repository=user_repository,
            uow=uow
        )

    async def handle(self, updates: list[dict]) -> BatchResult:
        """Update users with savepoint rollback per user."""

        # Validate all first
        validated_updates = []
        for update in updates:
            if self._service.validate_update(update):
                validated_updates.append(update)

        # Process with savepoints
        result = await self._processor.process_batch(
            items=validated_updates,
            skip_failures=True,  # Continue even if some fail
        )

        return result
```

---

## Best Practices

### 1. Choosing the Right Pattern

| Pattern | Batch Size | Consistency | Performance | Use Case |
|---------|-----------|-------------|-------------|----------|
| Single Transaction | < 1000 | Strong | Medium | Financial, critical |
| Chunked | > 1000 | Eventual | High | Bulk imports |
| Savepoint | < 5000 | Partial | Low | Mixed success/failure |
| Idempotent Retry | Any | Eventual | High | External APIs |

### 2. Transaction Size Guidelines

```python
BATCH_SIZE_LIMITS = {
    "postgresql": {
        "small": 500,      # Safe for single transaction
        "medium": 5000,    # Use chunked or savepoints
        "large": 50000,    # Must use chunked
    },
    "mysql": {
        "small": 1000,
        "medium": 10000,
        "large": 100000,
    },
    "sqlite": {
        "small": 100,      # Limited concurrency
        "medium": 500,
        "large": 5000,
    }
}
```

### 3. Error Handling

✅ **DO:**
- Log batch progress (succeeded/failed counts)
- Store failed items for retry
- Provide detailed error messages per item
- Monitor batch completion rates
- Set appropriate timeouts

❌ **DON'T:**
- Use single transaction for huge batches
- Silently skip failures
- Mix idempotent and non-idempotent operations
- Process unvalidated data
- Ignore partial failures

### 4. Performance Optimization

```python
# Batch insert optimization
async def bulk_insert_optimized(items: list[Any]) -> None:
    """Optimized bulk insert."""

    # Use database-specific bulk operations
    if isinstance(session, AsyncSession):  # SQLAlchemy
        session.add_all(items)
        await session.flush()

    # Or raw SQL for maximum performance
    values = [(item.field1, item.field2) for item in items]
    await session.execute(
        "INSERT INTO table (field1, field2) VALUES (:field1, :field2)",
        values
    )
```

---

## Monitoring & Observability

### 1. Batch Metrics

```python
batch_metrics = {
    "batch_total": Counter("batch_operations_total", ["operation", "pattern"]),
    "batch_items": Histogram("batch_items_count", ["operation"]),
    "batch_duration": Histogram("batch_duration_seconds", ["operation", "pattern"]),
    "batch_items_succeeded": Counter("batch_items_succeeded", ["operation"]),
    "batch_items_failed": Counter("batch_items_failed", ["operation", "error_type"]),
    "batch_chunk_count": Histogram("batch_chunk_count", ["operation"]),
}
```

### 2. Structured Logging

```json
{
  "event": "batch_processing_started",
  "operation": "import_users",
  "total_items": 5000,
  "chunks": 50,
  "chunk_size": 100,
  "pattern": "chunked_transaction"
}

{
  "event": "batch_processing_completed",
  "operation": "import_users",
  "total": 5000,
  "succeeded": 4850,
  "failed": 150,
  "duration_seconds": 45.2,
  "pattern": "chunked_transaction"
}
```

---

## Testing

### 1. Testing Batch Consistency

```python
@pytest.mark.asyncio
async def test_batch_rollback_on_error():
    """Test batch rolls back entire transaction on error."""
    repository = Mock()
    repository.save = AsyncMock(side_effect=[None, None, Exception("Error")])

    processor = SingleTransactionBatchProcessor(repository, mock_uow)

    items = [{"id": 1}, {"id": 2}, {"id": 3}]

    with pytest.raises(Exception):
        await processor.process_batch(items)

    # Verify transaction was rolled back (all items undone)
    mock_uow.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_chunked_batch_partial_success():
    """Test chunked batch continues after chunk failure."""
    processor = ChunkedTransactionBatchProcessor(
        repository=mock_repository,
        uow_factory=lambda: mock_uow,
        chunk_size=2
    )

    # 5 items = 3 chunks (2, 2, 1)
    items = list(range(5))

    result = await processor.process_batch(items, continue_on_error=True)

    # Should process all chunks even if one fails
    assert result.total == 5
```

---

## References

- `src/application/common/middleware/transaction.py` - Transaction middleware
- `docs/architecture/transaction-configuration.md` - Transaction config
- PostgreSQL Savepoints: https://www.postgresql.org/docs/current/sql-savepoint.html
- Two-Phase Commit: https://en.wikipedia.org/wiki/Two-phase_commit_protocol

---

**Status:** ✅ Documented
**Version:** 1.0
**Last Updated:** 2025-01-02
