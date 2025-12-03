# Runbooks

## Overview

Procedimentos operacionais para resolução de incidentes.

## Quick Reference

| Runbook | Severity | SLO Impact | Recovery Time |
|---------|----------|------------|---------------|
| [Database Issues](database-issues.md) | P1 | High | 5-30 min |
| [Cache Failures](../../runbooks/cache-failures.md) | P2 | Medium | 5-15 min |
| [Circuit Breaker Open](../../runbooks/circuit-breaker-open.md) | P2 | Medium | 5-30 min |
| [High Latency](high-latency.md) | P2 | Medium | 15-60 min |
| [Memory Issues](memory-issues.md) | P1 | High | 10-30 min |
| [Kafka Lag](kafka-lag.md) | P2 | Medium | 15-45 min |

## Severity Levels

| Level | Description | Response Time |
|-------|-------------|---------------|
| P1 | Critical - Service down | 15 min |
| P2 | High - Degraded service | 30 min |
| P3 | Medium - Minor impact | 2 hours |
| P4 | Low - No user impact | 24 hours |

## Escalation Path

1. **Level 1:** On-call engineer
2. **Level 2:** Team lead
3. **Level 3:** Engineering manager
4. **Level 4:** CTO

## Creating New Runbooks

Use the [runbook template](../../templates/runbook-template.md) for new runbooks.

## Post-Incident

After resolving an incident:

1. Update runbook if needed
2. Create post-mortem document
3. File follow-up tickets
4. Update monitoring/alerting
