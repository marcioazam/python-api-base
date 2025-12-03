# PostgreSQL Integration

## Overview

PostgreSQL é o banco de dados principal, acessado via SQLAlchemy 2.0 com suporte assíncrono.

## Connection Configuration

```python
# core/config/database.py
class DatabaseSettings(BaseSettings):
    url: str = "postgresql+asyncpg://localhost/mydb"
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    echo: bool = False
```

## Environment Variables

```bash
DATABASE__URL=postgresql+asyncpg://user:password@localhost:5432/mydb
DATABASE__POOL_SIZE=10
DATABASE__MAX_OVERFLOW=20
DATABASE__POOL_TIMEOUT=30
DATABASE__ECHO=false
```

## Connection Pooling

```python
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    settings.database.url,
    pool_size=settings.database.pool_size,      # Connections to keep open
    max_overflow=settings.database.max_overflow, # Extra connections allowed
    pool_timeout=settings.database.pool_timeout, # Wait time for connection
    pool_pre_ping=True,                          # Check connection health
    pool_recycle=3600,                           # Recycle connections after 1h
)
```

## Migrations (Alembic)

```bash
# Create migration
alembic revision --autogenerate -m "Add users table"

# Apply all migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View history
alembic history

# View current version
alembic current
```

### Migration Example

```python
# alembic/versions/001_add_users.py
def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.String(26), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('ix_users_email', 'users', ['email'])

def downgrade():
    op.drop_index('ix_users_email')
    op.drop_table('users')
```

## Query Optimization

### Indexes

```python
class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_created_at", "created_at"),
        Index("ix_users_active", "is_active", postgresql_where=text("is_active = true")),
    )
```

### Eager Loading

```python
# Avoid N+1 queries
query = select(Order).options(
    selectinload(Order.items),
    joinedload(Order.customer),
)
```

### Pagination

```python
async def get_paginated(skip: int, limit: int) -> list[User]:
    result = await session.execute(
        select(User)
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())
```

## Transactions

```python
async with session.begin():
    # All operations in this block are in a transaction
    await session.execute(...)
    await session.execute(...)
    # Commit happens automatically on exit
    # Rollback happens on exception
```

## Monitoring

```sql
-- Active connections
SELECT count(*) FROM pg_stat_activity WHERE datname = 'mydb';

-- Slow queries
SELECT query, calls, mean_time, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Table sizes
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

## Best Practices

1. **Use connection pooling** - Configure appropriate pool size
2. **Create indexes** - For frequently queried columns
3. **Use migrations** - Never modify schema manually
4. **Monitor slow queries** - Enable pg_stat_statements
5. **Use transactions** - For data consistency
