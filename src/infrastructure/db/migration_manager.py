"""Database Migration Manager with rollback support."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Protocol
from collections.abc import Callable, Awaitable
import hashlib


class MigrationStatus(Enum):
    """Migration execution status."""
    PENDING = "pending"
    APPLIED = "applied"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class Migration:
    """Migration definition."""
    version: str
    name: str
    up_sql: str
    down_sql: str
    checksum: str = ""
    applied_at: datetime | None = None
    status: MigrationStatus = MigrationStatus.PENDING

    def __post_init__(self) -> None:
        if not self.checksum:
            self.checksum = self._compute_checksum()

    def _compute_checksum(self) -> str:
        content = f"{self.up_sql}{self.down_sql}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class MigrationResult:
    """Result of migration execution."""
    migration: Migration
    success: bool
    error: str | None = None
    duration_ms: float = 0.0


class MigrationBackend(Protocol):
    """Protocol for migration storage backend."""

    async def get_applied_migrations(self) -> list[Migration]: ...
    async def mark_applied(self, migration: Migration) -> None: ...
    async def mark_rolled_back(self, migration: Migration) -> None: ...
    async def execute_sql(self, sql: str) -> None: ...
    async def begin_transaction(self) -> None: ...
    async def commit_transaction(self) -> None: ...
    async def rollback_transaction(self) -> None: ...


@dataclass
class SchemaDiff:
    """Schema difference between two states."""
    added_tables: list[str] = field(default_factory=list)
    removed_tables: list[str] = field(default_factory=list)
    added_columns: dict[str, list[str]] = field(default_factory=dict)
    removed_columns: dict[str, list[str]] = field(default_factory=dict)
    modified_columns: dict[str, list[str]] = field(default_factory=dict)
    added_indexes: list[str] = field(default_factory=list)
    removed_indexes: list[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(
            self.added_tables or self.removed_tables or
            self.added_columns or self.removed_columns or
            self.modified_columns or self.added_indexes or
            self.removed_indexes
        )

    def generate_up_sql(self) -> str:
        """Generate SQL for applying changes."""
        statements: list[str] = []
        for table in self.added_tables:
            statements.append(f"-- CREATE TABLE {table}")
        for table, columns in self.added_columns.items():
            for col in columns:
                statements.append(f"ALTER TABLE {table} ADD COLUMN {col};")
        for idx in self.added_indexes:
            statements.append(f"-- CREATE INDEX {idx}")
        return "\n".join(statements)

    def generate_down_sql(self) -> str:
        """Generate SQL for reverting changes."""
        statements: list[str] = []
        for idx in self.added_indexes:
            statements.append(f"-- DROP INDEX {idx}")
        for table, columns in self.added_columns.items():
            for col in columns:
                col_name = col.split()[0]
                statements.append(f"ALTER TABLE {table} DROP COLUMN {col_name};")
        for table in self.added_tables:
            statements.append(f"DROP TABLE IF EXISTS {table};")
        return "\n".join(statements)


class MigrationManager:
    """Manages database migrations with rollback support."""

    def __init__(self, backend: MigrationBackend) -> None:
        self._backend = backend
        self._migrations: dict[str, Migration] = {}
        self._hooks: dict[str, list[Callable[[Migration], Awaitable[None]]]] = {
            "before_up": [],
            "after_up": [],
            "before_down": [],
            "after_down": [],
        }

    def register(self, migration: Migration) -> None:
        """Register a migration."""
        self._migrations[migration.version] = migration

    def register_hook(
        self,
        event: str,
        callback: Callable[[Migration], Awaitable[None]]
    ) -> None:
        """Register a hook for migration events."""
        if event in self._hooks:
            self._hooks[event].append(callback)

    async def _run_hooks(self, event: str, migration: Migration) -> None:
        for hook in self._hooks.get(event, []):
            await hook(migration)

    def get_pending_migrations(
        self,
        applied: list[Migration]
    ) -> list[Migration]:
        """Get migrations that haven't been applied."""
        applied_versions = {m.version for m in applied}
        pending = [
            m for v, m in sorted(self._migrations.items())
            if v not in applied_versions
        ]
        return pending

    async def migrate(
        self,
        target_version: str | None = None
    ) -> list[MigrationResult]:
        """Apply pending migrations up to target version."""
        results: list[MigrationResult] = []
        applied = await self._backend.get_applied_migrations()
        pending = self.get_pending_migrations(applied)

        for migration in pending:
            if target_version and migration.version > target_version:
                break

            result = await self._apply_migration(migration)
            results.append(result)

            if not result.success:
                break

        return results

    async def _apply_migration(self, migration: Migration) -> MigrationResult:
        """Apply a single migration."""
        import time
        start = time.perf_counter()

        try:
            await self._run_hooks("before_up", migration)
            await self._backend.begin_transaction()

            await self._backend.execute_sql(migration.up_sql)
            migration.applied_at = datetime.now(timezone.utc)
            migration.status = MigrationStatus.APPLIED
            await self._backend.mark_applied(migration)

            await self._backend.commit_transaction()
            await self._run_hooks("after_up", migration)

            duration = (time.perf_counter() - start) * 1000
            return MigrationResult(migration, True, duration_ms=duration)

        except Exception as e:
            await self._backend.rollback_transaction()
            migration.status = MigrationStatus.FAILED
            duration = (time.perf_counter() - start) * 1000
            return MigrationResult(migration, False, str(e), duration)

    async def rollback(
        self,
        steps: int = 1
    ) -> list[MigrationResult]:
        """Rollback the last N migrations."""
        results: list[MigrationResult] = []
        applied = await self._backend.get_applied_migrations()
        applied_sorted = sorted(applied, key=lambda m: m.version, reverse=True)

        for migration in applied_sorted[:steps]:
            if migration.version not in self._migrations:
                continue

            full_migration = self._migrations[migration.version]
            result = await self._rollback_migration(full_migration)
            results.append(result)

            if not result.success:
                break

        return results

    async def _rollback_migration(
        self,
        migration: Migration
    ) -> MigrationResult:
        """Rollback a single migration."""
        import time
        start = time.perf_counter()

        try:
            await self._run_hooks("before_down", migration)
            await self._backend.begin_transaction()

            await self._backend.execute_sql(migration.down_sql)
            migration.status = MigrationStatus.ROLLED_BACK
            await self._backend.mark_rolled_back(migration)

            await self._backend.commit_transaction()
            await self._run_hooks("after_down", migration)

            duration = (time.perf_counter() - start) * 1000
            return MigrationResult(migration, True, duration_ms=duration)

        except Exception as e:
            await self._backend.rollback_transaction()
            duration = (time.perf_counter() - start) * 1000
            return MigrationResult(migration, False, str(e), duration)

    async def get_status(self) -> dict[str, MigrationStatus]:
        """Get status of all migrations."""
        applied = await self._backend.get_applied_migrations()
        applied_map = {m.version: m.status for m in applied}

        status: dict[str, MigrationStatus] = {}
        for version in sorted(self._migrations.keys()):
            status[version] = applied_map.get(version, MigrationStatus.PENDING)

        return status

    def diff_schemas(
        self,
        current_schema: dict[str, list[str]],
        target_schema: dict[str, list[str]]
    ) -> SchemaDiff:
        """Compare two schemas and generate diff."""
        diff = SchemaDiff()

        current_tables = set(current_schema.keys())
        target_tables = set(target_schema.keys())

        diff.added_tables = list(target_tables - current_tables)
        diff.removed_tables = list(current_tables - target_tables)

        for table in current_tables & target_tables:
            current_cols = set(current_schema[table])
            target_cols = set(target_schema[table])

            added = list(target_cols - current_cols)
            removed = list(current_cols - target_cols)

            if added:
                diff.added_columns[table] = added
            if removed:
                diff.removed_columns[table] = removed

        return diff

    def generate_migration(
        self,
        name: str,
        diff: SchemaDiff
    ) -> Migration:
        """Generate a migration from schema diff."""
        version = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

        return Migration(
            version=version,
            name=name,
            up_sql=diff.generate_up_sql(),
            down_sql=diff.generate_down_sql()
        )


class InMemoryMigrationBackend:
    """In-memory backend for testing."""

    def __init__(self) -> None:
        self._applied: list[Migration] = []
        self._in_transaction = False

    async def get_applied_migrations(self) -> list[Migration]:
        return list(self._applied)

    async def mark_applied(self, migration: Migration) -> None:
        self._applied.append(migration)

    async def mark_rolled_back(self, migration: Migration) -> None:
        self._applied = [m for m in self._applied if m.version != migration.version]

    async def execute_sql(self, sql: str) -> None:
        pass

    async def begin_transaction(self) -> None:
        self._in_transaction = True

    async def commit_transaction(self) -> None:
        self._in_transaction = False

    async def rollback_transaction(self) -> None:
        self._in_transaction = False
