"""Cloud provider filter implementation."""

from dataclasses import dataclass, field
from typing import Self

from .config import CloudProviderConfig
from .enums import CloudProvider
from .models import CloudProviderInfo, CloudProviderResult
from .ranges import CloudIPRangeProvider, InMemoryCloudRangeProvider


@dataclass
class CloudProviderFilter:
    """Filter for blocking cloud provider IPs."""

    config: CloudProviderConfig
    range_provider: CloudIPRangeProvider = field(
        default_factory=InMemoryCloudRangeProvider
    )

    async def check(self, ip: str) -> CloudProviderResult:
        """Check if an IP should be blocked based on cloud provider."""
        if ip in self.config.allowed_ips:
            return CloudProviderResult.allow()

        if ip in self.config.blocked_ips:
            info = CloudProviderInfo(ip=ip, provider=CloudProvider.UNKNOWN)
            return CloudProviderResult.block("IP is in blocklist", info)

        provider = self.range_provider.identify_provider(ip)

        if provider is None:
            return CloudProviderResult.allow()

        network_info = self.range_provider.get_network_for_ip(ip)
        network_str = str(network_info[1]) if network_info else None

        info = CloudProviderInfo(ip=ip, provider=provider, network=network_str)

        if provider == CloudProvider.CLOUDFLARE and self.config.allow_cloudflare:
            return CloudProviderResult.allow(info)

        if self.config.allowed_providers and provider in self.config.allowed_providers:
            return CloudProviderResult.allow(info)

        if self.config.block_all_cloud:
            return CloudProviderResult.block(
                f"Cloud provider {provider.value} is blocked (block_all_cloud)", info
            )

        if provider in self.config.blocked_providers:
            return CloudProviderResult.block(
                f"Cloud provider {provider.value} is blocked", info
            )

        return CloudProviderResult.allow(info)

    def is_cloud_ip(self, ip: str) -> bool:
        """Check if an IP belongs to any cloud provider."""
        return self.range_provider.identify_provider(ip) is not None

    def get_provider(self, ip: str) -> CloudProvider | None:
        """Get the cloud provider for an IP."""
        return self.range_provider.identify_provider(ip)


class CloudProviderFilterBuilder:
    """Fluent builder for CloudProviderFilter."""

    def __init__(self) -> None:
        self._config = CloudProviderConfig()
        self._range_provider: CloudIPRangeProvider | None = None

    def block_providers(self, *providers: CloudProvider) -> Self:
        """Block specific cloud providers."""
        self._config.blocked_providers.update(providers)
        return self

    def allow_providers(self, *providers: CloudProvider) -> Self:
        """Allow specific cloud providers."""
        self._config.allowed_providers.update(providers)
        return self

    def block_all_cloud(self, block: bool = True) -> Self:
        """Block all cloud provider IPs."""
        self._config.block_all_cloud = block
        return self

    def allow_cloudflare(self, allow: bool = True) -> Self:
        """Allow Cloudflare IPs (CDN)."""
        self._config.allow_cloudflare = allow
        return self

    def allow_ips(self, *ips: str) -> Self:
        """Add IPs to allowlist."""
        self._config.allowed_ips.update(ips)
        return self

    def block_ips(self, *ips: str) -> Self:
        """Add IPs to blocklist."""
        self._config.blocked_ips.update(ips)
        return self

    def with_range_provider(self, provider: CloudIPRangeProvider) -> Self:
        """Set custom range provider."""
        self._range_provider = provider
        return self

    def build(self) -> CloudProviderFilter:
        """Build the filter."""
        return CloudProviderFilter(
            config=self._config,
            range_provider=self._range_provider or InMemoryCloudRangeProvider(),
        )


def create_cloud_filter(
    block_providers: set[CloudProvider] | None = None,
    block_all: bool = False,
) -> CloudProviderFilter:
    """Create a cloud provider filter with common defaults."""
    config = CloudProviderConfig(
        blocked_providers=block_providers or set(),
        block_all_cloud=block_all,
    )
    return CloudProviderFilter(config=config)
