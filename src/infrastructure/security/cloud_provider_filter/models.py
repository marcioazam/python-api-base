"""Cloud provider filter models."""

from pydantic import BaseModel

from .enums import CloudProvider


class CloudProviderInfo(BaseModel):
    """Information about a cloud provider match."""

    ip: str
    provider: CloudProvider
    network: str | None = None
    region: str | None = None
    service: str | None = None
    is_blocked: bool = False


class CloudProviderResult(BaseModel):
    """Result of cloud provider check."""

    allowed: bool
    reason: str | None = None
    info: CloudProviderInfo | None = None

    @classmethod
    def allow(cls, info: CloudProviderInfo | None = None) -> "CloudProviderResult":
        """Create allow result."""
        return cls(allowed=True, info=info)

    @classmethod
    def block(
        cls, reason: str, info: CloudProviderInfo | None = None
    ) -> "CloudProviderResult":
        """Create block result."""
        if info:
            info.is_blocked = True
        return cls(allowed=False, reason=reason, info=info)
