# Event Handler Failure Strategies

**Feature:** application-layer-improvements-2025
**Status:** Documented
**Date:** 2025-01-02

## Overview

Comprehensive guide for handling failures in domain event handlers, covering retry strategies, error recovery, compensation logic, and resilience patterns.

## Problem Statement

Event handlers can fail for various reasons:
- **Transient failures** - Network timeouts, database locks, rate limits
- **Infrastructure failures** - Service unavailable, connection errors
- **Business logic errors** - Invalid data, constraint violations
- **External dependencies** - Third-party API failures

Without proper failure strategies:
- Events may be lost or processed inconsistently
- System state can become corrupted
- Recovery becomes manual and error-prone
- User experience degrades

## Solution

Implement comprehensive failure strategies:
1. **Retry patterns** - Automatic retry with exponential backoff
2. **Dead letter queue (DLQ)** - Capture unprocessable events
3. **Compensation logic** - Rollback on failure
4. **Circuit breakers** - Prevent cascade failures
5. **Idempotency** - Safe retry without side effects

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Event Handler Failure Flow                                  │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Event Published                                          │
│     └─> EventBus.publish(event)                              │
│                                                               │
│  2. Handler Execution                                         │
│     └─> try:                                                  │
│         ├─> await handler.handle(event)                      │
│         └─> ✅ Success                                        │
│                                                               │
│  3. Handler Failure                                           │
│     └─> except Exception as e:                               │
│         ├─> Is Transient Error?                              │
│         │   ├─> YES: Retry with backoff                      │
│         │   │   ├─> Max retries reached?                     │
│         │   │   │   ├─> YES: Send to DLQ                     │
│         │   │   │   └─> NO: Retry                            │
│         │   │                                                 │
│         │   └─> NO: Is Business Error?                       │
│         │       ├─> YES: Log & Skip                          │
│         │       └─> NO: Send to DLQ                          │
│         │                                                     │
│  4. Dead Letter Queue (DLQ)                                  │
│     └─> Store failed event + error + context                │
│         └─> Alert/Monitor                                    │
│                                                               │
│  5. Compensation (Optional)                                  │
│     └─> Execute compensation logic                           │
│         └─> Rollback changes                                 │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Failure Categories

### 1. Transient Failures (Retry)

Temporary errors that may succeed on retry:

- **Network timeouts** - HTTP 408, 504, connection timeout
- **Database locks** - Deadlock, lock timeout
- **Rate limiting** - HTTP 429 Too Many Requests
- **Service unavailable** - HTTP 503
- **Resource contention** - Concurrent modification

**Strategy:** Retry with exponential backoff

```python
TRANSIENT_ERRORS = [
    # HTTP errors
    408,  # Request Timeout
    429,  # Too Many Requests
    503,  # Service Unavailable
    504,  # Gateway Timeout
    # Database errors
    "Deadlock",
    "Lock wait timeout",
    # Network errors
    "Connection timeout",
    "Connection reset",
]
```

### 2. Permanent Failures (Skip/Log)

Errors that won't succeed on retry:

- **Validation errors** - Invalid data format
- **Business rule violations** - Constraint violations
- **Not found** - HTTP 404, entity doesn't exist
- **Unauthorized** - HTTP 401, 403
- **Bad request** - HTTP 400

**Strategy:** Log error and skip (don't retry)

```python
PERMANENT_ERRORS = [
    # HTTP errors
    400,  # Bad Request
    401,  # Unauthorized
    403,  # Forbidden
    404,  # Not Found
    422,  # Unprocessable Entity
    # Business errors
    ValidationError,
    ConstraintViolationError,
]
```

### 3. Unknown Failures (DLQ)

Unexpected errors that need investigation:

- **Unexpected exceptions**
- **Infrastructure failures**
- **Data corruption**
- **External service failures after max retries**

**Strategy:** Send to Dead Letter Queue for manual review

---

## Retry Patterns

### 1. Exponential Backoff with Jitter

```python
import random
from dataclasses import dataclass

@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_attempts: int = 3
    initial_delay_ms: int = 100
    max_delay_ms: int = 10000
    exponential_base: float = 2.0
    jitter: bool = True


async def retry_with_backoff(
    func: Callable,
    *args,
    config: RetryConfig = RetryConfig(),
    **kwargs,
) -> Any:
    """Retry function with exponential backoff.

    Args:
        func: Async function to retry.
        config: Retry configuration.

    Returns:
        Result from function.

    Raises:
        Exception: Last exception after all retries exhausted.
    """
    last_exception = None

    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)

        except Exception as e:
            last_exception = e

            # Don't retry permanent errors
            if not is_transient_error(e):
                raise

            # Last attempt, don't wait
            if attempt == config.max_attempts - 1:
                break

            # Calculate delay with exponential backoff
            delay_ms = min(
                config.initial_delay_ms * (config.exponential_base ** attempt),
                config.max_delay_ms
            )

            # Add jitter to prevent thundering herd
            if config.jitter:
                delay_ms = delay_ms * (0.5 + random.random() * 0.5)

            logger.info(
                "retrying_after_failure",
                extra={
                    "attempt": attempt + 1,
                    "max_attempts": config.max_attempts,
                    "delay_ms": delay_ms,
                    "error": str(e),
                }
            )

            await asyncio.sleep(delay_ms / 1000)

    # All retries exhausted
    raise last_exception


def is_transient_error(error: Exception) -> bool:
    """Check if error is transient (should retry)."""
    error_str = str(error)

    # HTTP transient errors
    if hasattr(error, "status_code"):
        return error.status_code in [408, 429, 503, 504]

    # Database transient errors
    if "deadlock" in error_str.lower():
        return True
    if "lock" in error_str.lower():
        return True

    # Network transient errors
    if "timeout" in error_str.lower():
        return True
    if "connection" in error_str.lower():
        return True

    return False
```

### 2. Event Handler with Retry

```python
from application.common.cqrs.event_bus import EventHandler
from domain.users.events import UserRegisteredEvent

class SendWelcomeEmailHandler(EventHandler[UserRegisteredEvent]):
    """Handler that sends welcome email with retry logic."""

    def __init__(self, email_service: EmailService):
        self._email_service = email_service

    async def handle(self, event: UserRegisteredEvent) -> None:
        """Handle event with automatic retry."""
        await retry_with_backoff(
            self._send_email,
            event.email,
            config=RetryConfig(
                max_attempts=3,
                initial_delay_ms=500,
                max_delay_ms=5000,
            )
        )

    async def _send_email(self, email: str) -> None:
        """Send email (may fail transiently)."""
        await self._email_service.send_welcome_email(email)
```

---

## Dead Letter Queue (DLQ)

### 1. DLQ Implementation

```python
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any

@dataclass
class DeadLetterEvent:
    """Event that failed processing."""

    event_type: str
    event_data: dict[str, Any]
    handler_name: str
    error_type: str
    error_message: str
    error_traceback: str
    attempt_count: int
    failed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    context: dict[str, Any] = field(default_factory=dict)


class DeadLetterQueue:
    """Repository for failed events."""

    async def add(self, dead_letter: DeadLetterEvent) -> None:
        """Store failed event for manual review."""
        # Store in database for persistence
        await self._repository.save(dead_letter)

        # Log for observability
        logger.error(
            "event_sent_to_dlq",
            extra={
                "event_type": dead_letter.event_type,
                "handler_name": dead_letter.handler_name,
                "error_type": dead_letter.error_type,
                "attempt_count": dead_letter.attempt_count,
                "operation": "DLQ_ADD",
            }
        )

        # Alert if critical
        if dead_letter.attempt_count > 3:
            await self._alert_service.send_alert(
                f"Event processing failed after {dead_letter.attempt_count} attempts"
            )

    async def retry(self, dead_letter_id: str) -> None:
        """Manually retry failed event."""
        dead_letter = await self._repository.get(dead_letter_id)

        # Reconstruct event
        event = reconstruct_event(dead_letter.event_type, dead_letter.event_data)

        # Republish
        await self._event_bus.publish(event, raise_on_error=False)

    async def list_failed(
        self,
        since: datetime | None = None,
        event_type: str | None = None,
    ) -> list[DeadLetterEvent]:
        """List failed events for investigation."""
        return await self._repository.find(
            since=since,
            event_type=event_type,
        )
```

### 2. Resilient Event Handler with DLQ

```python
class ResilientEventHandler[T](EventHandler[T]):
    """Base handler with retry and DLQ support."""

    def __init__(
        self,
        dlq: DeadLetterQueue,
        retry_config: RetryConfig | None = None,
    ):
        self._dlq = dlq
        self._retry_config = retry_config or RetryConfig()

    async def handle(self, event: T) -> None:
        """Handle event with retry and DLQ."""
        attempt = 0

        while attempt < self._retry_config.max_attempts:
            try:
                await self.process(event)
                return  # Success

            except Exception as e:
                attempt += 1

                # Permanent error - don't retry
                if not is_transient_error(e):
                    logger.warning(
                        "permanent_error_skipping",
                        extra={
                            "event_type": type(event).__name__,
                            "handler": type(self).__name__,
                            "error": str(e),
                        }
                    )
                    return

                # Max retries reached - send to DLQ
                if attempt >= self._retry_config.max_attempts:
                    await self._send_to_dlq(event, e, attempt)
                    return

                # Transient error - retry
                delay = self._calculate_delay(attempt)
                logger.info(
                    "transient_error_retrying",
                    extra={
                        "attempt": attempt,
                        "max_attempts": self._retry_config.max_attempts,
                        "delay_ms": delay,
                    }
                )
                await asyncio.sleep(delay / 1000)

    @abstractmethod
    async def process(self, event: T) -> None:
        """Process event (implement in subclass)."""
        ...

    async def _send_to_dlq(self, event: T, error: Exception, attempts: int) -> None:
        """Send failed event to DLQ."""
        import traceback

        dead_letter = DeadLetterEvent(
            event_type=type(event).__name__,
            event_data=event.__dict__,
            handler_name=type(self).__name__,
            error_type=type(error).__name__,
            error_message=str(error),
            error_traceback=traceback.format_exc(),
            attempt_count=attempts,
        )

        await self._dlq.add(dead_letter)

    def _calculate_delay(self, attempt: int) -> int:
        """Calculate delay for retry (exponential backoff with jitter)."""
        delay = self._retry_config.initial_delay_ms * (
            self._retry_config.exponential_base ** (attempt - 1)
        )
        delay = min(delay, self._retry_config.max_delay_ms)

        if self._retry_config.jitter:
            delay = delay * (0.5 + random.random() * 0.5)

        return int(delay)
```

### 3. Usage Example

```python
class NotifyUserHandler(ResilientEventHandler[UserRegisteredEvent]):
    """Send notification with automatic retry and DLQ."""

    def __init__(
        self,
        notification_service: NotificationService,
        dlq: DeadLetterQueue,
    ):
        super().__init__(dlq, RetryConfig(max_attempts=3))
        self._notification_service = notification_service

    async def process(self, event: UserRegisteredEvent) -> None:
        """Send notification (may fail)."""
        await self._notification_service.send(
            user_id=event.user_id,
            message="Welcome to our platform!"
        )
```

---

## Compensation Logic

### 1. Compensating Transaction Pattern

```python
from dataclasses import dataclass

@dataclass
class CompensationAction:
    """Action to execute on failure."""

    name: str
    execute: Callable[[], Awaitable[None]]


class CompensatingEventHandler[T](EventHandler[T]):
    """Handler that supports compensation on failure."""

    def __init__(self):
        self._compensations: list[CompensationAction] = []

    def register_compensation(self, action: CompensationAction) -> None:
        """Register compensation action."""
        self._compensations.append(action)

    async def handle(self, event: T) -> None:
        """Handle event with compensation on failure."""
        try:
            await self.process(event)

        except Exception as e:
            logger.error(
                "handler_failed_executing_compensation",
                extra={
                    "event_type": type(event).__name__,
                    "compensations_count": len(self._compensations),
                }
            )

            # Execute compensations in reverse order
            for compensation in reversed(self._compensations):
                try:
                    await compensation.execute()
                    logger.info(f"Compensation {compensation.name} executed")
                except Exception as comp_error:
                    logger.error(
                        "compensation_failed",
                        exc_info=True,
                        extra={"compensation": compensation.name}
                    )

            raise  # Re-raise original exception

    @abstractmethod
    async def process(self, event: T) -> None:
        """Process event (implement in subclass)."""
        ...
```

### 2. Saga Pattern Example

```python
class UserRegistrationSagaHandler(CompensatingEventHandler[UserRegisteredEvent]):
    """Handle user registration with saga pattern."""

    def __init__(
        self,
        email_service: EmailService,
        notification_service: NotificationService,
        user_repository: IUserRepository,
    ):
        super().__init__()
        self._email_service = email_service
        self._notification_service = notification_service
        self._user_repository = user_repository

    async def process(self, event: UserRegisteredEvent) -> None:
        """Process registration with compensations."""

        # Step 1: Send welcome email
        await self._email_service.send_welcome_email(event.email)
        self.register_compensation(
            CompensationAction(
                name="Cancel welcome email",
                execute=lambda: self._email_service.cancel_email(event.user_id)
            )
        )

        # Step 2: Create notification settings
        await self._notification_service.create_settings(event.user_id)
        self.register_compensation(
            CompensationAction(
                name="Delete notification settings",
                execute=lambda: self._notification_service.delete_settings(event.user_id)
            )
        )

        # Step 3: Activate premium trial
        await self._user_repository.activate_trial(event.user_id)
        self.register_compensation(
            CompensationAction(
                name="Cancel premium trial",
                execute=lambda: self._user_repository.deactivate_trial(event.user_id)
            )
        )
```

---

## Idempotency

### 1. Idempotent Event Handler

```python
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC

@dataclass
class ProcessedEvent:
    """Record of processed event for idempotency."""

    event_id: str
    event_type: str
    handler_name: str
    processed_at: datetime
    result: Any | None = None


class IdempotentEventHandler[T](EventHandler[T]):
    """Handler that prevents duplicate processing."""

    def __init__(self, idempotency_store: IdempotencyStore):
        self._store = idempotency_store

    async def handle(self, event: T) -> None:
        """Handle event idempotently."""
        event_id = self._get_event_id(event)
        handler_name = type(self).__name__

        # Check if already processed
        processed = await self._store.get(event_id, handler_name)
        if processed:
            logger.info(
                "event_already_processed_skipping",
                extra={
                    "event_id": event_id,
                    "handler": handler_name,
                    "processed_at": processed.processed_at.isoformat(),
                }
            )
            return  # Skip duplicate

        try:
            # Process event
            result = await self.process(event)

            # Record as processed
            await self._store.set(
                ProcessedEvent(
                    event_id=event_id,
                    event_type=type(event).__name__,
                    handler_name=handler_name,
                    processed_at=datetime.now(UTC),
                    result=result,
                )
            )

        except Exception as e:
            logger.error(
                "event_processing_failed",
                exc_info=True,
                extra={"event_id": event_id, "handler": handler_name}
            )
            raise

    def _get_event_id(self, event: T) -> str:
        """Extract event ID for idempotency check."""
        if hasattr(event, "event_id"):
            return event.event_id
        # Fallback: hash of event data
        import hashlib
        import json
        data = json.dumps(event.__dict__, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    @abstractmethod
    async def process(self, event: T) -> Any:
        """Process event (implement in subclass)."""
        ...
```

### 2. Idempotency Store

```python
class IdempotencyStore:
    """Store for tracking processed events."""

    def __init__(self, cache: QueryCache, ttl_seconds: int = 86400):
        self._cache = cache
        self._ttl = ttl_seconds  # 24 hours default

    async def get(
        self,
        event_id: str,
        handler_name: str,
    ) -> ProcessedEvent | None:
        """Check if event was already processed."""
        key = self._make_key(event_id, handler_name)
        return await self._cache.get(key)

    async def set(self, processed: ProcessedEvent) -> None:
        """Mark event as processed."""
        key = self._make_key(processed.event_id, processed.handler_name)
        await self._cache.set(key, processed, ttl=self._ttl)

    def _make_key(self, event_id: str, handler_name: str) -> str:
        return f"idempotency:{handler_name}:{event_id}"
```

---

## Circuit Breaker Pattern

### 1. Circuit Breaker for External Dependencies

```python
from enum import Enum
from datetime import datetime, timedelta, UTC

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """Circuit breaker for external dependencies."""

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        success_threshold: int = 2,
    ):
        self._failure_threshold = failure_threshold
        self._timeout_seconds = timeout_seconds
        self._success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: datetime | None = None

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker."""
        if self._state == CircuitState.OPEN:
            # Check if timeout expired
            if self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
                logger.info("circuit_breaker_half_open")
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        """Handle successful call."""
        self._failure_count = 0

        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._success_threshold:
                self._state = CircuitState.CLOSED
                self._success_count = 0
                logger.info("circuit_breaker_closed")

    def _on_failure(self) -> None:
        """Handle failed call."""
        self._failure_count += 1
        self._last_failure_time = datetime.now(UTC)
        self._success_count = 0

        if self._failure_count >= self._failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "circuit_breaker_opened",
                extra={
                    "failure_count": self._failure_count,
                    "threshold": self._failure_threshold,
                }
            )

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset."""
        if not self._last_failure_time:
            return False

        elapsed = (datetime.now(UTC) - self._last_failure_time).total_seconds()
        return elapsed >= self._timeout_seconds


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass
```

### 2. Event Handler with Circuit Breaker

```python
class ExternalAPIHandler(EventHandler[UserRegisteredEvent]):
    """Handler that calls external API with circuit breaker."""

    def __init__(self, api_client: APIClient):
        self._api_client = api_client
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            timeout_seconds=60,
        )

    async def handle(self, event: UserRegisteredEvent) -> None:
        """Handle event with circuit breaker protection."""
        try:
            await self._circuit_breaker.call(
                self._api_client.register_user,
                event.user_id,
                event.email,
            )

        except CircuitBreakerOpenError:
            logger.warning(
                "circuit_breaker_open_skipping_event",
                extra={
                    "event_type": type(event).__name__,
                    "user_id": event.user_id,
                }
            )
            # Don't fail the event, just skip (will retry later when circuit closes)

        except Exception as e:
            logger.error(
                "external_api_call_failed",
                exc_info=True,
                extra={"user_id": event.user_id}
            )
            raise
```

---

## Best Practices

### 1. Handler Design Principles

✅ **DO:**
- Make handlers **idempotent** - safe to execute multiple times
- Use **retry with backoff** for transient failures
- Send unrecoverable failures to **Dead Letter Queue**
- Implement **circuit breakers** for external dependencies
- Log failures with **structured logging** for observability
- Keep handlers **focused** - single responsibility
- Use **compensation** for multi-step workflows
- Set **timeouts** for external calls

❌ **DON'T:**
- Block event processing indefinitely
- Retry permanent errors
- Ignore failures silently
- Skip logging and monitoring
- Mix business logic with infrastructure concerns
- Create circular event dependencies
- Perform long-running operations synchronously

### 2. Error Categorization

```python
def categorize_error(error: Exception) -> ErrorCategory:
    """Categorize error for appropriate handling."""

    # Transient - retry
    if is_transient_error(error):
        return ErrorCategory.TRANSIENT

    # Permanent - skip
    if is_permanent_error(error):
        return ErrorCategory.PERMANENT

    # Unknown - DLQ
    return ErrorCategory.UNKNOWN


class ErrorCategory(Enum):
    TRANSIENT = "transient"    # Retry with backoff
    PERMANENT = "permanent"    # Log and skip
    UNKNOWN = "unknown"        # Send to DLQ
```

### 3. Monitoring & Alerts

```python
# Metrics to track
metrics = {
    "event_handler_success": Counter("event_handler_success", ["event_type", "handler"]),
    "event_handler_failure": Counter("event_handler_failure", ["event_type", "handler", "error_type"]),
    "event_handler_retry": Counter("event_handler_retry", ["event_type", "handler"]),
    "event_handler_dlq": Counter("event_handler_dlq", ["event_type", "handler"]),
    "event_handler_duration": Histogram("event_handler_duration_ms", ["event_type", "handler"]),
    "circuit_breaker_state": Gauge("circuit_breaker_state", ["service"]),
}

# Alert conditions
alerts = {
    "high_failure_rate": "event_handler_failure rate > 10% for 5 minutes",
    "dlq_accumulation": "event_handler_dlq count > 100",
    "circuit_breaker_open": "circuit_breaker_state == OPEN for > 2 minutes",
}
```

---

## Testing

### 1. Testing Retry Logic

```python
@pytest.mark.asyncio
async def test_handler_retries_transient_errors():
    """Test handler retries on transient errors."""
    mock_service = Mock()
    mock_service.send.side_effect = [
        TimeoutError(),  # First attempt fails
        TimeoutError(),  # Second attempt fails
        None,           # Third attempt succeeds
    ]

    handler = SendNotificationHandler(mock_service, dlq=Mock())
    event = UserRegisteredEvent(user_id="123")

    await handler.handle(event)

    # Verify retried 3 times
    assert mock_service.send.call_count == 3


@pytest.mark.asyncio
async def test_handler_sends_to_dlq_after_max_retries():
    """Test handler sends to DLQ after max retries."""
    mock_service = Mock()
    mock_service.send.side_effect = TimeoutError()  # Always fails

    mock_dlq = Mock()
    handler = SendNotificationHandler(
        mock_service,
        dlq=mock_dlq,
        retry_config=RetryConfig(max_attempts=2)
    )

    event = UserRegisteredEvent(user_id="123")
    await handler.handle(event)

    # Verify sent to DLQ
    mock_dlq.add.assert_called_once()
```

### 2. Testing Idempotency

```python
@pytest.mark.asyncio
async def test_idempotent_handler_skips_duplicate():
    """Test idempotent handler skips duplicate events."""
    store = InMemoryIdempotencyStore()
    handler = IdempotentNotificationHandler(store)

    event = UserRegisteredEvent(user_id="123", event_id="evt-123")

    # Process first time
    result1 = await handler.handle(event)
    assert result1 is not None

    # Process duplicate
    result2 = await handler.handle(event)
    # Should be skipped (no exception, no effect)

    # Verify processed only once
    assert handler.process_count == 1
```

---

## References

- `src/application/common/cqrs/event_bus.py` - Event bus implementation
- `src/domain/users/events.py` - Domain events
- `docs/architecture/cqrs-implementation.md` - CQRS architecture
- Saga Pattern: https://microservices.io/patterns/data/saga.html
- Circuit Breaker: https://martinfowler.com/bliki/CircuitBreaker.html

---

**Status:** ✅ Documented
**Version:** 1.0
**Last Updated:** 2025-01-02
