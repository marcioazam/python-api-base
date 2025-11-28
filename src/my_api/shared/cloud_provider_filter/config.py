"""Cloud provider filter configuration."""

from dataclasses import dataclass, field
from typing import Self

from .enums import CloudProvider


@dataclass
class CloudProviderConfig:
    """Configuration for cloud provider filtering."""

    blocked_providers: set[CloudProvider] = field(default_factory=set)
    allowed_providers: set[CloudProvider] = field(default_factory=set)
    allowed_ips: set[str] = field(default_factory=set)
    blocked_ips: set[str] = field(default_factory=set)
    block_all_cloud: bool = False
    allow_cloudflare: bool = True
    log_blocked: bool = True

    def with_blocked_providers(self, *providers: CloudProvider) -> Self:
        """Add providers to blocklist."""
        self.blocked_providers.update(providers)
        return self

    def with_allowed_providers(self, *providers: CloudProvider) -> Self:
        """Add providers to allowlist."""
        self.allowed_providers.update(providers)
        return self

    def with_allowed_ips(self, *ips: str) -> Self:
        """Add IPs to allowlist."""
        self.allowed_ips.update(ips)
        return self
