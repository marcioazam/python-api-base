# Monitoring

## Overview

Monitoring provides visibility into system health, performance, and behavior.

## Metrics

### Prometheus Endpoint

```
GET /metrics
```

### Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | Request latency |
| `http_requests_in_progress` | Gauge | Active requests |
| `db_pool_size` | Gauge | Database pool size |
| `cache_hits_total` | Counter | Cache hit count |
| `cache_misses_total` | Counter | Cache miss count |

### Grafana Queries

```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

# P99 latency
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

## Alerts

### Critical Alerts

| Alert | Condition | Action |
|-------|-----------|--------|
| High Error Rate | Error rate > 5% | Page on-call |
| High Latency | P99 > 5s | Page on-call |
| Database Down | Health check fails | Page on-call |

### Warning Alerts

| Alert | Condition | Action |
|-------|-----------|--------|
| Elevated Error Rate | Error rate > 1% | Notify team |
| Pool Exhaustion | Pool > 80% | Notify team |

## Dashboards

### Application Dashboard

- Request rate by endpoint
- Error rate by status code
- Latency percentiles
- Active connections

### Infrastructure Dashboard

- Database connections
- Cache hit ratio
- Memory usage
- CPU usage

## Related

- [Observability](../layers/infrastructure/observability.md)
- [Runbooks](runbooks/database-issues.md)
