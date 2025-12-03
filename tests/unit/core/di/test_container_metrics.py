"""Unit tests for Container metrics and observability.

**Feature: di-observability**
**Validates: Container metrics tracking and statistics**

Tests verify that the Container correctly tracks:
- Registrations by lifetime (SINGLETON, TRANSIENT, SCOPED)
- Resolution counts overall and per type
- Singleton instance creation
"""

import pytest

from src.core.di.container import Container, ContainerStats, Lifetime


class Database:
    """Mock database service."""

    pass


class UserRepository:
    """Mock repository depending on Database."""

    def __init__(self, db: Database) -> None:
        self.db = db


class EmailService:
    """Mock email service (transient)."""

    pass


class RequestContext:
    """Mock request context (scoped)."""

    pass


class TestContainerMetrics:
    """Tests for Container metrics tracking."""

    def test_initial_stats_are_zero(self) -> None:
        """Test that new container starts with zero metrics."""
        container = Container()

        stats = container.get_stats()

        assert stats.total_registrations == 0
        assert stats.singleton_registrations == 0
        assert stats.transient_registrations == 0
        assert stats.scoped_registrations == 0
        assert stats.total_resolutions == 0
        assert stats.singleton_instances_created == 0
        assert len(stats.resolutions_by_type) == 0

    def test_register_singleton_increments_stats(self) -> None:
        """Test that singleton registration increments counters."""
        container = Container()

        container.register_singleton(Database)
        stats = container.get_stats()

        assert stats.total_registrations == 1
        assert stats.singleton_registrations == 1
        assert stats.transient_registrations == 0
        assert stats.scoped_registrations == 0

    def test_register_transient_increments_stats(self) -> None:
        """Test that transient registration increments counters."""
        container = Container()

        container.register(EmailService, lifetime=Lifetime.TRANSIENT)
        stats = container.get_stats()

        assert stats.total_registrations == 1
        assert stats.singleton_registrations == 0
        assert stats.transient_registrations == 1
        assert stats.scoped_registrations == 0

    def test_register_scoped_increments_stats(self) -> None:
        """Test that scoped registration increments counters."""
        container = Container()

        container.register_scoped(RequestContext)
        stats = container.get_stats()

        assert stats.total_registrations == 1
        assert stats.singleton_registrations == 0
        assert stats.transient_registrations == 0
        assert stats.scoped_registrations == 1

    def test_register_instance_increments_stats(self) -> None:
        """Test that instance registration increments counters and tracks creation."""
        container = Container()
        db_instance = Database()

        container.register_instance(Database, db_instance)
        stats = container.get_stats()

        assert stats.total_registrations == 1
        assert stats.singleton_registrations == 1
        assert stats.singleton_instances_created == 1

    def test_multiple_registrations_track_correctly(self) -> None:
        """Test that multiple registrations of different lifetimes track correctly."""
        container = Container()

        container.register_singleton(Database)
        container.register(EmailService, lifetime=Lifetime.TRANSIENT)
        container.register_scoped(RequestContext)
        container.register(UserRepository)  # Default: TRANSIENT

        stats = container.get_stats()

        assert stats.total_registrations == 4
        assert stats.singleton_registrations == 1
        assert stats.transient_registrations == 2
        assert stats.scoped_registrations == 1

    def test_resolve_singleton_increments_resolution_count(self) -> None:
        """Test that resolving singleton increments resolution counter."""
        container = Container()
        container.register_singleton(Database)

        _ = container.resolve(Database)
        stats = container.get_stats()

        assert stats.total_resolutions == 1
        assert stats.singleton_instances_created == 1
        assert stats.resolutions_by_type["Database"] == 1

    def test_resolve_singleton_multiple_times_tracks_resolutions(self) -> None:
        """Test that resolving singleton multiple times tracks all resolutions."""
        container = Container()
        container.register_singleton(Database)

        # Resolve 3 times
        _ = container.resolve(Database)
        _ = container.resolve(Database)
        _ = container.resolve(Database)

        stats = container.get_stats()

        assert stats.total_resolutions == 3
        assert stats.singleton_instances_created == 1  # Only created once
        assert stats.resolutions_by_type["Database"] == 3

    def test_resolve_transient_creates_multiple_instances(self) -> None:
        """Test that resolving transient creates multiple instances (not tracked in singleton count)."""
        container = Container()
        container.register(EmailService, lifetime=Lifetime.TRANSIENT)

        # Resolve 3 times
        instance1 = container.resolve(EmailService)
        instance2 = container.resolve(EmailService)
        instance3 = container.resolve(EmailService)

        stats = container.get_stats()

        assert stats.total_resolutions == 3
        assert stats.singleton_instances_created == 0  # Transients don't count
        assert stats.resolutions_by_type["EmailService"] == 3

        # Verify different instances
        assert instance1 is not instance2
        assert instance2 is not instance3

    def test_resolve_with_dependencies_tracks_all_resolutions(self) -> None:
        """Test that resolving service with dependencies tracks all resolutions."""
        container = Container()
        container.register_singleton(Database)
        container.register(UserRepository)  # Depends on Database

        _ = container.resolve(UserRepository)
        stats = container.get_stats()

        assert stats.total_resolutions == 2  # UserRepository + Database
        assert stats.singleton_instances_created == 1  # Only Database
        assert stats.resolutions_by_type["UserRepository"] == 1
        assert stats.resolutions_by_type["Database"] == 1

    def test_resolutions_by_type_tracks_multiple_types(self) -> None:
        """Test that resolutions_by_type correctly tracks multiple service types."""
        container = Container()
        container.register_singleton(Database)
        container.register(EmailService, lifetime=Lifetime.TRANSIENT)
        container.register_scoped(RequestContext)

        # Resolve each service multiple times
        _ = container.resolve(Database)
        _ = container.resolve(Database)
        _ = container.resolve(EmailService)
        _ = container.resolve(EmailService)
        _ = container.resolve(EmailService)

        stats = container.get_stats()

        assert stats.total_resolutions == 5
        assert stats.resolutions_by_type["Database"] == 2
        assert stats.resolutions_by_type["EmailService"] == 3

    def test_get_stats_returns_copy_not_reference(self) -> None:
        """Test that get_stats returns a copy to prevent external mutation."""
        container = Container()
        container.register_singleton(Database)
        _ = container.resolve(Database)

        stats1 = container.get_stats()
        stats2 = container.get_stats()

        # Modify stats1
        stats1.resolutions_by_type["FakeService"] = 999

        # stats2 should not be affected
        assert "FakeService" not in stats2.resolutions_by_type
        assert stats2.resolutions_by_type["Database"] == 1

    def test_complex_scenario_with_all_lifetimes(self) -> None:
        """Test complex scenario with all lifetime types and multiple resolutions."""
        container = Container()

        # Register services
        container.register_singleton(Database)
        container.register(EmailService, lifetime=Lifetime.TRANSIENT)
        container.register_scoped(RequestContext)
        container.register(UserRepository)  # TRANSIENT with dependency

        # Resolve services
        _ = container.resolve(Database)
        _ = container.resolve(Database)  # Singleton reused
        _ = container.resolve(EmailService)
        _ = container.resolve(EmailService)
        _ = container.resolve(EmailService)
        _ = container.resolve(UserRepository)  # Also resolves Database

        stats = container.get_stats()

        # Registrations
        assert stats.total_registrations == 4
        assert stats.singleton_registrations == 1
        assert stats.transient_registrations == 2
        assert stats.scoped_registrations == 1

        # Resolutions
        assert stats.total_resolutions == 7  # 2 + 3 + 1 + 1 (Database from UserRepository)
        assert stats.singleton_instances_created == 1

        # Per-type resolutions
        assert stats.resolutions_by_type["Database"] == 3
        assert stats.resolutions_by_type["EmailService"] == 3
        assert stats.resolutions_by_type["UserRepository"] == 1

    def test_stats_dataclass_can_be_serialized(self) -> None:
        """Test that ContainerStats can be easily serialized (e.g., for logging)."""
        container = Container()
        container.register_singleton(Database)
        _ = container.resolve(Database)

        stats = container.get_stats()

        # Should be able to convert to dict for logging/serialization
        stats_dict = {
            "total_registrations": stats.total_registrations,
            "singleton_registrations": stats.singleton_registrations,
            "transient_registrations": stats.transient_registrations,
            "scoped_registrations": stats.scoped_registrations,
            "total_resolutions": stats.total_resolutions,
            "singleton_instances_created": stats.singleton_instances_created,
            "resolutions_by_type": stats.resolutions_by_type,
        }

        assert stats_dict["total_registrations"] == 1
        assert stats_dict["total_resolutions"] == 1
        assert isinstance(stats_dict["resolutions_by_type"], dict)
