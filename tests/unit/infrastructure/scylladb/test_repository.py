"""Unit tests for ScyllaDB repository.

**Feature: enterprise-infrastructure-2025**
**Requirement: S-004 - ScyllaDB Repository**
"""

import pytest
from typing import ClassVar
from uuid import uuid4

from infrastructure.scylladb.entity import ScyllaDBEntity
from infrastructure.scylladb.repository import ScyllaDBRepository


class User(ScyllaDBEntity):
    """Test user entity."""

    table_name: ClassVar[str] = "users"
    partition_keys: ClassVar[list[str]] = ["id"]
    clustering_keys: ClassVar[list[str]] = []

    id: str
    email: str
    name: str


class TestScyllaDBRepository:
    """Tests for ScyllaDBRepository."""

    def test_repository_initialization(self) -> None:
        """Test repository can be initialized."""
        from unittest.mock import AsyncMock

        mock_client = AsyncMock()
        repo = ScyllaDBRepository(User, mock_client)

        assert repo is not None

    def test_entity_table_name(self) -> None:
        """Test entity table name."""
        assert User.table_name == "users"

    def test_entity_primary_key(self) -> None:
        """Test entity primary key."""
        pk = User.primary_key()
        assert "id" in pk

    def test_entity_creation(self) -> None:
        """Test entity can be created."""
        user_id = str(uuid4())
        user = User(
            id=user_id,
            email="john@example.com",
            name="John Doe",
        )

        assert user.id == user_id
        assert user.email == "john@example.com"
        assert user.name == "John Doe"

    def test_entity_serialization(self) -> None:
        """Test entity serialization."""
        user_id = str(uuid4())
        user = User(
            id=user_id,
            email="john@example.com",
            name="John Doe",
        )

        data = user.model_dump()

        assert data["id"] == user_id
        assert data["email"] == "john@example.com"
        assert data["name"] == "John Doe"
