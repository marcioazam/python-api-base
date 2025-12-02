# Database Connection Issues

## Severity
High

## Symptoms

- API returning 503 Service Unavailable
- Logs showing `ConnectionPoolError` or `OperationalError`
- Health check `/health/ready` failing for database
- Increased latency on database operations
- Error messages containing "connection refused" or "timeout"

## Impact

- Users unable to perform operations requiring database access
- Data not being persisted
- Authentication failures (if using database for user storage)

## Prerequisites

- Access to application logs
- Access to database server
- Database credentials
- kubectl access (if running on Kubernetes)

## Diagnosis Steps

### 1. Check Application Logs

```bash
# Kubernetes
kubectl logs -l app=python-api-base --tail=100 | grep -i "database\|connection\|pool"

# Docker
docker logs python-api-base 2>&1 | grep -i "database\|connection\|pool"
```

Look for:
- `ConnectionPoolError`: Pool exhausted
- `OperationalError`: Connection refused
- `TimeoutError`: Connection timeout

### 2. Check Database Connectivity

```bash
# Test connection from application pod
kubectl exec -it <pod-name> -- python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
engine = create_async_engine('$DATABASE_URL')
async def test():
    async with engine.connect() as conn:
        result = await conn.execute('SELECT 1')
        print('Connection OK')
asyncio.run(test())
"
```

### 3. Check Database Server Status

```bash
# PostgreSQL
psql -h <host> -U <user> -d <database> -c "SELECT 1"

# Check connections
psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname = '<database>'"

# Check max connections
psql -c "SHOW max_connections"
```

### 4. Check Connection Pool Status

```bash
# Application metrics endpoint
curl http://localhost:8000/metrics | grep db_pool
```

### 5. Check Network Connectivity

```bash
# From application pod
kubectl exec -it <pod-name> -- nc -zv <db-host> 5432
```

## Resolution Steps

### Scenario 1: Connection Pool Exhausted

**Symptoms**: `ConnectionPoolError: Pool limit reached`

**Resolution**:

1. Increase pool size temporarily:
```bash
kubectl set env deployment/python-api-base DB_POOL_SIZE=20
```

2. Identify long-running queries:
```sql
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;
```

3. Kill long-running queries if necessary:
```sql
SELECT pg_terminate_backend(<pid>);
```

4. Review application code for connection leaks

### Scenario 2: Database Server Unreachable

**Symptoms**: `Connection refused` or `timeout`

**Resolution**:

1. Check database server status:
```bash
systemctl status postgresql
```

2. Check firewall rules:
```bash
# Check if port is open
sudo ufw status | grep 5432
```

3. Restart database if necessary:
```bash
systemctl restart postgresql
```

4. Check DNS resolution:
```bash
nslookup <db-host>
```

### Scenario 3: Authentication Failure

**Symptoms**: `authentication failed for user`

**Resolution**:

1. Verify credentials in environment:
```bash
kubectl get secret db-credentials -o jsonpath='{.data.password}' | base64 -d
```

2. Test credentials directly:
```bash
PGPASSWORD=<password> psql -h <host> -U <user> -d <database>
```

3. Check pg_hba.conf for allowed connections

### Scenario 4: Too Many Connections

**Symptoms**: `too many connections for role`

**Resolution**:

1. Check current connections:
```sql
SELECT usename, count(*) FROM pg_stat_activity GROUP BY usename;
```

2. Terminate idle connections:
```sql
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '<database>'
AND state = 'idle'
AND query_start < now() - interval '10 minutes';
```

3. Increase max_connections (requires restart):
```bash
# postgresql.conf
max_connections = 200
```

## Verification

1. Check health endpoint:
```bash
curl http://localhost:8000/health/ready
```

2. Verify database operations:
```bash
curl http://localhost:8000/api/v1/users
```

3. Monitor logs for errors:
```bash
kubectl logs -f -l app=python-api-base | grep -i error
```

## Prevention

1. **Connection Pool Sizing**: Set appropriate pool size based on load
   ```
   DB_POOL_SIZE = (2 * num_cores) + effective_spindle_count
   ```

2. **Connection Timeouts**: Configure appropriate timeouts
   ```
   DB_POOL_TIMEOUT=30
   DB_CONNECT_TIMEOUT=10
   ```

3. **Health Checks**: Ensure health checks include database connectivity

4. **Monitoring**: Set up alerts for:
   - Connection pool utilization > 80%
   - Database connection errors
   - Query latency > threshold

5. **Connection Recycling**: Configure connection recycling
   ```
   DB_POOL_RECYCLE=3600
   ```

## Related

- [Configuration Guide](../configuration.md)
- [ADR-005: Repository Pattern](../adr/ADR-005-repository-pattern.md)
- [Monitoring Guide](../monitoring.md)
