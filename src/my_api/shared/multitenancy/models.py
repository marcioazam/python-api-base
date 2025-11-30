"""multitenancy models."""

from dataclasses import dataclass


@dataclass
class TenantContext:
    """Context manager for tenant scope.

    Automatically sets and clears the tenant context.

    Usage:
        async with TenantContext("tenant_123"):
            # All operations use tenant_123
            items = await repo.get_all()
    """

    tenant_id: str

    def __enter__(self) -> "TenantContext":
        """Enter tenant context."""
        self._previous = get_current_tenant()
        set_current_tenant(self.tenant_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit tenant context and restore previous."""
        set_current_tenant(self._previous)

    async def __aenter__(self) -> "TenantContext":
        """Async enter tenant context."""
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async exit tenant context."""
        self.__exit__(exc_type, exc_val, exc_tb)
