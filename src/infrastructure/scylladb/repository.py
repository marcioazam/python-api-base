"""Generic ScyllaDB repository with PEP 695 generics.

**Feature: observability-infrastructure**
**Requirement: R4 - Generic ScyllaDB Repository**
"""

from __future__ import annotations

import logging
from datetime import datetime, UTC
from typing import Any, Generic, TypeVar
from uuid import UUID

from infrastructure.scylladb.client import ScyllaDBClient
from infrastructure.scylladb.entity import ScyllaDBEntity

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=ScyllaDBEntity)


class ScyllaDBRepository(Generic[T]):
    """Generic repository for ScyllaDB entities.

    Provides type-safe CRUD operations using PEP 695 generics pattern.

    **Feature: observability-infrastructure**
    **Requirement: R4.3 - Generic Repository**

    Example:
        >>> class User(ScyllaDBEntity):
        ...     __table_name__ = "users"
        ...     name: str
        ...     email: str
        >>> repo = ScyllaDBRepository[User](client, User)
        >>> user = await repo.create(User(name="John", email="john@ex.com"))
        >>> found = await repo.get(user.id)
    """

    def __init__(
        self,
        client: ScyllaDBClient,
        entity_class: type[T],
    ) -> None:
        """Initialize repository.

        Args:
            client: ScyllaDB client
            entity_class: Entity class for type conversion
        """
        self._client = client
        self._entity_class = entity_class
        self._prepared_statements: dict[str, Any] = {}

    @property
    def table_name(self) -> str:
        """Get table name."""
        return self._entity_class.table_name()

    # CRUD Operations

    async def create(self, entity: T) -> T:
        """Create a new entity.

        Args:
            entity: Entity to create

        Returns:
            Created entity
        """
        entity.updated_at = datetime.now(UTC)
        data = entity.to_dict()
        columns = list(data.keys())
        placeholders = ", ".join(["%s"] * len(columns))
        cols_str = ", ".join(columns)

        query = f"INSERT INTO {self.table_name} ({cols_str}) VALUES ({placeholders})"
        await self._client.execute(query, tuple(data.values()))

        logger.debug(
            f"Created entity in {self.table_name}", extra={"id": str(entity.id)}
        )
        return entity

    async def get(self, id: UUID) -> T | None:
        """Get entity by ID.

        Args:
            id: Entity ID

        Returns:
            Entity or None if not found
        """
        pk_cols = self._entity_class.primary_key()
        where = " AND ".join(f"{col} = %s" for col in pk_cols)

        query = f"SELECT * FROM {self.table_name} WHERE {where}"
        rows = await self._client.execute(query, (id,))

        if not rows:
            return None

        return self._entity_class.from_row(rows[0])

    async def get_by_keys(self, **key_values: Any) -> T | None:
        """Get entity by composite key values.

        Args:
            **key_values: Key column values

        Returns:
            Entity or None if not found
        """
        where_parts = []
        values = []

        for col, val in key_values.items():
            where_parts.append(f"{col} = %s")
            values.append(val)

        where = " AND ".join(where_parts)
        query = f"SELECT * FROM {self.table_name} WHERE {where}"

        rows = await self._client.execute(query, tuple(values))

        if not rows:
            return None

        return self._entity_class.from_row(rows[0])

    async def update(self, entity: T) -> T:
        """Update an entity.

        Args:
            entity: Entity with updated values

        Returns:
            Updated entity
        """
        entity.updated_at = datetime.now(UTC)
        data = entity.to_dict()

        # Separate PK from other columns
        pk_cols = set(
            self._entity_class.primary_key() + self._entity_class.clustering_key()
        )
        update_cols = {k: v for k, v in data.items() if k not in pk_cols}
        pk_values = {k: v for k, v in data.items() if k in pk_cols}

        # Build SET clause
        set_parts = [f"{col} = %s" for col in update_cols.keys()]
        set_clause = ", ".join(set_parts)

        # Build WHERE clause
        where_parts = [f"{col} = %s" for col in pk_cols]
        where_clause = " AND ".join(where_parts)

        query = f"UPDATE {self.table_name} SET {set_clause} WHERE {where_clause}"
        values = list(update_cols.values()) + [pk_values[col] for col in pk_cols]

        await self._client.execute(query, tuple(values))

        logger.debug(
            f"Updated entity in {self.table_name}", extra={"id": str(entity.id)}
        )
        return entity

    async def delete(self, id: UUID) -> bool:
        """Delete an entity.

        Args:
            id: Entity ID

        Returns:
            True if deleted
        """
        pk_cols = self._entity_class.primary_key()
        where = " AND ".join(f"{col} = %s" for col in pk_cols)

        query = f"DELETE FROM {self.table_name} WHERE {where}"
        await self._client.execute(query, (id,))

        logger.debug(f"Deleted entity from {self.table_name}", extra={"id": str(id)})
        return True

    async def delete_by_keys(self, **key_values: Any) -> bool:
        """Delete entity by composite key.

        Args:
            **key_values: Key column values

        Returns:
            True if deleted
        """
        where_parts = []
        values = []

        for col, val in key_values.items():
            where_parts.append(f"{col} = %s")
            values.append(val)

        where = " AND ".join(where_parts)
        query = f"DELETE FROM {self.table_name} WHERE {where}"

        await self._client.execute(query, tuple(values))
        return True

    async def exists(self, id: UUID) -> bool:
        """Check if entity exists.

        Args:
            id: Entity ID

        Returns:
            True if exists
        """
        entity = await self.get(id)
        return entity is not None

    # Query Operations

    async def find_all(self, limit: int = 100) -> list[T]:
        """Find all entities.

        Args:
            limit: Maximum number to return

        Returns:
            List of entities
        """
        query = f"SELECT * FROM {self.table_name} LIMIT %s"
        rows = await self._client.execute(query, (limit,))

        return [self._entity_class.from_row(row) for row in rows]

    async def find_by(
        self,
        column: str,
        value: Any,
        limit: int = 100,
    ) -> list[T]:
        """Find entities by column value.

        Note: Column must be part of primary key or have an index.

        Args:
            column: Column name
            value: Column value
            limit: Maximum results

        Returns:
            List of matching entities
        """
        query = f"SELECT * FROM {self.table_name} WHERE {column} = %s LIMIT %s"
        rows = await self._client.execute(query, (value, limit))

        return [self._entity_class.from_row(row) for row in rows]

    async def find_by_query(
        self,
        where: str,
        values: tuple | None = None,
        limit: int = 100,
        allow_filtering: bool = False,
    ) -> list[T]:
        """Find entities by custom query.

        Args:
            where: WHERE clause (without WHERE keyword)
            values: Parameter values
            limit: Maximum results
            allow_filtering: Add ALLOW FILTERING clause

        Returns:
            List of matching entities
        """
        query = f"SELECT * FROM {self.table_name} WHERE {where} LIMIT %s"
        if allow_filtering:
            query += " ALLOW FILTERING"

        params = (*(values or ()), limit)
        rows = await self._client.execute(query, params)

        return [self._entity_class.from_row(row) for row in rows]

    async def count(self) -> int:
        """Count all entities.

        Returns:
            Entity count
        """
        query = f"SELECT COUNT(*) FROM {self.table_name}"
        rows = await self._client.execute(query)

        return rows[0].count if rows else 0

    # Bulk Operations

    async def bulk_create(self, entities: list[T]) -> list[T]:
        """Bulk create entities.

        Args:
            entities: Entities to create

        Returns:
            Created entities
        """
        if not entities:
            return []

        statements = []
        for entity in entities:
            entity.updated_at = datetime.now(UTC)
            data = entity.to_dict()
            columns = list(data.keys())
            placeholders = ", ".join(["%s"] * len(columns))
            cols_str = ", ".join(columns)

            query = (
                f"INSERT INTO {self.table_name} ({cols_str}) VALUES ({placeholders})"
            )
            statements.append((query, tuple(data.values())))

        await self._client.execute_batch(statements, batch_type="UNLOGGED")

        logger.info(f"Bulk created {len(entities)} entities in {self.table_name}")
        return entities

    async def bulk_delete(self, ids: list[UUID]) -> int:
        """Bulk delete entities.

        Args:
            ids: Entity IDs to delete

        Returns:
            Number deleted
        """
        if not ids:
            return 0

        pk_cols = self._entity_class.primary_key()
        where = " AND ".join(f"{col} = %s" for col in pk_cols)
        query = f"DELETE FROM {self.table_name} WHERE {where}"

        statements = [(query, (id,)) for id in ids]
        await self._client.execute_batch(statements, batch_type="UNLOGGED")

        logger.info(f"Bulk deleted {len(ids)} entities from {self.table_name}")
        return len(ids)

    # Table Management

    async def ensure_table(self) -> bool:
        """Ensure table exists.

        Returns:
            True if created, False if existed
        """
        columns = self._entity_class.columns()
        pk = self._entity_class.primary_key()
        ck = self._entity_class.clustering_key()

        # Build primary key
        if ck:
            pk_def = f"({', '.join(pk)}), {', '.join(ck)}"
        else:
            pk_def = ", ".join(pk)

        await self._client.create_table(
            table=self.table_name,
            columns=columns,
            primary_key=pk_def,
            if_not_exists=True,
        )

        return True

    async def truncate(self) -> None:
        """Truncate the table."""
        await self._client.truncate_table(self.table_name)
