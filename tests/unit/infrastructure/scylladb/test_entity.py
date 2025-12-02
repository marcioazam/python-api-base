"""Unit tests for ScyllaDB entity.

**Feature: observability-infrastructure**
**Requirement: R4 - Generic ScyllaDB Repository**
"""

import pytest
from datetime import datetime, UTC
from uuid import UUID, uuid4

from infrastructure.scylladb.entity import ScyllaDBEntity


class User(ScyllaDBEntity):
    """Sample entity for testing."""

    __table_name__ = "users"
    __primary_key__ = ["id"]

    name: str
    email: str
    age: int | None = None


class Event(ScyllaDBEntity):
    """Entity with composite key for testing."""

    __table_name__ = "events"
    __primary_key__ = ["tenant_id"]
    __clustering_key__ = ["event_id"]

    tenant_id: UUID
    event_id: UUID
    event_type: str
    data: str | None = None


class TestScyllaDBEntity:
    """Tests for ScyllaDBEntity."""

    def test_create_entity(self) -> None:
        """Test creating an entity."""
        user = User(name="John", email="john@example.com")

        assert user.name == "John"
        assert user.email == "john@example.com"
        assert user.id is not None
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_table_name(self) -> None:
        """Test table_name class method."""
        assert User.table_name() == "users"
        assert Event.table_name() == "events"

    def test_table_name_default(self) -> None:
        """Test default table name from class name."""

        class MyTestEntity(ScyllaDBEntity):
            value: str

        # Should convert to snake_case
        assert "my_test_entity" in MyTestEntity.table_name().lower()

    def test_primary_key(self) -> None:
        """Test primary_key class method."""
        assert User.primary_key() == ["id"]
        assert Event.primary_key() == ["tenant_id"]

    def test_clustering_key(self) -> None:
        """Test clustering_key class method."""
        assert User.clustering_key() == []
        assert Event.clustering_key() == ["event_id"]

    def test_columns(self) -> None:
        """Test columns class method."""
        columns = User.columns()

        assert "id" in columns
        assert "name" in columns
        assert "email" in columns
        assert "created_at" in columns
        assert columns["id"] == "uuid"
        assert columns["name"] == "text"

    def test_to_dict(self) -> None:
        """Test to_dict method."""
        user = User(name="John", email="john@example.com", age=30)
        data = user.to_dict()

        assert data["name"] == "John"
        assert data["email"] == "john@example.com"
        assert data["age"] == 30
        assert "id" in data
        assert "created_at" in data

    def test_to_dict_exclude_none(self) -> None:
        """Test to_dict with exclude_none."""
        user = User(name="John", email="john@example.com")
        data = user.to_dict(exclude_none=True)

        assert "age" not in data

    def test_get_primary_key_values(self) -> None:
        """Test get_primary_key_values method."""
        user_id = uuid4()
        user = User(id=user_id, name="John", email="john@example.com")

        pk_values = user.get_primary_key_values()

        assert pk_values == {"id": user_id}

    def test_get_primary_key_values_composite(self) -> None:
        """Test get_primary_key_values with composite key."""
        tenant_id = uuid4()
        event_id = uuid4()

        event = Event(
            tenant_id=tenant_id,
            event_id=event_id,
            event_type="click",
        )

        pk_values = event.get_primary_key_values()

        assert pk_values["tenant_id"] == tenant_id
        assert pk_values["event_id"] == event_id

    def test_from_row_namedtuple(self) -> None:
        """Test from_row with named tuple."""
        from collections import namedtuple

        Row = namedtuple("Row", ["id", "name", "email", "age", "created_at", "updated_at"])
        row = Row(
            id=uuid4(),
            name="Jane",
            email="jane@example.com",
            age=25,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        user = User.from_row(row)

        assert user.name == "Jane"
        assert user.email == "jane@example.com"
        assert user.age == 25
