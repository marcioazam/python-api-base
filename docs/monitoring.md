# Monitoramento

Este documento descreve a stack de observabilidade do Python API Base.

## Visão Geral

O sistema implementa os três pilares da observabilidade:
- **Logs**: Estruturados em JSON com structlog
- **Traces**: Distribuídos com OpenTelemetry
- **Metrics**: Expostas para Prometheus

## 1. Prometheus Metrics

### Endpoint
```
GET /metrics
```

### HTTP Metrics

| Métrica | Tipo | Labels | Descrição |
|---------|------|--------|-----------|
| `http_requests_total` | Counter | method, endpoint, status | Total de requisições HTTP |
| `http_request_duration_seconds` | Histogram | method, endpoint | Latência das requisições |
| `http_requests_in_progress` | Gauge | - | Requisições em andamento |

### Database Metrics

| Métrica | Tipo | Labels | Descrição |
|---------|------|--------|-----------|
| `db_pool_connections` | Gauge | state | Conexões no pool (active, idle) |
| `db_query_duration_seconds` | Histogram | operation | Duração das queries |
| `db_errors_total` | Counter | type | Erros de banco de dados |

### Cache Metrics

| Métrica | Tipo | Labels | Descrição |
|---------|------|--------|-----------|
| `cache_hits_total` | Counter | cache_name | Cache hits |
| `cache_misses_total` | Counter | cache_name | Cache misses |
| `cache_errors_total` | Counter | cache_name, error_type | Erros de cache |
| `cache_operation_duration_seconds` | Histogram | operation | Duração das operações |

### Circuit Breaker Metrics

| Métrica | Tipo | Labels | Descrição |
|---------|------|--------|-----------|
| `circuit_breaker_state` | Gauge | service | Estado (0=closed, 1=open, 2=half_open) |
| `circuit_breaker_failures_total` | Counter | service | Total de falhas |
| `circuit_breaker_successes_total` | Counter | service | Total de sucessos |

### Business Metrics

| Métrica | Tipo | Labels | Descrição |
|---------|------|--------|-----------|
| `users_created_total` | Counter | - | Usuários criados |
| `authentication_attempts_total` | Counter | result | Tentativas de autenticação |
| `api_rate_limit_exceeded_total` | Counter | endpoint | Rate limit excedido |

## 2. OpenTelemetry Traces

### Configuração

```python
# src/core/config/observability.py
class ObservabilitySettings(BaseSettings):
    otlp_endpoint: str | None = None
    service_name: str = "python-api-base"
    trace_sample_rate: float = 1.0
```

### Span Naming Convention

```
<service>.<operation>
```

Exemplos:
- `http.request`
- `db.query`
- `cache.get`
- `external.api_call`

### Span Attributes

| Atributo | Descrição |
|----------|-----------|
| `http.method` | Método HTTP |
| `http.url` | URL da requisição |
| `http.status_code` | Código de status |
| `db.system` | Sistema de banco (postgresql) |
| `db.statement` | Query SQL (sanitizada) |
| `cache.key` | Chave do cache |
| `user.id` | ID do usuário (se autenticado) |

### Trace Context Propagation

Headers propagados:
- `traceparent`
- `tracestate`
- `X-Correlation-ID`

## 3. Structured Logs

### Formato JSON

```json
{
    "timestamp": "2024-12-02T10:30:00.000Z",
    "level": "info",
    "event": "user_created",
    "logger": "application.users",
    "user_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
    "email": "user@example.com",
    "trace_id": "abc123def456",
    "span_id": "789ghi",
    "correlation_id": "req-123",
    "service": "python-api-base",
    "environment": "production"
}
```

### Log Levels

| Level | Uso |
|-------|-----|
| `DEBUG` | Informações detalhadas para debugging |
| `INFO` | Eventos normais do sistema |
| `WARNING` | Situações inesperadas mas não críticas |
| `ERROR` | Erros que afetam operações |
| `CRITICAL` | Erros que afetam o sistema inteiro |

### Campos Padrão

| Campo | Descrição |
|-------|-----------|
| `timestamp` | ISO 8601 timestamp |
| `level` | Nível do log |
| `event` | Nome do evento |
| `logger` | Nome do logger |
| `trace_id` | ID do trace OpenTelemetry |
| `span_id` | ID do span atual |
| `correlation_id` | ID de correlação da requisição |
| `service` | Nome do serviço |
| `environment` | Ambiente (dev, staging, prod) |

### PII Redaction

Campos sensíveis são automaticamente redactados:
- `password` → `[REDACTED]`
- `token` → `[REDACTED]`
- `secret` → `[REDACTED]`
- `authorization` → `[REDACTED]`

## 4. Grafana Dashboards

### API Overview Dashboard

```json
{
  "panels": [
    {
      "title": "Request Rate",
      "query": "rate(http_requests_total[5m])"
    },
    {
      "title": "Error Rate",
      "query": "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m])"
    },
    {
      "title": "P99 Latency",
      "query": "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))"
    },
    {
      "title": "Active Requests",
      "query": "http_requests_in_progress"
    }
  ]
}
```

### Database Dashboard

```json
{
  "panels": [
    {
      "title": "Connection Pool",
      "query": "db_pool_connections"
    },
    {
      "title": "Query Latency P95",
      "query": "histogram_quantile(0.95, rate(db_query_duration_seconds_bucket[5m]))"
    },
    {
      "title": "Error Rate",
      "query": "rate(db_errors_total[5m])"
    }
  ]
}
```

### Cache Dashboard

```json
{
  "panels": [
    {
      "title": "Hit Rate",
      "query": "rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m]))"
    },
    {
      "title": "Operation Latency",
      "query": "histogram_quantile(0.95, rate(cache_operation_duration_seconds_bucket[5m]))"
    }
  ]
}
```

## 5. Alerting Rules

### Critical Alerts

```yaml
groups:
  - name: critical
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"

      - alert: ServiceDown
        expr: up{job="python-api-base"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
```

### Warning Alerts

```yaml
groups:
  - name: warning
    rules:
      - alert: HighLatency
        expr: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"

      - alert: CircuitBreakerOpen
        expr: circuit_breaker_state == 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Circuit breaker is open"

      - alert: LowCacheHitRate
        expr: rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m])) < 0.5
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Low cache hit rate"
```

## 6. Health Checks

### Endpoints

| Endpoint | Propósito | Kubernetes Probe |
|----------|-----------|------------------|
| `/health/live` | Liveness | livenessProbe |
| `/health/ready` | Readiness | readinessProbe |
| `/health/startup` | Startup | startupProbe |

### Response Format

```json
{
    "status": "healthy",
    "checks": {
        "database": "healthy",
        "redis": "healthy",
        "kafka": "degraded"
    },
    "version": "1.0.0",
    "uptime": 3600
}
```

## Referências

- [ADR-011: Observability Stack](adr/ADR-011-observability-stack.md)
- [Configuration Guide](configuration.md)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
