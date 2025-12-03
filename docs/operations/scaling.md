# Scaling Guide

## Overview

Este guia documenta estratégias de escalabilidade para o Python API Base, incluindo escalabilidade horizontal, vertical e auto-scaling.

## Scaling Strategies

### Horizontal Scaling (Scale Out)

Adicionar mais instâncias da aplicação para distribuir carga.

```yaml
# Kubernetes HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: python-api-base-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: python-api-base
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

### Vertical Scaling (Scale Up)

Aumentar recursos (CPU/memória) de instâncias existentes.

```yaml
# Resource requests and limits
resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
  limits:
    cpu: "2000m"
    memory: "2Gi"
```

## Resource Estimates

### Per Instance Requirements

| Workload | CPU Request | CPU Limit | Memory Request | Memory Limit |
|----------|-------------|-----------|----------------|--------------|
| Light | 250m | 500m | 256Mi | 512Mi |
| Medium | 500m | 1000m | 512Mi | 1Gi |
| Heavy | 1000m | 2000m | 1Gi | 2Gi |

### Scaling Thresholds

| Metric | Scale Up | Scale Down |
|--------|----------|------------|
| CPU Utilization | > 70% | < 30% |
| Memory Utilization | > 80% | < 40% |
| Request Latency P99 | > 500ms | < 100ms |
| Request Queue | > 100 | < 10 |

## Component Scaling

### API Pods

```yaml
# Deployment scaling
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
```

### Database (PostgreSQL)

| Strategy | Use Case | Configuration |
|----------|----------|---------------|
| Read Replicas | Read-heavy workloads | 1 primary + N replicas |
| Connection Pooling | High concurrency | PgBouncer with 100+ connections |
| Vertical Scaling | Write-heavy workloads | Increase CPU/RAM |

```yaml
# PgBouncer configuration
[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
reserve_pool_size = 5
```

### Redis Cache

| Strategy | Use Case | Configuration |
|----------|----------|---------------|
| Cluster Mode | High availability | 3+ nodes with replication |
| Sentinel | Automatic failover | 3 sentinels + replicas |
| Memory Scaling | Large datasets | Increase maxmemory |

```yaml
# Redis cluster configuration
cluster-enabled yes
cluster-node-timeout 5000
maxmemory 2gb
maxmemory-policy allkeys-lru
```

### Kafka

| Strategy | Use Case | Configuration |
|----------|----------|---------------|
| Partition Scaling | Increase throughput | Add partitions |
| Consumer Groups | Parallel processing | Multiple consumers |
| Broker Scaling | High availability | 3+ brokers |

```properties
# Topic configuration
num.partitions=12
replication.factor=3
min.insync.replicas=2
```

## Auto-Scaling Configuration

### Kubernetes HPA with Custom Metrics

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: python-api-base-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: python-api-base
  minReplicas: 2
  maxReplicas: 20
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Pods
          value: 2
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "100"
```

### KEDA (Kubernetes Event-Driven Autoscaling)

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: python-api-base-scaler
spec:
  scaleTargetRef:
    name: python-api-base
  minReplicaCount: 2
  maxReplicaCount: 20
  triggers:
    - type: prometheus
      metadata:
        serverAddress: http://prometheus:9090
        metricName: http_request_duration_seconds
        threshold: "0.5"
        query: |
          histogram_quantile(0.99, 
            sum(rate(http_request_duration_seconds_bucket{app="python-api-base"}[5m])) 
            by (le))
```

## Load Testing

### Baseline Performance

```bash
# Using k6 for load testing
k6 run --vus 100 --duration 5m load-test.js
```

```javascript
// load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 50 },
    { duration: '3m', target: 100 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(99)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const res = http.get('http://api.example.com/api/v1/health');
  check(res, { 'status is 200': (r) => r.status === 200 });
  sleep(1);
}
```

### Capacity Planning

| Metric | Target | Current | Headroom |
|--------|--------|---------|----------|
| RPS | 1000 | 600 | 40% |
| P99 Latency | 500ms | 200ms | 60% |
| Error Rate | < 0.1% | 0.01% | OK |
| CPU Usage | < 70% | 45% | 25% |

## Monitoring Scaling Events

### Prometheus Alerts

```yaml
groups:
  - name: scaling
    rules:
      - alert: HighCPUUsage
        expr: |
          avg(rate(container_cpu_usage_seconds_total{pod=~"python-api-base.*"}[5m])) > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: High CPU usage detected
          
      - alert: ScalingLimitReached
        expr: |
          kube_hpa_status_current_replicas == kube_hpa_spec_max_replicas
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: HPA at maximum replicas
```

### Grafana Dashboard

Key panels for scaling monitoring:
- Pod count over time
- CPU/Memory utilization per pod
- Request rate vs pod count
- HPA scaling events
- Response time percentiles

## Best Practices

1. **Start Conservative**: Begin with lower limits and scale up based on data
2. **Monitor Before Scaling**: Understand current performance before changes
3. **Test Scaling**: Validate auto-scaling behavior in staging
4. **Set Appropriate Cooldowns**: Prevent thrashing with stabilization windows
5. **Plan for Failures**: Ensure minimum replicas handle failure scenarios
6. **Document Decisions**: Record scaling decisions in ADRs

## Related Documentation

- [Deployment Guide](deployment.md)
- [Monitoring Guide](monitoring.md)
- [Infrastructure Overview](../infrastructure/index.md)
