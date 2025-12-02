"""Observability infrastructure.

Provides:
- Correlation ID propagation
- Structured logging with ECS compatibility
- Elasticsearch log shipping
- OpenTelemetry tracing
- Prometheus metrics

**Feature: observability-infrastructure**
"""

from infrastructure.observability.correlation_id import (
    CorrelationConfig,
    CorrelationContext,
    CorrelationContextManager,
    CorrelationService,
    add_correlation_context,
    get_correlation_id,
    set_correlation_id,
    get_request_id,
    set_request_id,
    clear_context,
)
from infrastructure.observability.logging_middleware import (
    LoggingMiddleware,
    create_logging_middleware,
)
from infrastructure.observability.elasticsearch_handler import (
    ElasticsearchConfig,
    ElasticsearchHandler,
    ElasticsearchLogProcessor,
    create_elasticsearch_handler,
)
from infrastructure.observability.middleware import TracingMiddleware
from infrastructure.observability.metrics import CacheMetrics

__all__ = [
    # Correlation
    "CorrelationConfig",
    "CorrelationContext",
    "CorrelationContextManager",
    "CorrelationService",
    "add_correlation_context",
    "get_correlation_id",
    "set_correlation_id",
    "get_request_id",
    "set_request_id",
    "clear_context",
    # Logging
    "LoggingMiddleware",
    "create_logging_middleware",
    # Elasticsearch
    "ElasticsearchConfig",
    "ElasticsearchHandler",
    "ElasticsearchLogProcessor",
    "create_elasticsearch_handler",
    # Tracing
    "TracingMiddleware",
    # Metrics
    "CacheMetrics",
]
