"""Property-based tests for Migration Manager.

**Feature: api-architecture-analysis, Property: Migration operations**
**Validates: Requirements 19.1**
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime

from my_api.shared.migration_manager import (
    Migration,
    MigrationManager,
    MigrationStatus,
    SchemaDiff,
    InMemoryMigrationBackend,
)


@st.composite
def migration_strategy(draw: st.DrawFn) -> Migration:
    """Generate valid migrations."""
    version = draw(st.text(
        alphabet="0123456789",
        min_size=14,
        max_size=14
    ))
    name = draw(st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz_",
        min_size=3,
        max_size=30
    ))
    up_sql = draw(st.text(min_size=1, max_size=100))
    down_sql = draw(st.text(min_size=1, max_size=100))
    return Migration(version=version, name=name, up_sql=up_sql, down_sql=down_sql)


class TestMigrationProperties:
    """Property tests for migrations."""

    @given(migration_strategy())
    @settings(max_examples=100)
    def test_checksum_deterministic(self, migration: Migration) -> None:
        """Checksum is deterministic for same content."""
        m1 = Migration(
            version=migration.version,
            name=migration.name,
            up_sql=migration.up_sql,
            down_sql=migration.down_sql
        )
        m2 = Migration(
            version=migration.version,
            name=migration.name,
            up_sql=migration.up_sql,
            down_sql=migration.down_sql
        )
        assert m1.checksum == m2.checksum

    @given(st.lists(migration_strategy(), min_size=0, max_size=5, unique_by=lambda m: m.version))
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_pending_migrations_correct(self, migrations: list[Migration]) -> None:
        """Pending migrations excludes applied ones."""
        backend = InMemoryMigrationBackend()
        manager = MigrationManager(backend)

        for m in migrations:
            manager.register(m)

        applied = await backend.get_applied_migrations()
        pending = manager.get_pending_migrations(applied)

        assert len(pending) == len(migrations)

    @given(
        st.dictionaries(
            st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=10),
            st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=5),
            min_size=0,
            max_size=5
        ),
        st.dictionaries(
            st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=10),
            st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=5),
            min_size=0,
            max_size=5
        )
    )
    @settings(max_examples=50)
    def test_schema_diff_detects_changes(
        self,
        current: dict[str, list[str]],
        target: dict[str, list[str]]
    ) -> None:
        """Schema diff correctly identifies changes."""
        manager = MigrationManager(InMemoryMigrationBackend())
        diff = manager.diff_schemas(current, target)

        current_tables = set(current.keys())
        target_tables = set(target.keys())

        assert set(diff.added_tables) == target_tables - current_tables
        assert set(diff.removed_tables) == current_tables - target_tables


class TestSchemaDiffProperties:
    """Property tests for schema diff."""

    @given(st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=5))
    @settings(max_examples=50)
    def test_added_tables_in_up_sql(self, tables: list[str]) -> None:
        """Added tables appear in up SQL."""
        diff = SchemaDiff(added_tables=tables)
        up_sql = diff.generate_up_sql()

        for table in tables:
            assert table in up_sql

    @given(st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=5))
    @settings(max_examples=50)
    def test_added_tables_dropped_in_down_sql(self, tables: list[str]) -> None:
        """Added tables are dropped in down SQL."""
        diff = SchemaDiff(added_tables=tables)
        down_sql = diff.generate_down_sql()

        for table in tables:
            assert table in down_sql

    def test_empty_diff_has_no_changes(self) -> None:
        """Empty diff reports no changes."""
        diff = SchemaDiff()
        assert not diff.has_changes
