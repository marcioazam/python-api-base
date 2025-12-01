"""No-op implementations for telemetry when OpenTelemetry is not available.

Feature: file-size-compliance-phase2
"""

from typing import Any


class _NoOpSpan:
    """No-op span for when tracing is disabled."""

    def __enter__(self) -> "_NoOpSpan":
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        pass

    def record_exception(self, exception: BaseException) -> None:
        pass

    def set_status(self, status: Any, description: str | None = None) -> None:
        pass


class _NoOpTracer:
    """No-op tracer for when OpenTelemetry is not available."""

    def start_as_current_span(
        self,
        name: str,
        **kwargs: Any,
    ) -> _NoOpSpan:
        return _NoOpSpan()

    def start_span(self, name: str, **kwargs: Any) -> _NoOpSpan:
        return _NoOpSpan()


class _NoOpMeter:
    """No-op meter for when OpenTelemetry is not available."""

    def create_counter(self, name: str, **kwargs: Any) -> "_NoOpCounter":
        return _NoOpCounter()

    def create_histogram(self, name: str, **kwargs: Any) -> "_NoOpHistogram":
        return _NoOpHistogram()

    def create_up_down_counter(self, name: str, **kwargs: Any) -> "_NoOpCounter":
        return _NoOpCounter()


class _NoOpCounter:
    """No-op counter."""

    def add(self, amount: int | float, attributes: dict[str, Any] | None = None) -> None:
        pass


class _NoOpHistogram:
    """No-op histogram."""

    def record(self, amount: int | float, attributes: dict[str, Any] | None = None) -> None:
        pass
