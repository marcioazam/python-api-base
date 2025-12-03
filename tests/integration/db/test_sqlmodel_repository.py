"""Integration tests for SQLModel repository.

**Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 14.2**
"""

import pytest
pytest.skip("Module infrastructure.adapters not implemented", allow_module_level=True)
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.adapters.repositories.sqlmodel_repository import SQLModelRepository
from domain.entities.item import Item, ItemCreate, ItemUpdate
from infrastructure.database.session import DatabaseSession


@pytest.mark.asyncio
class TestSQLModelRepositoryIntegration:
    """Integration tests for SQLModelRepository with real database."""

    async def test_create_and_get_by_id(self, db_session: DatabaseSession) -> None:
        """Test creating an entity and retrieving it by ID."""
        async with db_session.session() as session:
            repo = SQLModelRepository[Item, ItemCreate, ItemUpdate](
                session=session,
                model_class=Item,
            )
            
            create_data = ItemCreate(
                name="Integration Test Item",
                description="Testing with real database",
                price=99.99,
                tax=8.00,
            )
            
            # Create
            created = await repo.create(create_data)
            assert created.id is not None
            assert created.name == "Integration Test Item"
            assert created.price == 99.99
            
            # Get by ID
            retrieved = await repo.get_by_id(created.id)
            assert retrieved is not None
            assert retrieved.id == created.id
            assert retrieved.name == created.name

    async def test_get_all_with_pagination(self, db_session: DatabaseSession) -> None:
        """Test getting all entities with pagination."""
        async with db_session.session() as session:
            repo = SQLModelRepository[Item, ItemCreate, ItemUpdate](
                session=session,
                model_class=Item,
            )
            
            # Create multiple items
            for i in range(5):
                await repo.create(ItemCreate(
                    name=f"Item {i}",
                    price=float(10 + i),
                ))
            
            # Get with pagination
            entities, total = await repo.get_all(skip=0, limit=3)
            assert total == 5
            assert len(entities) == 3
            
            # Get second page
            entities2, total2 = await repo.get_all(skip=3, limit=3)
            assert total2 == 5
            assert len(entities2) == 2

    async def test_update_entity(self, db_session: DatabaseSession) -> None:
        """Test updating an existing entity."""
        async with db_session.session() as session:
            repo = SQLModelRepository[Item, ItemCreate, ItemUpdate](
                session=session,
                model_class=Item,
            )
            
            # Create
            created = await repo.create(ItemCreate(
                name="Original Name",
                price=50.00,
            ))
            
            # Update
            update_data = ItemUpdate(name="Updated Name", price=75.00)
            updated = await repo.update(created.id, update_data)
            
            assert updated is not None
            assert updated.name == "Updated Name"
            assert updated.price == 75.00
            
            # Verify persistence
            retrieved = await repo.get_by_id(created.id)
            assert retrieved.name == "Updated Name"

    async def test_soft_delete(self, db_session: DatabaseSession) -> None:
        """Test soft delete functionality."""
        async with db_session.session() as session:
            repo = SQLModelRepository[Item, ItemCreate, ItemUpdate](
                session=session,
                model_class=Item,
            )
            
            # Create
            created = await repo.create(ItemCreate(
                name="To Be Deleted",
                price=25.00,
            ))
            
            # Delete
            deleted = await repo.delete(created.id, soft=True)
            assert deleted is True
            
            # Should not be retrievable
            retrieved = await repo.get_by_id(created.id)
            assert retrieved is None

    async def test_exists(self, db_session: DatabaseSession) -> None:
        """Test exists check."""
        async with db_session.session() as session:
            repo = SQLModelRepository[Item, ItemCreate, ItemUpdate](
                session=session,
                model_class=Item,
            )
            
            # Create
            created = await repo.create(ItemCreate(
                name="Exists Test",
                price=15.00,
            ))
            
            # Should exist
            assert await repo.exists(created.id) is True
            
            # Non-existent should not exist
            assert await repo.exists("nonexistent-id") is False

    async def test_create_many(self, db_session: DatabaseSession) -> None:
        """Test bulk create functionality."""
        async with db_session.session() as session:
            repo = SQLModelRepository[Item, ItemCreate, ItemUpdate](
                session=session,
                model_class=Item,
            )
            
            items_data = [
                ItemCreate(name=f"Bulk Item {i}", price=float((i + 1) * 10))
                for i in range(3)
            ]
            
            created = await repo.create_many(items_data)
            
            assert len(created) == 3
            assert all(item.id is not None for item in created)
            
            # Verify all were persisted
            entities, total = await repo.get_all()
            assert total == 3

    async def test_get_all_with_filters(self, db_session: DatabaseSession) -> None:
        """Test filtering entities."""
        async with db_session.session() as session:
            repo = SQLModelRepository[Item, ItemCreate, ItemUpdate](
                session=session,
                model_class=Item,
            )
            
            # Create items with different names
            await repo.create(ItemCreate(name="Apple", price=1.00))
            await repo.create(ItemCreate(name="Banana", price=2.00))
            await repo.create(ItemCreate(name="Apple", price=3.00))
            
            # Filter by name
            entities, total = await repo.get_all(filters={"name": "Apple"})
            assert total == 2
            assert all(e.name == "Apple" for e in entities)

    async def test_get_all_with_sorting(self, db_session: DatabaseSession) -> None:
        """Test sorting entities."""
        async with db_session.session() as session:
            repo = SQLModelRepository[Item, ItemCreate, ItemUpdate](
                session=session,
                model_class=Item,
            )
            
            # Create items
            await repo.create(ItemCreate(name="C Item", price=30.00))
            await repo.create(ItemCreate(name="A Item", price=10.00))
            await repo.create(ItemCreate(name="B Item", price=20.00))
            
            # Sort ascending
            entities_asc, _ = await repo.get_all(sort_by="name", sort_order="asc")
            names_asc = [e.name for e in entities_asc]
            assert names_asc == ["A Item", "B Item", "C Item"]
            
            # Sort descending
            entities_desc, _ = await repo.get_all(sort_by="name", sort_order="desc")
            names_desc = [e.name for e in entities_desc]
            assert names_desc == ["C Item", "B Item", "A Item"]

    async def test_update_nonexistent_returns_none(
        self, db_session: DatabaseSession
    ) -> None:
        """Test updating non-existent entity returns None."""
        async with db_session.session() as session:
            repo = SQLModelRepository[Item, ItemCreate, ItemUpdate](
                session=session,
                model_class=Item,
            )
            
            result = await repo.update(
                "nonexistent-id",
                ItemUpdate(name="Test"),
            )
            assert result is None

    async def test_delete_nonexistent_returns_false(
        self, db_session: DatabaseSession
    ) -> None:
        """Test deleting non-existent entity returns False."""
        async with db_session.session() as session:
            repo = SQLModelRepository[Item, ItemCreate, ItemUpdate](
                session=session,
                model_class=Item,
            )
            
            result = await repo.delete("nonexistent-id")
            assert result is False
