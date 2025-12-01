"""OpenTelemetry integration for distributed tracing and metrics.

This module provides:
- TracerProvider and MeterProvider initialization
- OTLP exporter configuration
- @traced decorator for custom spa

Feature: file-size-compliance-phase2
"""

from .constants import *
from .service import *

from .service import _current_trace_id, _current_span_id

__all__ = ['P', 'T', 'TelemetryProvider', '_NoOpCounter', '_NoOpHistogram', '_NoOpMeter', '_NoOpSpan', '_NoOpTracer', 'get_current_span_id', 'get_current_trace_id', 'get_telemetry', 'init_telemetry', 'traced', '_current_trace_id', '_current_span_id']
