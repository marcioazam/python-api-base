# Cache Failures

## Severity
Medium

## Symptoms

- Increased database load
- Higher response latency
- Logs showing `CacheError` or `ConnectionError` for Redis
- Health check `/health/ready` failing for Redis
- Cache hit rate dropping to 0%

## Impact

- Degraded performance (fallback to database)
- Increased database load
- Higher latency for cached operations
- Potential cascade failures under high load

## Prerequisites

- Access to application logs
- Access to Redis server
- Redis CLI access
- kubectl access (if running on Kubernetes)

## Diagnosis Steps

### 1. Check Application Logs

```bash
# Look for cache-related errors
kubectl logs -l app=python-api-base --tail=100 | grep -i "redis\|cache"
```

### 2. Check Redis Connectivity

```bash
# From application pod
kubectl exec -it <pod-name> -- redis-cli -h <redis-host> ping
```

### 3. Check Redis Server Status

```bash
# Redis info
redis-cli INFO

# Memory usage
redis-cli INFO memory

# Connected clients
redis-cli CLIENT LIST | wc -l

# Check if Redis is responding
redis-cli DEBUG SLEEP 0
```

### 4. Check Cache Metrics

```bash
curl http://localhost:8000/metrics | grep cache
```

Look for:
- `cache_hits_total`
- `cache_misses_total`
- `cache_errors_total`

### 5. Check Redis Memory

```bash
redis-cli INFO memory | grep used_memory_human
redis-cli INFO memory | grep maxmemory
```

## Resolution Steps

### Scenario 1: Redis Server Unreachable

**Symptoms**: `Connection refused` or `timeout`

**Resolution**:

1. Check Redis server status:
```bash
systemctl status redis
```

2. Restart Redis if necessary:
```bash
systemctl restart redis
```

3. Check Redis logs:
```bash
tail -f /var/log/redis/redis-server.log
```

4. Verify network connectivity:
```bash
nc -zv <redis-host> 6379
```

### Scenario 2: Redis Out of Memory

**Symptoms**: `OOM command not allowed` or `maxmemory reached`

**Resolution**:

1. Check memory usage:
```bash
redis-cli INFO memory
```

2. Clear expired keys:
```bash
redis-cli DEBUG SLEEP 0  # Triggers lazy expiration
```

3. Manually clear cache if necessary:
```bash
redis-cli FLUSHDB  # Current database only
```

4. Increase maxmemory (if possible):
```bash
redis-cli CONFIG SET maxmemory 2gb
```

5. Review eviction policy:
```bash
redis-cli CONFIG GET maxmemory-policy
# Recommended: allkeys-lru
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### Scenario 3: Too Many Connections

**Symptoms**: `max number of clients reached`

**Resolution**:

1. Check current connections:
```bash
redis-cli CLIENT LIST | wc -l
redis-cli INFO clients
```

2. Kill idle connections:
```bash
redis-cli CLIENT KILL TYPE normal
```

3. Increase max clients:
```bash
redis-cli CONFIG SET maxclients 10000
```

4. Review application connection pooling

### Scenario 4: High Latency

**Symptoms**: Cache operations taking > 100ms

**Resolution**:

1. Check slow log:
```bash
redis-cli SLOWLOG GET 10
```

2. Check for blocking operations:
```bash
redis-cli INFO commandstats
```

3. Check network latency:
```bash
redis-cli --latency
```

4. Consider using Redis Cluster for scaling

### Scenario 5: Application Fallback Active

**Symptoms**: Cache errors but application still working

**Resolution**:

1. Verify fallback is working:
```bash
# Check if requests are succeeding
curl http://localhost:8000/api/v1/users
```

2. Monitor database load:
```bash
# Check database connections
psql -c "SELECT count(*) FROM pg_stat_activity"
```

3. Fix Redis issue (see above scenarios)

4. Cache will auto-recover when Redis is available

## Verification

1. Check Redis connectivity:
```bash
redis-cli PING
```

2. Check health endpoint:
```bash
curl http://localhost:8000/health/ready
```

3. Verify cache operations:
```bash
# Set a test key
redis-cli SET test:key "value" EX 60
redis-cli GET test:key
```

4. Monitor cache hit rate:
```bash
curl http://localhost:8000/metrics | grep cache_hit
```

## Prevention

1. **Memory Management**:
   - Set appropriate maxmemory
   - Use TTL on all keys
   - Configure eviction policy (allkeys-lru recommended)

2. **Connection Pooling**:
   - Configure appropriate pool size
   - Set connection timeouts

3. **Monitoring**:
   - Alert on memory usage > 80%
   - Alert on connection count > 80% of max
   - Alert on cache error rate > 1%

4. **High Availability**:
   - Use Redis Sentinel or Cluster
   - Configure automatic failover

5. **Graceful Degradation**:
   - Ensure application works without cache
   - Implement circuit breaker for cache operations

## Related

- [Configuration Guide](../configuration.md)
- [ADR-008: Cache Strategy](../adr/ADR-008-cache-strategy.md)
- [Monitoring Guide](../monitoring.md)
