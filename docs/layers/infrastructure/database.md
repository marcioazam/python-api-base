# Database Infrastructure

## Overview

O sistema utiliza SQLAlchemy 2.0 com suporte assíncrono para acesso ao PostgreSQL.

## Session Management

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

engine = create_async_engine(
    settings.database.url,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    pool_timeout=settings.database.pool_timeout,
    echo=settings.database.echo,
)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

## Repository Implementation

```python
class SQLAlchemyRepository[T: SQLModel, ID](AsyncRepository[T, ID]):
    def __init__(self, session: AsyncSession, model: type[T]):
        self._session = session
        self._model = model
    
    async def get(self, id: ID) -> T | None:
        return await self._session.get(self._model, id)
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        result = await self._session.execute(
            select(self._model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())
    
    async def create(self, entity: T) -> T:
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity
    
    async def update(self, entity: T) -> T:
        merged = await self._session.merge(entity)
        await self._session.flush()
        return merged
    
    async def delete(self, id: ID) -> bool:
        entity = await self.get(id)
        if entity:
            await self._session.delete(entity)
            return True
        return False
```

## Unit of Work

```python
class UnitOfWork:
    def __init__(self, session_factory: async_sessionmaker):
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
    
    async def __aenter__(self) -> "UnitOfWork":
        self._session = self._session_factory()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        await self._session.close()
    
    async def commit(self) -> None:
        await self._session.commit()
    
    async def rollback(self) -> None:
        await self._session.rollback()
    
    @property
    def session(self) -> AsyncSession:
        return self._session
```

## Query Builder

```python
class QueryBuilder[T]:
    def __init__(self, model: type[T]):
        self._model = model
        self._query = select(model)
    
    def where(self, *conditions) -> "QueryBuilder[T]":
        self._query = self._query.where(*conditions)
        return self
    
    def order_by(self, *columns) -> "QueryBuilder[T]":
        self._query = self._query.order_by(*columns)
        return self
    
    def limit(self, n: int) -> "QueryBuilder[T]":
        self._query = self._query.limit(n)
        return self
    
    def offset(self, n: int) -> "QueryBuilder[T]":
        self._query = self._query.offset(n)
        return self
    
    async def execute(self, session: AsyncSession) -> list[T]:
        result = await session.execute(self._query)
        return list(result.scalars().all())
    
    async def first(self, session: AsyncSession) -> T | None:
        result = await session.execute(self._query.limit(1))
        return result.scalar_one_or_none()
```

## Migrations (Alembic)

```bash
# Create migration
alembic revision --autogenerate -m "Add users table"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Best Practices

1. **Use async sessions** - For non-blocking I/O
2. **Commit at boundaries** - In use cases, not repositories
3. **Use Unit of Work** - For transaction management
4. **Index frequently queried columns** - For performance
5. **Use connection pooling** - Configure pool_size appropriately
