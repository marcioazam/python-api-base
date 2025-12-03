# Runbook: Kafka Consumer Lag

## Metadata

- **Severity:** P2
- **SLO Impact:** Event processing delays, data inconsistency
- **Recovery Time Estimate:** 15-45 minutes
- **Last Updated:** December 2025
- **Owner:** Platform Team

## Symptoms

- Growing consumer lag
- Events not being processed
- Data sync delays
- Kafka lag alerts

## Diagnosis

### Step 1: Check Consumer Lag

```bash
# Check lag for consumer group
kafka-consumer-groups.sh --bootstrap-server kafka:9092 \
  --describe --group python-api-base
```

**Expected:** Lag < 1000 messages

### Step 2: Check Consumer Status

```bash
# Check if consumers are running
kubectl get pods -l app=kafka-consumer

# Check consumer logs
kubectl logs -l app=kafka-consumer --tail=100
```

### Step 3: Check Kafka Broker Health

```bash
# Check broker status
kafka-broker-api-versions.sh --bootstrap-server kafka:9092

# Check topic partitions
kafka-topics.sh --bootstrap-server kafka:9092 \
  --describe --topic events.user
```

### Step 4: Check Processing Errors

```bash
# Check for processing errors
kubectl logs -l app=kafka-consumer | grep -i error | tail -20

# Check dead letter queue
kafka-console-consumer.sh --bootstrap-server kafka:9092 \
  --topic events.user.dlq --from-beginning --max-messages 10
```

## Resolution

### Option A: Scale Consumers

```bash
# Scale consumer pods
kubectl scale deployment kafka-consumer --replicas=5

# Verify
kubectl get pods -l app=kafka-consumer
```

### Option B: Restart Consumers

```bash
# Rolling restart
kubectl rollout restart deployment kafka-consumer

# Verify
kubectl rollout status deployment kafka-consumer
```

### Option C: Increase Partitions

```bash
# Add partitions (cannot be undone)
kafka-topics.sh --bootstrap-server kafka:9092 \
  --alter --topic events.user --partitions 10
```

### Option D: Fix Processing Errors

If errors causing slowdown:

1. Check error logs
2. Fix processing code
3. Reprocess failed messages

```bash
# Reprocess from DLQ
kafka-console-consumer.sh --bootstrap-server kafka:9092 \
  --topic events.user.dlq --from-beginning | \
kafka-console-producer.sh --bootstrap-server kafka:9092 \
  --topic events.user
```

### Option E: Reset Consumer Offset

**Warning:** May cause duplicate processing

```bash
# Reset to latest (skip backlog)
kafka-consumer-groups.sh --bootstrap-server kafka:9092 \
  --group python-api-base --topic events.user \
  --reset-offsets --to-latest --execute

# Or reset to specific time
kafka-consumer-groups.sh --bootstrap-server kafka:9092 \
  --group python-api-base --topic events.user \
  --reset-offsets --to-datetime 2024-01-01T00:00:00.000 --execute
```

## Verification

```bash
# Check lag reduced
kafka-consumer-groups.sh --bootstrap-server kafka:9092 \
  --describe --group python-api-base

# Should show lag decreasing
```

## Escalation

- **Level 1:** On-call engineer (15 min)
- **Level 2:** Platform team lead (30 min)
- **Level 3:** Engineering manager (1 hour)

## Post-Incident

- [ ] Analyze root cause
- [ ] Update consumer capacity
- [ ] Add lag alerts
- [ ] Review partition strategy
