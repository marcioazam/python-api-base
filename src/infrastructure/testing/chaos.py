"""Chaos engineering middleware for fault injection.

**Feature: api-architecture-analysis, Task 13.3: Chaos Engineering**
**Validates: Requirements 6.1, 6.2**

Provides fault injection for testing system resilience.
"""

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum

from pydantic import BaseModel


class FaultType(str, Enum):
    """Types of faults that can be injected."""

    LATENCY = "latency"
    ERROR = "error"
    TIMEOUT = "timeout"
    EXCEPTION = "exception"
    PARTIAL_FAILURE = "partial_failure"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


@dataclass
class FaultConfig:
    """Fault injection configuration.

    Attributes:
        fault_type: Type of fault to inject.
        probability: Probability of fault (0.0-1.0).
        latency_ms: Latency to add (for LATENCY fault).
        error_code: HTTP error code (for ERROR fault).
        error_message: Error message.
        timeout_ms: Timeout duration (for TIMEOUT fault).
        exception_class: Exception class to raise.
        affected_endpoints: Endpoints to affect (empty = all).
        enabled: Whether fault is enabled.
    """

    fault_type: FaultType
    probability: float = 0.1
    latency_ms: int = 1000
    error_code: int = 500
    error_message: str = "Chaos fault injected"
    timeout_ms: int = 30000
    exception_class: type[Exception] = Exception
    affected_endpoints: list[str] = field(default_factory=list)
    enabled: bool = True


class ChaosStats(BaseModel):
    """Chaos injection statistics.

    Attributes:
        total_requests: Total requests processed.
        faults_injected: Number of faults injected.
        latency_faults: Latency faults injected.
        error_faults: Error faults injected.
        timeout_faults: Timeout faults injected.
        exception_faults: Exception faults injected.
    """

    total_requests: int = 0
    faults_injected: int = 0
    latency_faults: int = 0
    error_faults: int = 0
    timeout_faults: int = 0
    exception_faults: int = 0


class ChaosError(Exception):
    """Chaos-injected error."""

    def __init__(self, message: str, fault_type: FaultType) -> None:
        super().__init__(message)
        self.fault_type = fault_type


class ChaosEngine:
    """Chaos engineering engine for fault injection.

    Provides controlled fault injection for testing system resilience.
    """

    def __init__(self, seed: int | None = None) -> None:
        """Initialize chaos engine.

        Args:
            seed: Random seed for reproducibility.
        """
        self._faults: list[FaultConfig] = []
        self._stats = ChaosStats()
        self._enabled = False
        self._random = random.Random(seed)

    def add_fault(self, config: FaultConfig) -> None:
        """Add a fault configuration.

        Args:
            config: Fault configuration.
        """
        self._faults.append(config)

    def remove_fault(self, fault_type: FaultType) -> bool:
        """Remove faults of a specific type.

        Args:
            fault_type: Type of fault to remove.

        Returns:
            True if any faults were removed.
        """
        initial_count = len(self._faults)
        self._faults = [f for f in self._faults if f.fault_type != fault_type]
        return len(self._faults) < initial_count

    def clear_faults(self) -> None:
        """Remove all fault configurations."""
        self._faults.clear()

    def enable(self) -> None:
        """Enable chaos injection."""
        self._enabled = True

    def disable(self) -> None:
        """Disable chaos injection."""
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        """Check if chaos is enabled."""
        return self._enabled

    def should_inject(self, config: FaultConfig, endpoint: str = "") -> bool:
        """Determine if fault should be injected.

        Args:
            config: Fault configuration.
            endpoint: Current endpoint.

        Returns:
            True if fault should be injected.
        """
        if not self._enabled or not config.enabled:
            return False

        # Check endpoint filter
        if config.affected_endpoints:
            if not any(endpoint.startswith(e) for e in config.affected_endpoints):
                return False

        # Check probability
        return self._random.random() < config.probability

    async def maybe_inject_fault(self, endpoint: str = "") -> FaultConfig | None:
        """Maybe inject a fault based on configuration.

        Args:
            endpoint: Current endpoint.

        Returns:
            Injected fault config or None.
        """
        self._stats.total_requests += 1

        if not self._enabled:
            return None

        for config in self._faults:
            if self.should_inject(config, endpoint):
                await self._inject_fault(config)
                return config

        return None

    async def _inject_fault(self, config: FaultConfig) -> None:
        """Inject a specific fault.

        Args:
            config: Fault configuration.

        Raises:
            ChaosError: For error/exception faults.
            asyncio.TimeoutError: For timeout faults.
        """
        self._stats.faults_injected += 1

        if config.fault_type == FaultType.LATENCY:
            self._stats.latency_faults += 1
            await asyncio.sleep(config.latency_ms / 1000)

        elif config.fault_type == FaultType.ERROR:
            self._stats.error_faults += 1
            raise ChaosError(config.error_message, config.fault_type)

        elif config.fault_type == FaultType.TIMEOUT:
            self._stats.timeout_faults += 1
            await asyncio.sleep(config.timeout_ms / 1000)
            raise asyncio.TimeoutError("Chaos timeout")

        elif config.fault_type == FaultType.EXCEPTION:
            self._stats.exception_faults += 1
            raise config.exception_class(config.error_message)

    def get_stats(self) -> ChaosStats:
        """Get chaos statistics.

        Returns:
            Current statistics.
        """
        return self._stats.model_copy()

    def reset_stats(self) -> None:
        """Reset statistics."""
        self._stats = ChaosStats()


@dataclass
class ChaosExperiment:
    """Chaos experiment definition.

    Attributes:
        name: Experiment name.
        description: Experiment description.
        faults: Faults to inject.
        duration_seconds: Experiment duration.
        started_at: Start time.
        ended_at: End time.
    """

    name: str
    description: str = ""
    faults: list[FaultConfig] = field(default_factory=list)
    duration_seconds: int = 60
    started_at: datetime | None = None
    ended_at: datetime | None = None


class ChaosExperimentRunner:
    """Runner for chaos experiments.

    Manages chaos experiments with defined duration and faults.
    """

    def __init__(self, engine: ChaosEngine) -> None:
        """Initialize experiment runner.

        Args:
            engine: Chaos engine to use.
        """
        self._engine = engine
        self._current_experiment: ChaosExperiment | None = None
        self._experiment_task: asyncio.Task | None = None

    async def start_experiment(self, experiment: ChaosExperiment) -> None:
        """Start a chaos experiment.

        Args:
            experiment: Experiment to run.
        """
        if self._current_experiment:
            await self.stop_experiment()

        self._current_experiment = experiment
        experiment.started_at = datetime.now(UTC)

        # Add faults to engine
        for fault in experiment.faults:
            self._engine.add_fault(fault)

        self._engine.enable()

        # Schedule experiment end
        self._experiment_task = asyncio.create_task(
            self._run_experiment(experiment.duration_seconds)
        )

    async def _run_experiment(self, duration: int) -> None:
        """Run experiment for specified duration.

        Args:
            duration: Duration in seconds.
        """
        await asyncio.sleep(duration)
        await self.stop_experiment()

    async def stop_experiment(self) -> ChaosExperiment | None:
        """Stop the current experiment.

        Returns:
            The stopped experiment or None.
        """
        if not self._current_experiment:
            return None

        experiment = self._current_experiment
        experiment.ended_at = datetime.now(UTC)

        # Remove faults
        for fault in experiment.faults:
            self._engine.remove_fault(fault.fault_type)

        self._engine.disable()

        if self._experiment_task:
            self._experiment_task.cancel()
            try:
                await self._experiment_task
            except asyncio.CancelledError:
                pass

        self._current_experiment = None
        return experiment

    @property
    def is_running(self) -> bool:
        """Check if experiment is running."""
        return self._current_experiment is not None


def create_latency_fault(
    latency_ms: int = 1000,
    probability: float = 0.1,
    endpoints: list[str] | None = None,
) -> FaultConfig:
    """Create a latency fault configuration.

    Args:
        latency_ms: Latency to add in milliseconds.
        probability: Probability of fault.
        endpoints: Affected endpoints.

    Returns:
        Fault configuration.
    """
    return FaultConfig(
        fault_type=FaultType.LATENCY,
        latency_ms=latency_ms,
        probability=probability,
        affected_endpoints=endpoints or [],
    )


def create_error_fault(
    error_code: int = 500,
    probability: float = 0.1,
    message: str = "Chaos error",
    endpoints: list[str] | None = None,
) -> FaultConfig:
    """Create an error fault configuration.

    Args:
        error_code: HTTP error code.
        probability: Probability of fault.
        message: Error message.
        endpoints: Affected endpoints.

    Returns:
        Fault configuration.
    """
    return FaultConfig(
        fault_type=FaultType.ERROR,
        error_code=error_code,
        error_message=message,
        probability=probability,
        affected_endpoints=endpoints or [],
    )


def create_timeout_fault(
    timeout_ms: int = 30000,
    probability: float = 0.05,
    endpoints: list[str] | None = None,
) -> FaultConfig:
    """Create a timeout fault configuration.

    Args:
        timeout_ms: Timeout duration in milliseconds.
        probability: Probability of fault.
        endpoints: Affected endpoints.

    Returns:
        Fault configuration.
    """
    return FaultConfig(
        fault_type=FaultType.TIMEOUT,
        timeout_ms=timeout_ms,
        probability=probability,
        affected_endpoints=endpoints or [],
    )
