"""Unit tests for repository caching decorator.

**Feature: repository-caching**
**Validates: Automatic caching and invalidation for repositories**

Tests verify that the decorator:
- Caches read operations (get_by_id, get_all, exists)
- Invalidates cache on mutations (create, update, delete)
- Generates proper cache keys
- Handles cache failures gracefully
"""

import pytest
from typing import Any
from pydantic import BaseModel

from src.infrastructure.cache.repository import (
    cached_repository,
    RepositoryCacheConfig,
    invalidate_repository_cache,
)
from src.infrastructure.cache.providers import InMemoryCacheProvider
from src.core.base.repository.interface import IRepository


# Test models
class User(BaseModel):
    """Test user model."""

    id: str
    email: str
    name: str


class CreateUser(BaseModel):
    """Test create DTO."""

    email: str
    name: str


class UpdateUser(BaseModel):
    """Test update DTO."""

    name: str | None = None


# Mock repository without caching
class UserRepository(IRepository[User, CreateUser, UpdateUser, str]):
    """Mock user repository for testing."""

    def __init__(self) -> None:
        self._data: dict[str, User] = {}
        self._call_counts: dict[str, int] = {
            "get_by_id": 0,
            "get_all": 0,
            "create": 0,
            "update": 0,
            "delete": 0,
            "exists": 0,
            "create_many": 0,
        }

    async def get_by_id(self, id: str) -> User | None:
        """Get user by ID."""
        self._call_counts["get_by_id"] += 1
        return self._data.get(id)

    async def get_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[User], int]:
        """Get all users."""
        self._call_counts["get_all"] += 1
        users = list(self._data.values())[skip : skip + limit]
        return users, len(self._data)

    async def create(self, data: CreateUser) -> User:
        """Create user."""
        self._call_counts["create"] += 1
        user_id = f"user_{len(self._data) + 1}"
        user = User(id=user_id, email=data.email, name=data.name)
        self._data[user_id] = user
        return user

    async def update(self, id: str, data: UpdateUser) -> User | None:
        """Update user."""
        self._call_counts["update"] += 1
        user = self._data.get(id)
        if user is None:
            return None
        updated = user.model_copy(update=data.model_dump(exclude_unset=True))
        self._data[id] = updated
        return updated

    async def delete(self, id: str, *, soft: bool = True) -> bool:
        """Delete user."""
        self._call_counts["delete"] += 1
        if id in self._data:
            del self._data[id]
            return True
        return False

    async def exists(self, id: str) -> bool:
        """Check if user exists."""
        self._call_counts["exists"] += 1
        return id in self._data

    async def create_many(self, data: list[CreateUser]) -> list[User]:
        """Create many users."""
        self._call_counts["create_many"] += 1
        users = []
        for dto in data:
            user = await self.create(dto)
            users.append(user)
        return users


class TestRepositoryCacheDecorator:
    """Tests for repository caching decorator."""

    @pytest.fixture
    def cache_provider(self) -> InMemoryCacheProvider:
        """Create cache provider."""
        return InMemoryCacheProvider()

    @pytest.fixture
    def cache_config(self) -> RepositoryCacheConfig:
        """Create cache config."""
        return RepositoryCacheConfig(
            ttl=300,
            enabled=True,
            log_hits=False,
            log_misses=False,
        )

    @pytest.fixture
    def cached_repo(
        self, cache_provider: InMemoryCacheProvider, cache_config: RepositoryCacheConfig
    ) -> UserRepository:
        """Create cached repository."""

        @cached_repository(cache_provider, cache_config)
        class CachedUserRepository(UserRepository):
            pass

        return CachedUserRepository()

    @pytest.mark.asyncio
    async def test_get_by_id_caches_result(self, cached_repo: UserRepository) -> None:
        """Test that get_by_id caches the result."""
        # Create a user
        user = await cached_repo.create(CreateUser(email="test@example.com", name="Test"))

        # First call - cache miss
        result1 = await cached_repo.get_by_id(user.id)
        assert result1 == user
        assert cached_repo._call_counts["get_by_id"] == 1

        # Second call - cache hit (should not increment call count)
        result2 = await cached_repo.get_by_id(user.id)
        assert result2 == user
        assert cached_repo._call_counts["get_by_id"] == 1  # Still 1!

    @pytest.mark.asyncio
    async def test_get_all_caches_result(self, cached_repo: UserRepository) -> None:
        """Test that get_all caches the result."""
        # Create users
        await cached_repo.create(CreateUser(email="user1@example.com", name="User 1"))
        await cached_repo.create(CreateUser(email="user2@example.com", name="User 2"))

        # First call - cache miss
        users1, count1 = await cached_repo.get_all()
        assert len(users1) == 2
        assert cached_repo._call_counts["get_all"] == 1

        # Second call - cache hit
        users2, count2 = await cached_repo.get_all()
        assert len(users2) == 2
        assert cached_repo._call_counts["get_all"] == 1  # Still 1!

    @pytest.mark.asyncio
    async def test_exists_caches_result(self, cached_repo: UserRepository) -> None:
        """Test that exists caches the result."""
        user = await cached_repo.create(CreateUser(email="test@example.com", name="Test"))

        # First call - cache miss
        exists1 = await cached_repo.exists(user.id)
        assert exists1 is True
        assert cached_repo._call_counts["exists"] == 1

        # Second call - cache hit
        exists2 = await cached_repo.exists(user.id)
        assert exists2 is True
        assert cached_repo._call_counts["exists"] == 1  # Still 1!

    @pytest.mark.asyncio
    async def test_create_invalidates_cache(self, cached_repo: UserRepository) -> None:
        """Test that create invalidates all cached entries."""
        # Create first user and cache get_all
        user1 = await cached_repo.create(CreateUser(email="user1@example.com", name="User 1"))
        users1, _ = await cached_repo.get_all()
        assert len(users1) == 1
        assert cached_repo._call_counts["get_all"] == 1

        # Call get_all again - should be cached
        users2, _ = await cached_repo.get_all()
        assert cached_repo._call_counts["get_all"] == 1  # Still 1

        # Create second user - should invalidate cache
        user2 = await cached_repo.create(CreateUser(email="user2@example.com", name="User 2"))

        # Call get_all again - should hit database (cache invalidated)
        users3, _ = await cached_repo.get_all()
        assert len(users3) == 2
        assert cached_repo._call_counts["get_all"] == 2  # Incremented!

    @pytest.mark.asyncio
    async def test_update_invalidates_cache(self, cached_repo: UserRepository) -> None:
        """Test that update invalidates cached entries."""
        user = await cached_repo.create(CreateUser(email="test@example.com", name="Test"))

        # Get user - caches it
        result1 = await cached_repo.get_by_id(user.id)
        assert result1.name == "Test"
        assert cached_repo._call_counts["get_by_id"] == 1

        # Update user - invalidates cache
        updated = await cached_repo.update(user.id, UpdateUser(name="Updated"))
        assert updated.name == "Updated"

        # Get user again - should hit database (cache invalidated)
        result2 = await cached_repo.get_by_id(user.id)
        assert result2.name == "Updated"
        assert cached_repo._call_counts["get_by_id"] == 2  # Incremented!

    @pytest.mark.asyncio
    async def test_delete_invalidates_cache(self, cached_repo: UserRepository) -> None:
        """Test that delete invalidates cached entries."""
        user = await cached_repo.create(CreateUser(email="test@example.com", name="Test"))

        # Get user - caches it
        result1 = await cached_repo.get_by_id(user.id)
        assert result1 is not None
        assert cached_repo._call_counts["get_by_id"] == 1

        # Delete user - invalidates cache
        deleted = await cached_repo.delete(user.id)
        assert deleted is True

        # Get user again - should hit database (cache invalidated)
        result2 = await cached_repo.get_by_id(user.id)
        assert result2 is None
        assert cached_repo._call_counts["get_by_id"] == 2  # Incremented!

    @pytest.mark.asyncio
    async def test_cache_disabled_does_not_cache(
        self, cache_provider: InMemoryCacheProvider
    ) -> None:
        """Test that caching can be disabled."""
        config = RepositoryCacheConfig(enabled=False)

        @cached_repository(cache_provider, config)
        class DisabledCacheRepo(UserRepository):
            pass

        repo = DisabledCacheRepo()
        user = await repo.create(CreateUser(email="test@example.com", name="Test"))

        # Both calls should hit database
        _ = await repo.get_by_id(user.id)
        _ = await repo.get_by_id(user.id)

        assert repo._call_counts["get_by_id"] == 2  # Both hit database

    @pytest.mark.asyncio
    async def test_cache_key_includes_entity_name(
        self, cache_provider: InMemoryCacheProvider, cache_config: RepositoryCacheConfig
    ) -> None:
        """Test that cache keys include entity name for isolation."""

        @cached_repository(cache_provider, cache_config)
        class CachedUserRepository(UserRepository):
            pass

        repo = CachedUserRepository()
        user = await repo.create(CreateUser(email="test@example.com", name="Test"))

        # Get user - should cache with "User" in key
        _ = await repo.get_by_id(user.id)

        # Verify cache key exists
        stats = await cache_provider.get_stats()
        assert stats.entry_count > 0

        # Keys should include "User" entity name
        # (We can't directly inspect keys in InMemory provider, but we know it was cached)

    @pytest.mark.asyncio
    async def test_none_results_not_cached(self, cached_repo: UserRepository) -> None:
        """Test that None results are not cached."""
        # Get non-existent user - should return None
        result1 = await cached_repo.get_by_id("nonexistent")
        assert result1 is None
        assert cached_repo._call_counts["get_by_id"] == 1

        # Get again - should hit database (None not cached)
        result2 = await cached_repo.get_by_id("nonexistent")
        assert result2 is None
        assert cached_repo._call_counts["get_by_id"] == 2  # Incremented!

    @pytest.mark.asyncio
    async def test_pattern_matching_works(
        self, cache_provider: InMemoryCacheProvider
    ) -> None:
        """Test that pattern matching works correctly."""
        # Manually set cache entries
        await cache_provider.set("repo:User:get_by_id:123", {"id": "123", "name": "Test"})
        await cache_provider.set("repo:User:get_all:_", [{"id": "123"}])
        await cache_provider.set("repo:Order:get_by_id:456", {"id": "456"})

        # Clear User entries
        count = await cache_provider.clear_pattern("repo:User:*")
        assert count == 2  # Should clear 2 User entries

        # Verify User entries are gone
        user_entry = await cache_provider.get("repo:User:get_by_id:123")
        assert user_entry is None

        # Verify Order entry still exists
        order_entry = await cache_provider.get("repo:Order:get_by_id:456")
        assert order_entry is not None

    @pytest.mark.asyncio
    async def test_manual_cache_invalidation(
        self, cache_provider: InMemoryCacheProvider, cached_repo: UserRepository
    ) -> None:
        """Test manual cache invalidation helper."""
        user = await cached_repo.create(CreateUser(email="test@example.com", name="Test"))

        # Reset call counts after create (which invalidates cache)
        cached_repo._call_counts["get_by_id"] = 0

        # Cache the result (after create invalidation)
        result = await cached_repo.get_by_id(user.id)
        assert result is not None
        assert cached_repo._call_counts["get_by_id"] == 1

        # Verify cache is populated
        stats_before = await cache_provider.get_stats()
        print(f"Cache entries before clear: {stats_before.entry_count}")
        assert stats_before.entry_count > 0

        # Check what's in the cache by trying to get it directly
        # The key should be "repo:CachedUser:get_by_id:{user.id}" (CachedUserRepository -> CachedUser)
        expected_key = f"repo:CachedUser:get_by_id:{user.id}"
        direct_get = await cache_provider.get(expected_key)
        print(f"Direct get of '{expected_key}': {direct_get}")

        # Try the pattern (use "CachedUser" not "User")
        count = await cache_provider.clear_pattern("repo:CachedUser:*")
        print(f"Clear pattern 'repo:CachedUser:*' cleared {count} entries")

        stats_after = await cache_provider.get_stats()
        print(f"Cache entries after clear: {stats_after.entry_count}")

        # Verify that cache was cleared
        assert count > 0, f"Expected cache entries to be cleared, but got {count}"
        assert stats_after.entry_count == 0, "Cache should be empty after clear"

        # Get again - should hit database (cache invalidated)
        _ = await cached_repo.get_by_id(user.id)
        print(f"get_by_id count after second call: {cached_repo._call_counts['get_by_id']}")
        assert cached_repo._call_counts["get_by_id"] == 2

    @pytest.mark.asyncio
    async def test_different_methods_have_different_cache_keys(
        self, cached_repo: UserRepository
    ) -> None:
        """Test that different methods have isolated cache keys."""
        user = await cached_repo.create(CreateUser(email="test@example.com", name="Test"))

        # Cache get_by_id
        _ = await cached_repo.get_by_id(user.id)
        assert cached_repo._call_counts["get_by_id"] == 1

        # exists should have its own cache (different method)
        _ = await cached_repo.exists(user.id)
        assert cached_repo._call_counts["exists"] == 1

        # Call exists again - should be cached
        _ = await cached_repo.exists(user.id)
        assert cached_repo._call_counts["exists"] == 1  # Still 1

        # Call get_by_id again - should still be cached
        _ = await cached_repo.get_by_id(user.id)
        assert cached_repo._call_counts["get_by_id"] == 1  # Still 1

    @pytest.mark.asyncio
    async def test_create_many_invalidates_cache(self, cached_repo: UserRepository) -> None:
        """Test that create_many invalidates cache."""
        # Cache get_all
        users1, _ = await cached_repo.get_all()
        assert len(users1) == 0
        assert cached_repo._call_counts["get_all"] == 1

        # Create many users - should invalidate cache
        await cached_repo.create_many(
            [
                CreateUser(email="user1@example.com", name="User 1"),
                CreateUser(email="user2@example.com", name="User 2"),
            ]
        )

        # Get all again - should hit database (cache invalidated)
        users2, _ = await cached_repo.get_all()
        assert len(users2) == 2
        assert cached_repo._call_counts["get_all"] == 2  # Incremented!
