"""Property-based tests for multi-tenancy support.

**Feature: api-architecture-analysis, Task 3.3: Multi-tenancy Support**
**Validates: Requirements 2.1**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from my_app.application.multitenancy import (
    TenantContext,
    get_current_tenant,
    set_current_tenant,
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


# =============================================================================
# Property 1: Tenant Context Round-Trip
# =============================================================================


@given(tenant_id=tenant_ids())
@settings(max_examples=100)
def test_set_get_tenant_round_trip(tenant_id: str) -> None:
    """Property: set then get returns same tenant ID.

    **Feature: api-architecture-analysis, Property 1: Tenant Context Round-Trip**
    **Validates: Requirements 2.1**

    For any tenant ID, setting it and then getting it should
    return the same value.
    """
    # Clear any existing context
    set_current_tenant(None)

    set_current_tenant(tenant_id)
    result = get_current_tenant()

    assert result == tenant_id

    # Cleanup
    set_current_tenant(None)


@given(tenant_id=tenant_ids())
@settings(max_examples=100)
def test_tenant_context_manager_sets_tenant(tenant_id: str) -> None:
    """Property: TenantContext sets tenant during scope.

    **Feature: api-architecture-analysis, Property 2: Context Manager Sets Tenant**
    **Validates: Requirements 2.1**

    Within a TenantContext, get_current_tenant should return
    the context's tenant ID.
    """
    # Clear any existing context
    set_current_tenant(None)

    with TenantContext(tenant_id):
        result = get_current_tenant()
        assert result == tenant_id

    # Cleanup
    set_current_tenant(None)


@given(tenant_id=tenant_ids())
@settings(max_examples=100)
def test_tenant_context_restores_previous(tenant_id: str) -> None:
    """Property: TenantContext restores previous tenant on exit.

    **Feature: api-architecture-analysis, Property 3: Context Restores Previous**
    **Validates: Requirements 2.1**

    After exiting a TenantContext, the previous tenant should
    be restored.
    """
    # Clear any existing context
    set_current_tenant(None)

    # Verify None before
    assert get_current_tenant() is None

    with TenantContext(tenant_id):
        assert get_current_tenant() == tenant_id

    # Should be None after
    assert get_current_tenant() is None


@given(
    outer_tenant=tenant_ids(),
    inner_tenant=tenant_ids(),
)
@settings(max_examples=100)
def test_nested_tenant_contexts(outer_tenant: str, inner_tenant: str) -> None:
    """Property: nested TenantContexts work correctly.

    **Feature: api-architecture-analysis, Property 4: Nested Contexts**
    **Validates: Requirements 2.1**

    Nested TenantContexts should properly set and restore
    tenant IDs at each level.
    """
    # Clear any existing context
    set_current_tenant(None)

    with TenantContext(outer_tenant):
        assert get_current_tenant() == outer_tenant

        with TenantContext(inner_tenant):
            assert get_current_tenant() == inner_tenant

        # Should restore outer
        assert get_current_tenant() == outer_tenant

    # Should restore None
    assert get_current_tenant() is None


# =============================================================================
# Property 2: Tenant Isolation
# =============================================================================


@given(
    tenant_ids_list=st.lists(tenant_ids(), min_size=2, max_size=5, unique=True)
)
@settings(max_examples=100)
def test_tenant_contexts_are_isolated(tenant_ids_list: list[str]) -> None:
    """Property: different tenant contexts are isolated.

    **Feature: api-architecture-analysis, Property 5: Tenant Isolation**
    **Validates: Requirements 2.1**

    Each TenantContext should only see its own tenant ID.
    """
    # Clear any existing context
    set_current_tenant(None)

    for tenant_id in tenant_ids_list:
        with TenantContext(tenant_id):
            # Should only see current tenant
            assert get_current_tenant() == tenant_id
            # Should not see other tenants
            for other_id in tenant_ids_list:
                if other_id != tenant_id:
                    assert get_current_tenant() != other_id


# =============================================================================
# Property 3: Clear Tenant
# =============================================================================


@given(tenant_id=tenant_ids())
@settings(max_examples=100)
def test_set_none_clears_tenant(tenant_id: str) -> None:
    """Property: setting None clears tenant context.

    **Feature: api-architecture-analysis, Property 6: Clear Tenant**
    **Validates: Requirements 2.1**

    Setting tenant to None should clear the context.
    """
    set_current_tenant(tenant_id)
    assert get_current_tenant() == tenant_id

    set_current_tenant(None)
    assert get_current_tenant() is None


# =============================================================================
# Property 4: Async Context Manager
# =============================================================================


@given(tenant_id=tenant_ids())
@settings(max_examples=100)
def test_async_tenant_context(tenant_id: str) -> None:
    """Property: async TenantContext works correctly.

    **Feature: api-architecture-analysis, Property 7: Async Context**
    **Validates: Requirements 2.1**

    TenantContext should work with async context manager protocol.
    """
    import asyncio

    async def test_async():
        set_current_tenant(None)

        async with TenantContext(tenant_id):
            assert get_current_tenant() == tenant_id

        assert get_current_tenant() is None

    asyncio.get_event_loop().run_until_complete(test_async())


# =============================================================================
# Property 5: Tenant ID Types
# =============================================================================


@given(tenant_id=st.text(min_size=1, max_size=100))
@settings(max_examples=100)
def test_tenant_id_preserves_string(tenant_id: str) -> None:
    """Property: tenant ID preserves string value exactly.

    **Feature: api-architecture-analysis, Property 8: String Preservation**
    **Validates: Requirements 2.1**

    The tenant ID should be preserved exactly as set.
    """
    set_current_tenant(None)
    set_current_tenant(tenant_id)

    result = get_current_tenant()
    assert result == tenant_id
    assert type(result) is str

    set_current_tenant(None)


# =============================================================================
# Property 6: Context Independence
# =============================================================================


@given(
    tenant1=tenant_ids(),
    tenant2=tenant_ids(),
)
@settings(max_examples=100)
def test_sequential_contexts_independent(tenant1: str, tenant2: str) -> None:
    """Property: sequential contexts are independent.

    **Feature: api-architecture-analysis, Property 9: Sequential Independence**
    **Validates: Requirements 2.1**

    Sequential TenantContexts should not affect each other.
    """
    set_current_tenant(None)

    # First context
    with TenantContext(tenant1):
        assert get_current_tenant() == tenant1

    # Between contexts
    assert get_current_tenant() is None

    # Second context
    with TenantContext(tenant2):
        assert get_current_tenant() == tenant2

    # After all contexts
    assert get_current_tenant() is None
