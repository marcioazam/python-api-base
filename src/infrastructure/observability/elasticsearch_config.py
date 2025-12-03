"""Elasticsearch configuration for log shipping.

**Feature: observability-infrastructure**
**Requirement: R1.3 - Ship logs to Elasticsearch**
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ElasticsearchConfig:
    """Configuration for Elasticsearch connection.

    Attributes:
        hosts: List of Elasticsearch hosts
        index_prefix: Prefix for index names (e.g., "logs-api")
        batch_size: Number of logs to batch before sending
        flush_interval_seconds: Max seconds between flushes
        username: Optional username for authentication
        password: Optional password for authentication
        api_key: Optional API key for authentication
        use_ssl: Whether to use SSL/TLS
        verify_certs: Whether to verify SSL certificates
        ca_certs: Path to CA certificates
        timeout: Connection timeout in seconds
        max_retries: Maximum retry attempts
        retry_on_timeout: Whether to retry on timeout
    """

    hosts: list[str] = field(default_factory=lambda: ["http://localhost:9200"])
    index_prefix: str = "logs-python-api-base"
    batch_size: int = 100
    flush_interval_seconds: float = 5.0
    username: str | None = None
    password: str | None = None
    api_key: str | tuple[str, str] | None = None
    use_ssl: bool = False
    verify_certs: bool = True
    ca_certs: str | None = None
    timeout: int = 30
    max_retries: int = 3
    retry_on_timeout: bool = True


# Index template for ECS-compatible logs
ECS_INDEX_TEMPLATE = {
    "index_patterns": ["logs-*"],
    "template": {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 1,
            "index.lifecycle.name": "logs-policy",
            "index.lifecycle.rollover_alias": "logs",
        },
        "mappings": {
            "properties": {
                "@timestamp": {"type": "date"},
                "message": {"type": "text"},
                "log.level": {"type": "keyword"},
                "log.logger": {"type": "keyword"},
                "service.name": {"type": "keyword"},
                "service.version": {"type": "keyword"},
                "service.environment": {"type": "keyword"},
                "trace.id": {"type": "keyword"},
                "correlation_id": {"type": "keyword"},
                "request_id": {"type": "keyword"},
                "span_id": {"type": "keyword"},
                "http.method": {"type": "keyword"},
                "http.status_code": {"type": "integer"},
                "http.url": {"type": "keyword"},
                "http.path": {"type": "keyword"},
                "user.id": {"type": "keyword"},
                "error.message": {"type": "text"},
                "error.type": {"type": "keyword"},
                "error.stack_trace": {"type": "text"},
            }
        },
    },
}
