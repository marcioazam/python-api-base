"""Property-based tests for application services integration.

**Feature: application-services-integration**
**Validates: Requirements 2.1, 2.2, 2.4, 3.2**

Tests correctness properties for:
- Tenant isolation in queries
- Tenant assignment on create
- Feature flag evaluation consistency
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any

import pytest
from hypothesis import given, settings, strategies as st

from application.services.multitenancy import (
    TenantContext,
    get_current_tenant,
    set_current_tenant,
)
from application.services.feature_flags import (
    EvaluationContext,
    FeatureFlagService,
    FlagConfig,
    FlagStatus,
)


# =============================================================================
# Strategies
# =============================================================================

@st.composite
def tenant_ids(draw: st.DrawFn) -> str:
    """Generate valid tenant IDs."""
    return draw(
        st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=1,
            max_size=50,
        )
    )


@st.composite
def user_ids(draw: st.DrawFn) -> str:
    """Generate valid user IDs."""
    return draw(
        st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=1,
            max_size=50,
        )
    )


# =============================================================================
# In-Memory Repository for Testing
# =============================================================================

@dataclass
class TenantAwareEntity:
    """Simple tenant-aware entity for testing."""
    id: str
    tenant_id: str
    name: str


class InMemoryTenantRepository:
    """In-memory repository with tenant filtering for testing."""
    
    def __init__(self) -> None:
        self._storage: dict[str, TenantAwareEntity] = {}
    
    def create(self, entity: TenantAwareEntity) -> TenantAwareEntity:
        """Create entity with current tenant."""
        tenant_id = get_current_tenant()
        if tenant_id is None:
            raise ValueError("No tenant context set")
        entity.tenant_id = tenant_id
        self._storage[entity.id] = entity
        return entity
    
    def get_all(self) -> list[TenantAwareEntity]:
        """Get all entities for current tenant."""
        tenant_id = get_current_tenant()
        if tenant_id is None:
            raise ValueError("No tenant context set")
        return [e for e in self._storage.values() if e.tenant_id == tenant_id]
    
    def get_by_id(self, entity_id: str) -> TenantAwareEntity | None:
        """Get entity by ID within tenant scope."""
        tenant_id = get_current_tenant()
        if tenant_id is None:
            raise ValueError("No tenant context set")
        entity = self._storage.get(entity_id)
        if entity and entity.tenant_id == tenant_id:
            return entity
        return None
    
    def clear(self) -> None:
        """Clear all data."""
        self._storage.clear()


# =============================================================================
# Property 1: Tenant Query Isolation
# **Feature: application-services-integration, Property 1: Tenant Query Isolation**
# **Validates: Requirements 2.1, 2.4**
# =============================================================================

class TestTenantQueryIsolation:
    """Property tests for tenant query isolation."""

    @given(
        tenant1=tenant_ids(),
        tenant2=tenant_ids(),
        entity_name=st.text(min_size=1, max_size=20),
    )
    @settings(max_examples=100)
    def test_tenant_isolation_in_queries(
        self, tenant1: str, tenant2: str, entity_name: str
    ) -> None:
        """**Property 1: Tenant Query Isolation**
        
        *For any* tenant context and any query operation, all returned results 
        should belong exclusively to the current tenant.
        
        **Feature: application-services-integration, Property 1: Tenant Query Isolation**
        **Validates: Requirements 2.1, 2.4**
        """
        # Skip if tenants are the same
        if tenant1 == tenant2:
            return
        
        set_current_tenant(None)
        repo = InMemoryTenantRepository()
        
        # Create entity in tenant1
        with TenantContext(tenant1):
            entity1 = TenantAwareEntity(id="entity-1", tenant_id="", name=entity_name)
            repo.create(entity1)
        
        # Create entity in tenant2
        with TenantContext(tenant2):
            entity2 = TenantAwareEntity(id="entity-2", tenant_id="", name=entity_name)
            repo.create(entity2)
        
        # Query from tenant1 should only see tenant1's data
        with TenantContext(tenant1):
            results = repo.get_all()
            assert len(results) == 1
            assert all(e.tenant_id == tenant1 for e in results)
            assert repo.get_by_id("entity-2") is None  # Can't see tenant2's entity
        
        # Query from tenant2 should only see tenant2's data
        with TenantContext(tenant2):
            results = repo.get_all()
            assert len(results) == 1
            assert all(e.tenant_id == tenant2 for e in results)
            assert repo.get_by_id("entity-1") is None  # Can't see tenant1's entity
        
        set_current_tenant(None)


# =============================================================================
# Property 2: Tenant Assignment on Create
# **Feature: application-services-integration, Property 2: Tenant Assignment on Create**
# **Validates: Requirements 2.2**
# =============================================================================

class TestTenantAssignmentOnCreate:
    """Property tests for automatic tenant assignment."""

    @given(
        tenant_id=tenant_ids(),
        entity_id=st.text(min_size=1, max_size=20),
        entity_name=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=100)
    def test_tenant_automatically_assigned_on_create(
        self, tenant_id: str, entity_id: str, entity_name: str
    ) -> None:
        """**Property 2: Tenant Assignment on Create**
        
        *For any* tenant context and any create operation, the created entity 
        should have its tenant_id field set to the current tenant.
        
        **Feature: application-services-integration, Property 2: Tenant Assignment on Create**
        **Validates: Requirements 2.2**
        """
        set_current_tenant(None)
        repo = InMemoryTenantRepository()
        
        with TenantContext(tenant_id):
            # Create entity without explicit tenant_id
            entity = TenantAwareEntity(id=entity_id, tenant_id="", name=entity_name)
            created = repo.create(entity)
            
            # Verify tenant_id was automatically assigned
            assert created.tenant_id == tenant_id
            
            # Verify entity can be retrieved
            retrieved = repo.get_by_id(entity_id)
            assert retrieved is not None
            assert retrieved.tenant_id == tenant_id
        
        set_current_tenant(None)


# =============================================================================
# Property 3: Feature Flag Evaluation Consistency
# **Feature: application-services-integration, Property 3: Feature Flag Evaluation Consistency**
# **Validates: Requirements 3.2**
# =============================================================================

class TestFeatureFlagConsistency:
    """Property tests for feature flag evaluation consistency."""

    @given(
        user_id=user_ids(),
        percentage=st.floats(min_value=0.0, max_value=100.0),
    )
    @settings(max_examples=100)
    def test_same_user_gets_consistent_result(
        self, user_id: str, percentage: float
    ) -> None:
        """**Property 3: Feature Flag Evaluation Consistency**
        
        *For any* user ID and any percentage rollout, multiple evaluations 
        of the same flag should return the same result.
        
        **Feature: application-services-integration, Property 3: Feature Flag Evaluation Consistency**
        **Validates: Requirements 3.2**
        """
        service = FeatureFlagService(seed=42)
        flag = FlagConfig(
            key="test-consistency-flag",
            status=FlagStatus.PERCENTAGE,
            percentage=percentage,
        )
        service.register_flag(flag)
        
        context = EvaluationContext(user_id=user_id)
        
        # Evaluate multiple times
        results = [service.is_enabled("test-consistency-flag", context) for _ in range(10)]
        
        # All results should be identical
        assert len(set(results)) == 1, f"Inconsistent results for user {user_id}: {results}"

    @given(
        user_id=user_ids(),
    )
    @settings(max_examples=100)
    def test_100_percent_always_enabled(self, user_id: str) -> None:
        """100% rollout should always be enabled for any user.
        
        **Feature: application-services-integration, Property 3: Feature Flag Evaluation Consistency**
        **Validates: Requirements 3.2**
        """
        service = FeatureFlagService()
        flag = FlagConfig(
            key="always-on-flag",
            status=FlagStatus.PERCENTAGE,
            percentage=100.0,
        )
        service.register_flag(flag)
        
        context = EvaluationContext(user_id=user_id)
        assert service.is_enabled("always-on-flag", context) is True

    @given(
        user_id=user_ids(),
    )
    @settings(max_examples=100)
    def test_0_percent_always_disabled(self, user_id: str) -> None:
        """0% rollout should always be disabled for any user.
        
        **Feature: application-services-integration, Property 3: Feature Flag Evaluation Consistency**
        **Validates: Requirements 3.2**
        """
        service = FeatureFlagService()
        flag = FlagConfig(
            key="always-off-flag",
            status=FlagStatus.PERCENTAGE,
            percentage=0.0,
        )
        service.register_flag(flag)
        
        context = EvaluationContext(user_id=user_id)
        assert service.is_enabled("always-off-flag", context) is False
