"""ScyllaDB client wrapper.

**Feature: observability-infrastructure**
**Requirement: R4 - Generic ScyllaDB Repository**
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Self

from infrastructure.scylladb.config import ScyllaDBConfig

if TYPE_CHECKING:
    from cassandra.cluster import Cluster, Session

logger = logging.getLogger(__name__)


class ScyllaDBClient:
    """Async-compatible ScyllaDB client.

    Wraps cassandra-driver with async execution support.

    **Feature: observability-infrastructure**
    **Requirement: R4.1 - Client Wrapper**

    Example:
        >>> config = ScyllaDBConfig(hosts=["localhost"], keyspace="my_keyspace")
        >>> async with ScyllaDBClient(config) as client:
        ...     rows = await client.execute("SELECT * FROM users")
    """

    def __init__(
        self,
        config: ScyllaDBConfig,
        executor: ThreadPoolExecutor | None = None,
    ) -> None:
        """Initialize client.

        Args:
            config: ScyllaDB configuration
            executor: Optional thread pool for async execution
        """
        self._config = config
        self._executor = executor or ThreadPoolExecutor(max_workers=10)
        self._owns_executor = executor is None
        self._cluster: Cluster | None = None
        self._session: Session | None = None

    async def connect(self) -> Self:
        """Connect to ScyllaDB.

        Returns:
            Self for chaining
        """
        if self._session:
            return self

        from cassandra.cluster import Cluster

        loop = asyncio.get_event_loop()

        # Create cluster and session in thread pool
        def _connect() -> tuple[Cluster, Any]:
            cluster = Cluster(**self._config.to_cluster_kwargs())
            session = cluster.connect(self._config.keyspace)
            session.default_timeout = self._config.request_timeout
            session.default_consistency_level = self._config.get_consistency_level()
            return cluster, session

        self._cluster, self._session = await loop.run_in_executor(
            self._executor, _connect
        )

        logger.info(
            "Connected to ScyllaDB",
            extra={
                "hosts": self._config.hosts,
                "keyspace": self._config.keyspace,
            },
        )

        return self

    async def close(self) -> None:
        """Close the connection."""
        if self._cluster:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self._executor, self._cluster.shutdown)
            self._cluster = None
            self._session = None

            if self._owns_executor:
                self._executor.shutdown(wait=False)

            logger.info("Disconnected from ScyllaDB")

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    @property
    def session(self) -> Any:
        """Get the raw session.

        Raises:
            RuntimeError: If not connected
        """
        if not self._session:
            raise RuntimeError("Not connected")
        return self._session

    async def execute(
        self,
        query: str,
        parameters: tuple | dict | None = None,
        timeout: float | None = None,
    ) -> list[Any]:
        """Execute a CQL query.

        Args:
            query: CQL query string
            parameters: Query parameters
            timeout: Query timeout

        Returns:
            List of result rows
        """
        if not self._session:
            raise RuntimeError("Not connected")

        loop = asyncio.get_event_loop()

        def _execute() -> list[Any]:
            result = self._session.execute(
                query,
                parameters,
                timeout=timeout or self._config.request_timeout,
            )
            return list(result)

        return await loop.run_in_executor(self._executor, _execute)

    async def execute_async(
        self,
        query: str,
        parameters: tuple | dict | None = None,
    ) -> Any:
        """Execute query using driver's async.

        Uses cassandra-driver's built-in async execution.

        Args:
            query: CQL query string
            parameters: Query parameters

        Returns:
            ResponseFuture that can be awaited
        """
        if not self._session:
            raise RuntimeError("Not connected")

        future = self._session.execute_async(query, parameters)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            future.result,
        )

    async def prepare(self, query: str) -> Any:
        """Prepare a CQL statement.

        Args:
            query: CQL query to prepare

        Returns:
            PreparedStatement
        """
        if not self._session:
            raise RuntimeError("Not connected")

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._session.prepare,
            query,
        )

    async def execute_batch(
        self,
        statements: list[tuple[str, tuple | dict | None]],
        batch_type: str = "LOGGED",
    ) -> None:
        """Execute a batch of statements.

        Args:
            statements: List of (query, parameters) tuples
            batch_type: LOGGED, UNLOGGED, or COUNTER
        """
        if not self._session:
            raise RuntimeError("Not connected")

        from cassandra.query import BatchStatement, BatchType

        loop = asyncio.get_event_loop()

        def _batch() -> None:
            bt = getattr(BatchType, batch_type)
            batch = BatchStatement(batch_type=bt)

            for query, params in statements:
                batch.add(query, params)

            self._session.execute(batch)

        await loop.run_in_executor(self._executor, _batch)

    async def create_keyspace(
        self,
        keyspace: str,
        replication: dict[str, Any] | None = None,
        if_not_exists: bool = True,
    ) -> None:
        """Create a keyspace.

        Args:
            keyspace: Keyspace name
            replication: Replication strategy
            if_not_exists: Add IF NOT EXISTS clause
        """
        replication = replication or {
            "class": "SimpleStrategy",
            "replication_factor": 1,
        }

        replication_str = ", ".join(
            f"'{k}': '{v}'" if isinstance(v, str) else f"'{k}': {v}"
            for k, v in replication.items()
        )

        query = f"CREATE KEYSPACE {'IF NOT EXISTS ' if if_not_exists else ''}{keyspace} "
        query += f"WITH replication = {{{replication_str}}}"

        await self.execute(query)
        logger.info(f"Created keyspace: {keyspace}")

    async def create_table(
        self,
        table: str,
        columns: dict[str, str],
        primary_key: str | list[str],
        if_not_exists: bool = True,
        **options: Any,
    ) -> None:
        """Create a table.

        Args:
            table: Table name
            columns: Column definitions {name: type}
            primary_key: Primary key column(s)
            if_not_exists: Add IF NOT EXISTS clause
            **options: Table options
        """
        cols = ", ".join(f"{name} {ctype}" for name, ctype in columns.items())

        if isinstance(primary_key, list):
            pk = f"({', '.join(primary_key)})"
        else:
            pk = primary_key

        query = f"CREATE TABLE {'IF NOT EXISTS ' if if_not_exists else ''}{table} "
        query += f"({cols}, PRIMARY KEY ({pk}))"

        if options:
            opts = " AND ".join(f"{k} = {v}" for k, v in options.items())
            query += f" WITH {opts}"

        await self.execute(query)
        logger.info(f"Created table: {table}")

    async def drop_table(self, table: str, if_exists: bool = True) -> None:
        """Drop a table.

        Args:
            table: Table name
            if_exists: Add IF EXISTS clause
        """
        query = f"DROP TABLE {'IF EXISTS ' if if_exists else ''}{table}"
        await self.execute(query)
        logger.info(f"Dropped table: {table}")

    async def truncate_table(self, table: str) -> None:
        """Truncate a table.

        Args:
            table: Table name
        """
        await self.execute(f"TRUNCATE TABLE {table}")
        logger.info(f"Truncated table: {table}")
