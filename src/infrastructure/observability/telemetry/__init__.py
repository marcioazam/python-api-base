"""OpenTelemetry integration for distributed tracing and metrics.

This module provides:
- TracerProvider and MeterProvider initialization
- OTLP exporter configuration
- @traced decorator for custom spans

Feature: file-size-compliance-phase2
"""

from .noop import (
    _NoOpCounter,
    _NoOpHistogram,
    _NoOpMeter,
    _NoOpSpan,
    _NoOpTracer,
)
from .service import (
    P,
    TelemetryProvider,
    _current_span_id,
    _current_trace_id,
    get_current_span_id,
    get_current_trace_id,
    get_telemetry,
    init_telemetry,
    traced,
)

__all__ = [
    "P",
    "TelemetryProvider",
    "_NoOpCounter",
    "_NoOpHistogram",
    "_NoOpMeter",
    "_NoOpSpan",
    "_NoOpTracer",
    "_current_span_id",
    "_current_trace_id",
    "get_current_span_id",
    "get_current_trace_id",
    "get_telemetry",
    "init_telemetry",
    "traced",
]
