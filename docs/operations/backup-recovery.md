# Backup and Recovery Guide

## Overview

Este guia documenta procedimentos de backup, recuperação e estratégias de rollback para o Python API Base.

## Backup Strategy

### Database (PostgreSQL)

#### Automated Backups

```yaml
# Kubernetes CronJob for pg_dump
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: postgres:15
              command:
                - /bin/sh
                - -c
                - |
                  pg_dump -h $PGHOST -U $PGUSER -d $PGDATABASE | \
                  gzip > /backups/db-$(date +%Y%m%d-%H%M%S).sql.gz
              env:
                - name: PGPASSWORD
                  valueFrom:
                    secretKeyRef:
                      name: postgres-secret
                      key: password
              volumeMounts:
                - name: backup-storage
                  mountPath: /backups
          volumes:
            - name: backup-storage
              persistentVolumeClaim:
                claimName: backup-pvc
          restartPolicy: OnFailure
```

#### Manual Backup

```bash
# Full database backup
pg_dump -h localhost -U postgres -d python_api_base -F c -f backup.dump

# Schema only
pg_dump -h localhost -U postgres -d python_api_base --schema-only -f schema.sql

# Data only
pg_dump -h localhost -U postgres -d python_api_base --data-only -f data.sql

# Specific tables
pg_dump -h localhost -U postgres -d python_api_base -t users -t items -f tables.dump
```

#### Point-in-Time Recovery (PITR)

```bash
# Enable WAL archiving in postgresql.conf
archive_mode = on
archive_command = 'cp %p /archive/%f'
wal_level = replica

# Restore to specific point
pg_restore --target-time="2025-01-15 10:30:00" -d python_api_base backup.dump
```

### Redis Cache

```bash
# Manual snapshot
redis-cli BGSAVE

# Automated RDB snapshots (redis.conf)
save 900 1      # After 900 sec if at least 1 key changed
save 300 10     # After 300 sec if at least 10 keys changed
save 60 10000   # After 60 sec if at least 10000 keys changed

# AOF persistence
appendonly yes
appendfsync everysec
```

### MinIO/S3 Storage

```bash
# Sync to backup bucket
mc mirror minio/primary-bucket minio/backup-bucket

# Cross-region replication
mc replicate add minio/primary-bucket \
  --remote-bucket "https://backup-region/backup-bucket" \
  --replicate "delete,delete-marker,existing-objects"
```

### Application Configuration

```bash
# Backup Kubernetes secrets
kubectl get secrets -o yaml > secrets-backup.yaml

# Backup ConfigMaps
kubectl get configmaps -o yaml > configmaps-backup.yaml

# Backup Helm values
helm get values python-api-base > values-backup.yaml
```

## Recovery Procedures

### Database Recovery

#### Full Restore

```bash
# Stop application
kubectl scale deployment python-api-base --replicas=0

# Restore database
pg_restore -h localhost -U postgres -d python_api_base -c backup.dump

# Verify data integrity
psql -h localhost -U postgres -d python_api_base -c "SELECT count(*) FROM users;"

# Restart application
kubectl scale deployment python-api-base --replicas=3
```

#### Partial Restore (Specific Tables)

```bash
# Restore specific table
pg_restore -h localhost -U postgres -d python_api_base -t users backup.dump

# Restore with data only (preserve schema)
pg_restore -h localhost -U postgres -d python_api_base --data-only -t users backup.dump
```

### Redis Recovery

```bash
# Stop Redis
redis-cli SHUTDOWN NOSAVE

# Replace dump.rdb with backup
cp /backups/dump.rdb /var/lib/redis/dump.rdb

# Start Redis
redis-server /etc/redis/redis.conf
```

### Application Rollback

#### Kubernetes Rollback

```bash
# View rollout history
kubectl rollout history deployment/python-api-base

# Rollback to previous version
kubectl rollout undo deployment/python-api-base

# Rollback to specific revision
kubectl rollout undo deployment/python-api-base --to-revision=3

# Verify rollback
kubectl rollout status deployment/python-api-base
```

#### Helm Rollback

```bash
# View release history
helm history python-api-base

# Rollback to previous release
helm rollback python-api-base

# Rollback to specific revision
helm rollback python-api-base 3
```

### Database Migration Rollback

```bash
# View migration history
alembic history

# Rollback last migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade abc123

# Rollback all migrations
alembic downgrade base
```

## Disaster Recovery

### Recovery Time Objectives (RTO)

| Component | RTO | RPO | Strategy |
|-----------|-----|-----|----------|
| API | 15 min | 0 | Multi-replica deployment |
| Database | 30 min | 1 hour | Daily backups + WAL |
| Cache | 5 min | N/A | Rebuild from DB |
| Storage | 1 hour | 24 hours | Cross-region replication |

### Recovery Point Objectives (RPO)

| Data Type | RPO | Backup Frequency |
|-----------|-----|------------------|
| User Data | 1 hour | Hourly incremental |
| Transactions | 5 min | WAL streaming |
| Logs | 24 hours | Daily archive |
| Config | 0 | GitOps |

### Disaster Recovery Runbook

1. **Assess Impact**
   ```bash
   # Check cluster status
   kubectl get nodes
   kubectl get pods -A
   ```

2. **Activate DR Site** (if applicable)
   ```bash
   # Update DNS to DR site
   # Scale up DR deployment
   kubectl scale deployment python-api-base --replicas=5 -n dr
   ```

3. **Restore Data**
   ```bash
   # Restore from latest backup
   ./scripts/restore-database.sh latest
   ```

4. **Verify Services**
   ```bash
   # Health checks
   curl https://api.example.com/health/ready
   ```

5. **Notify Stakeholders**
   - Update status page
   - Send incident notification

## Backup Retention Policy

| Backup Type | Retention | Storage |
|-------------|-----------|---------|
| Hourly | 24 hours | Local |
| Daily | 7 days | S3 |
| Weekly | 4 weeks | S3 |
| Monthly | 12 months | S3 Glacier |
| Yearly | 7 years | S3 Glacier Deep Archive |

## Verification and Testing

### Backup Verification

```bash
# Verify backup integrity
pg_restore --list backup.dump

# Test restore to temporary database
createdb test_restore
pg_restore -d test_restore backup.dump
psql -d test_restore -c "SELECT count(*) FROM users;"
dropdb test_restore
```

### DR Testing Schedule

| Test Type | Frequency | Duration |
|-----------|-----------|----------|
| Backup Restore | Weekly | 1 hour |
| Failover Test | Monthly | 2 hours |
| Full DR Test | Quarterly | 4 hours |

## Monitoring Backups

### Prometheus Alerts

```yaml
groups:
  - name: backup
    rules:
      - alert: BackupFailed
        expr: |
          backup_last_success_timestamp < (time() - 86400)
        for: 1h
        labels:
          severity: critical
        annotations:
          summary: Database backup failed
          
      - alert: BackupSizeAnomaly
        expr: |
          abs(backup_size_bytes - backup_size_bytes offset 1d) / backup_size_bytes > 0.5
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: Backup size changed significantly
```

## Related Documentation

- [Deployment Guide](deployment.md)
- [Database Infrastructure](../infrastructure/postgresql.md)
- [Runbooks](runbooks/README.md)
