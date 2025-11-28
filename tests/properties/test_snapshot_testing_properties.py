"""Property-based tests for Snapshot Testing module.

**Feature: api-architecture-analysis, Property 15.4: API Snapshot Testing**
**Validates: Requirements 8.3**
"""

import pytest
from hypothesis import given, strategies as st, settings
from pathlib import Path
import tempfile

from src.my_api.shared.snapshot_testing import (
    ChangeType,
    ChangeSeverity,
    SchemaChange,
    Snapshot,
    ComparisonResult,
    SnapshotStore,
    SchemaComparator,
    SnapshotTester,
    extract_schema_from_response,
)


# Strategies
snapshot_names = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
    min_size=1, max_size=30,
)
versions = st.from_regex(r"[0-9]+\.[0-9]+\.[0-9]+", fullmatch=True)
field_names = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=10)

simple_values = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-1000, max_value=1000),
    st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False),
    st.text(min_size=0, max_size=20),
)

simple_schemas = st.dictionaries(field_names, simple_values, min_size=1, max_size=5)


class TestSchemaChange:
    """Property tests for SchemaChange."""

    @given(
        path=st.text(min_size=1, max_size=30),
        change_type=st.sampled_from(list(ChangeType)),
        severity=st.sampled_from(list(ChangeSeverity)),
    )
    @settings(max_examples=100)
    def test_to_dict_contains_fields(
        self, path: str, change_type: ChangeType, severity: ChangeSeverity
    ) -> None:
        """to_dict contains all required fields."""
        change = SchemaChange(path=path, change_type=change_type, severity=severity)
        d = change.to_dict()
        assert "path" in d
        assert "change_type" in d
        assert "severity" in d


class TestSnapshot:
    """Property tests for Snapshot."""

    @given(name=snapshot_names, schema=simple_schemas)
    @settings(max_examples=100)
    def test_hash_deterministic(self, name: str, schema: dict) -> None:
        """Same schema produces same hash."""
        snap1 = Snapshot(name=name, schema=schema)
        snap2 = Snapshot(name=name, schema=schema)
        assert snap1.hash == snap2.hash

    @given(name=snapshot_names, schema1=simple_schemas, schema2=simple_schemas)
    @settings(max_examples=100)
    def test_different_schemas_different_hash(
        self, name: str, schema1: dict, schema2: dict
    ) -> None:
        """Different schemas produce different hashes."""
        if schema1 != schema2:
            snap1 = Snapshot(name=name, schema=schema1)
            snap2 = Snapshot(name=name, schema=schema2)
            assert snap1.hash != snap2.hash

    @given(name=snapshot_names, schema=simple_schemas, version=versions)
    @settings(max_examples=100)
    def test_roundtrip_dict(self, name: str, schema: dict, version: str) -> None:
        """Snapshot roundtrips through dict."""
        snap = Snapshot(name=name, schema=schema, version=version)
        d = snap.to_dict()
        restored = Snapshot.from_dict(d)
        assert restored.name == snap.name
        assert restored.schema == snap.schema
        assert restored.version == snap.version


class TestComparisonResult:
    """Property tests for ComparisonResult."""

    @given(name=snapshot_names)
    @settings(max_examples=100)
    def test_empty_changes_compatible(self, name: str) -> None:
        """Empty changes means compatible."""
        result = ComparisonResult(snapshot_name=name, changes=[])
        assert result.is_compatible
        assert not result.has_breaking_changes

    @given(name=snapshot_names, path=st.text(min_size=1, max_size=20))
    @settings(max_examples=100)
    def test_breaking_change_detected(self, name: str, path: str) -> None:
        """Breaking changes are detected."""
        change = SchemaChange(
            path=path, change_type=ChangeType.REMOVED, severity=ChangeSeverity.BREAKING
        )
        result = ComparisonResult(snapshot_name=name, changes=[change])
        assert result.has_breaking_changes
        assert len(result.breaking_changes) == 1


class TestSnapshotStore:
    """Property tests for SnapshotStore."""

    @given(name=snapshot_names, schema=simple_schemas)
    @settings(max_examples=50)
    def test_save_and_load(self, name: str, schema: dict) -> None:
        """Saved snapshot can be loaded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SnapshotStore(Path(tmpdir))
            snap = Snapshot(name=name, schema=schema)
            store.save(snap)
            loaded = store.load(name)
            assert loaded is not None
            assert loaded.name == name
            assert loaded.schema == schema

    @given(name=snapshot_names)
    @settings(max_examples=50)
    def test_load_nonexistent(self, name: str) -> None:
        """Loading nonexistent returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SnapshotStore(Path(tmpdir))
            assert store.load(name) is None

    @given(name=snapshot_names, schema=simple_schemas)
    @settings(max_examples=50)
    def test_exists(self, name: str, schema: dict) -> None:
        """exists returns True after save."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SnapshotStore(Path(tmpdir))
            assert not store.exists(name)
            store.save(Snapshot(name=name, schema=schema))
            assert store.exists(name)

    @given(names=st.lists(snapshot_names, min_size=1, max_size=5, unique=True))
    @settings(max_examples=50)
    def test_list_all(self, names: list[str]) -> None:
        """list_all returns all snapshot names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SnapshotStore(Path(tmpdir))
            for name in names:
                store.save(Snapshot(name=name, schema={"test": 1}))
            listed = store.list_all()
            assert set(listed) == set(names)


class TestSchemaComparator:
    """Property tests for SchemaComparator."""

    @given(schema=simple_schemas)
    @settings(max_examples=100)
    def test_identical_schemas_no_changes(self, schema: dict) -> None:
        """Identical schemas produce no changes."""
        comparator = SchemaComparator()
        changes = comparator.compare(schema, schema)
        assert len(changes) == 0

    @given(schema=simple_schemas, new_field=field_names, new_value=simple_values)
    @settings(max_examples=100)
    def test_added_field_detected(
        self, schema: dict, new_field: str, new_value
    ) -> None:
        """Added fields are detected."""
        if new_field not in schema:
            comparator = SchemaComparator()
            new_schema = {**schema, new_field: new_value}
            changes = comparator.compare(schema, new_schema)
            added = [c for c in changes if c.change_type == ChangeType.ADDED]
            assert len(added) >= 1

    @given(schema=simple_schemas)
    @settings(max_examples=100)
    def test_removed_field_detected(self, schema: dict) -> None:
        """Removed fields are detected."""
        if len(schema) > 1:
            comparator = SchemaComparator()
            key_to_remove = list(schema.keys())[0]
            new_schema = {k: v for k, v in schema.items() if k != key_to_remove}
            changes = comparator.compare(schema, new_schema)
            removed = [c for c in changes if c.change_type == ChangeType.REMOVED]
            assert len(removed) >= 1


class TestSnapshotTester:
    """Property tests for SnapshotTester."""

    @given(name=snapshot_names, schema=simple_schemas)
    @settings(max_examples=50)
    def test_create_and_get(self, name: str, schema: dict) -> None:
        """Created snapshot can be retrieved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tester = SnapshotTester(Path(tmpdir))
            tester.create_snapshot(name, schema)
            snap = tester.get_snapshot(name)
            assert snap is not None
            assert snap.schema == schema

    @given(name=snapshot_names, schema=simple_schemas)
    @settings(max_examples=50)
    def test_compare_identical(self, name: str, schema: dict) -> None:
        """Comparing identical schemas is compatible."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tester = SnapshotTester(Path(tmpdir))
            tester.create_snapshot(name, schema)
            result = tester.compare_with_snapshot(name, schema)
            assert result.is_compatible
            assert not result.has_breaking_changes

    @given(name=snapshot_names, schema=simple_schemas)
    @settings(max_examples=50)
    def test_assert_matches_identical(self, name: str, schema: dict) -> None:
        """assert_matches returns True for identical schemas."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tester = SnapshotTester(Path(tmpdir))
            tester.create_snapshot(name, schema)
            assert tester.assert_matches(name, schema)

    @given(names=st.lists(snapshot_names, min_size=1, max_size=5, unique=True))
    @settings(max_examples=50)
    def test_list_snapshots(self, names: list[str]) -> None:
        """list_snapshots returns all names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tester = SnapshotTester(Path(tmpdir))
            for name in names:
                tester.create_snapshot(name, {"test": 1})
            listed = tester.list_snapshots()
            assert set(listed) == set(names)


class TestExtractSchema:
    """Property tests for extract_schema_from_response."""

    @given(value=st.integers())
    @settings(max_examples=100)
    def test_integer_type(self, value: int) -> None:
        """Integers produce integer type."""
        schema = extract_schema_from_response(value)
        assert schema["type"] == "integer"

    @given(value=st.floats(allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_float_type(self, value: float) -> None:
        """Floats produce number type."""
        schema = extract_schema_from_response(value)
        assert schema["type"] == "number"

    @given(value=st.text())
    @settings(max_examples=100)
    def test_string_type(self, value: str) -> None:
        """Strings produce string type."""
        schema = extract_schema_from_response(value)
        assert schema["type"] == "string"

    @given(value=st.booleans())
    @settings(max_examples=100)
    def test_boolean_type(self, value: bool) -> None:
        """Booleans produce boolean type."""
        schema = extract_schema_from_response(value)
        assert schema["type"] == "boolean"

    def test_null_type(self) -> None:
        """None produces null type."""
        schema = extract_schema_from_response(None)
        assert schema["type"] == "null"

    @given(values=st.lists(st.integers(), min_size=1, max_size=5))
    @settings(max_examples=100)
    def test_array_type(self, values: list) -> None:
        """Lists produce array type."""
        schema = extract_schema_from_response(values)
        assert schema["type"] == "array"

    @given(obj=simple_schemas)
    @settings(max_examples=100)
    def test_object_type(self, obj: dict) -> None:
        """Dicts produce object type."""
        schema = extract_schema_from_response(obj)
        assert schema["type"] == "object"
        assert "properties" in schema
