"""Retry policies for task queue with PEP 695 generics.

**Feature: architecture-validation-fixes-2025**
**Validates: Requirements 23.4**
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import random


class RetryPolicy(ABC):
    """Abstract base class for retry policies.

    **Feature: architecture-validation-fixes-2025**
    **Validates: Requirements 23.4**
    """

    @abstractmethod
    def get_delay(self, attempt: int) -> float:
        """Calculate delay before next retry in seconds.

        Args:
            attempt: Current attempt number (1-indexed).

        Returns:
            Delay in seconds before next retry.
        """
        ...

    @abstractmethod
    def should_retry(self, attempt: int, max_attempts: int) -> bool:
        """Check if task should be retried.

        Args:
            attempt: Current attempt number.
            max_attempts: Maximum allowed attempts.

        Returns:
            True if should retry.
        """
        ...


@dataclass(frozen=True, slots=True)
class NoRetry(RetryPolicy):
    """Policy that never retries."""

    def get_delay(self, attempt: int) -> float:
        """No delay - never retries."""
        return 0.0

    def should_retry(self, attempt: int, max_attempts: int) -> bool:
        """Never retry."""
        return False


@dataclass(frozen=True, slots=True)
class FixedDelay(RetryPolicy):
    """Retry with fixed delay between attempts.

    Attributes:
        delay_seconds: Fixed delay between retries.
    """

    delay_seconds: float = 5.0

    def get_delay(self, attempt: int) -> float:
        """Return fixed delay."""
        return self.delay_seconds

    def should_retry(self, attempt: int, max_attempts: int) -> bool:
        """Retry if under max attempts."""
        return attempt < max_attempts


@dataclass(frozen=True, slots=True)
class ExponentialBackoff(RetryPolicy):
    """Retry with exponential backoff and optional jitter.

    Delay formula: min(max_delay, base_delay * (multiplier ^ attempt)) + jitter

    Attributes:
        base_delay: Initial delay in seconds.
        multiplier: Multiplier for each subsequent attempt.
        max_delay: Maximum delay cap in seconds.
        jitter: Add random jitter (0-1 multiplied by delay).

    Example:
        With base_delay=1, multiplier=2:
        - Attempt 1: 1s delay
        - Attempt 2: 2s delay
        - Attempt 3: 4s delay
        - Attempt 4: 8s delay

    **Feature: architecture-validation-fixes-2025**
    **Validates: Requirements 23.4**
    """

    base_delay: float = 1.0
    multiplier: float = 2.0
    max_delay: float = 300.0  # 5 minutes
    jitter: float = 0.1

    def get_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with optional jitter."""
        delay = self.base_delay * (self.multiplier ** (attempt - 1))
        delay = min(delay, self.max_delay)

        if self.jitter > 0:
            jitter_amount = delay * self.jitter * random.random()
            delay += jitter_amount

        return delay

    def should_retry(self, attempt: int, max_attempts: int) -> bool:
        """Retry if under max attempts."""
        return attempt < max_attempts


# Default retry policy
DEFAULT_RETRY_POLICY = ExponentialBackoff()
