"""Cloud Provider IP Filtering.

Provides filtering to block or allow requests from cloud provider IP ranges
(AWS, GCP, Azure, DigitalOcean, etc.) to protect against automated bots.

**Feature: api-architecture-analysis, Task 6.3: Cloud Provider Blocking**
**Validates: Requirements 5.3**

Usage:
    from my_api.shared.cloud_provider_filter import (
        CloudProvider,
        CloudProviderFilter,
        CloudProviderConfig,
    )

    config = CloudProviderConfig(blocked_providers={CloudProvider.AWS, CloudProvider.GCP})
    filter = CloudProviderFilter(config)
    result = await filter.check("52.94.76.1")
"""

from dataclasses import dataclass, field
from enum import Enum
from ipaddress import IPv4Address, IPv4Network, ip_address, ip_network
from typing import Protocol, Self

from pydantic import BaseModel


class CloudProvider(str, Enum):
    """Known cloud providers."""

    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    DIGITALOCEAN = "digitalocean"
    LINODE = "linode"
    VULTR = "vultr"
    OVH = "ovh"
    HETZNER = "hetzner"
    ORACLE = "oracle"
    IBM = "ibm"
    ALIBABA = "alibaba"
    CLOUDFLARE = "cloudflare"
    UNKNOWN = "unknown"


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


# Sample IP ranges for common cloud providers (simplified for demo)
# In production, these would be fetched from official sources
DEFAULT_CLOUD_RANGES: dict[CloudProvider, list[str]] = {
    CloudProvider.AWS: [
        "3.0.0.0/8",
        "13.0.0.0/8",
        "15.0.0.0/8",
        "18.0.0.0/8",
        "35.0.0.0/8",
        "52.0.0.0/8",
        "54.0.0.0/8",
        "99.0.0.0/8",
    ],
    CloudProvider.GCP: [
        "34.0.0.0/8",
        "35.0.0.0/8",
        "104.196.0.0/14",
        "130.211.0.0/16",
        "142.250.0.0/15",
    ],
    CloudProvider.AZURE: [
        "13.64.0.0/11",
        "20.0.0.0/8",
        "40.64.0.0/10",
        "51.0.0.0/8",
        "52.224.0.0/11",
        "104.40.0.0/13",
    ],
    CloudProvider.DIGITALOCEAN: [
        "64.225.0.0/16",
        "134.209.0.0/16",
        "138.68.0.0/16",
        "139.59.0.0/16",
        "142.93.0.0/16",
        "157.245.0.0/16",
        "159.65.0.0/16",
        "159.89.0.0/16",
        "161.35.0.0/16",
        "164.90.0.0/16",
        "165.22.0.0/16",
        "167.71.0.0/16",
        "167.172.0.0/16",
        "178.128.0.0/16",
        "188.166.0.0/16",
        "206.189.0.0/16",
    ],
    CloudProvider.LINODE: [
        "45.33.0.0/16",
        "45.56.0.0/16",
        "45.79.0.0/16",
        "50.116.0.0/16",
        "66.175.208.0/20",
        "69.164.192.0/18",
        "72.14.176.0/20",
        "74.207.224.0/19",
        "96.126.96.0/19",
        "97.107.128.0/17",
        "139.162.0.0/16",
        "172.104.0.0/15",
        "173.230.128.0/17",
        "173.255.192.0/18",
        "178.79.128.0/17",
        "192.155.80.0/20",
        "198.58.96.0/19",
        "198.74.48.0/20",
    ],
    CloudProvider.VULTR: [
        "45.32.0.0/16",
        "45.63.0.0/16",
        "45.76.0.0/16",
        "45.77.0.0/16",
        "64.156.0.0/16",
        "66.42.0.0/16",
        "78.141.192.0/18",
        "95.179.128.0/17",
        "104.156.224.0/19",
        "104.207.128.0/17",
        "108.61.0.0/16",
        "136.244.64.0/18",
        "140.82.0.0/16",
        "144.202.0.0/16",
        "149.28.0.0/16",
        "155.138.128.0/17",
        "207.148.0.0/17",
        "209.250.224.0/19",
        "216.128.128.0/17",
        "217.69.0.0/16",
    ],
    CloudProvider.HETZNER: [
        "5.9.0.0/16",
        "23.88.0.0/16",
        "46.4.0.0/16",
        "78.46.0.0/15",
        "88.198.0.0/16",
        "88.99.0.0/16",
        "94.130.0.0/16",
        "95.216.0.0/15",
        "116.202.0.0/16",
        "116.203.0.0/16",
        "128.140.0.0/16",
        "135.181.0.0/16",
        "136.243.0.0/16",
        "138.201.0.0/16",
        "142.132.128.0/17",
        "144.76.0.0/16",
        "148.251.0.0/16",
        "157.90.0.0/16",
        "159.69.0.0/16",
        "162.55.0.0/16",
        "167.233.0.0/16",
        "168.119.0.0/16",
        "176.9.0.0/16",
        "178.63.0.0/16",
        "188.40.0.0/16",
        "195.201.0.0/16",
        "213.133.96.0/19",
        "213.239.192.0/18",
    ],
    CloudProvider.OVH: [
        "5.39.0.0/16",
        "5.135.0.0/16",
        "5.196.0.0/16",
        "37.59.0.0/16",
        "37.187.0.0/16",
        "46.105.0.0/16",
        "51.38.0.0/16",
        "51.68.0.0/16",
        "51.75.0.0/16",
        "51.77.0.0/16",
        "51.79.0.0/16",
        "51.83.0.0/16",
        "51.89.0.0/16",
        "51.91.0.0/16",
        "51.161.0.0/16",
        "51.178.0.0/16",
        "51.195.0.0/16",
        "51.210.0.0/16",
        "51.254.0.0/16",
        "54.36.0.0/16",
        "54.37.0.0/16",
        "54.38.0.0/16",
        "57.128.0.0/16",
        "91.121.0.0/16",
        "92.222.0.0/16",
        "135.125.0.0/16",
        "137.74.0.0/16",
        "139.99.0.0/16",
        "141.94.0.0/16",
        "141.95.0.0/16",
        "142.4.192.0/18",
        "144.217.0.0/16",
        "145.239.0.0/16",
        "147.135.0.0/16",
        "149.56.0.0/16",
        "151.80.0.0/16",
        "158.69.0.0/16",
        "162.19.0.0/16",
        "164.132.0.0/16",
        "167.114.0.0/16",
        "176.31.0.0/16",
        "178.32.0.0/16",
        "185.12.32.0/22",
        "188.165.0.0/16",
        "192.95.0.0/16",
        "192.99.0.0/16",
        "193.70.0.0/16",
        "198.27.64.0/18",
        "198.50.128.0/17",
        "198.100.144.0/20",
        "198.245.48.0/20",
        "213.186.32.0/19",
        "213.251.128.0/17",
    ],
    CloudProvider.CLOUDFLARE: [
        "103.21.244.0/22",
        "103.22.200.0/22",
        "103.31.4.0/22",
        "104.16.0.0/13",
        "104.24.0.0/14",
        "108.162.192.0/18",
        "131.0.72.0/22",
        "141.101.64.0/18",
        "162.158.0.0/15",
        "172.64.0.0/13",
        "173.245.48.0/20",
        "188.114.96.0/20",
        "190.93.240.0/20",
        "197.234.240.0/22",
        "198.41.128.0/17",
    ],
}


@dataclass
class CloudProviderConfig:
    """Configuration for cloud provider filtering."""

    blocked_providers: set[CloudProvider] = field(default_factory=set)
    allowed_providers: set[CloudProvider] = field(default_factory=set)
    allowed_ips: set[str] = field(default_factory=set)
    blocked_ips: set[str] = field(default_factory=set)
    block_all_cloud: bool = False
    allow_cloudflare: bool = True  # Often used as CDN, not bot
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


class CloudIPRangeProvider(Protocol):
    """Protocol for cloud IP range data providers."""

    def get_ranges(self, provider: CloudProvider) -> list[IPv4Network]:
        """Get IP ranges for a cloud provider."""
        ...

    def identify_provider(self, ip: str) -> CloudProvider | None:
        """Identify which cloud provider owns an IP."""
        ...


@dataclass
class InMemoryCloudRangeProvider:
    """In-memory cloud IP range provider."""

    _ranges: dict[CloudProvider, list[IPv4Network]] = field(default_factory=dict)
    _initialized: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        """Initialize with default ranges if empty."""
        if not self._ranges:
            self._load_default_ranges()

    def _load_default_ranges(self) -> None:
        """Load default cloud provider ranges."""
        for provider, cidrs in DEFAULT_CLOUD_RANGES.items():
            networks = []
            for cidr in cidrs:
                try:
                    networks.append(ip_network(cidr, strict=False))
                except ValueError:
                    continue
            self._ranges[provider] = networks
        self._initialized = True

    def add_range(self, provider: CloudProvider, cidr: str) -> Self:
        """Add a CIDR range for a provider."""
        if provider not in self._ranges:
            self._ranges[provider] = []
        try:
            self._ranges[provider].append(ip_network(cidr, strict=False))
        except ValueError:
            pass
        return self

    def get_ranges(self, provider: CloudProvider) -> list[IPv4Network]:
        """Get IP ranges for a cloud provider."""
        return self._ranges.get(provider, [])

    def identify_provider(self, ip: str) -> CloudProvider | None:
        """Identify which cloud provider owns an IP."""
        try:
            addr = ip_address(ip)
        except ValueError:
            return None

        for provider, networks in self._ranges.items():
            for network in networks:
                if addr in network:
                    return provider
        return None

    def get_network_for_ip(self, ip: str) -> tuple[CloudProvider, IPv4Network] | None:
        """Get the provider and network containing an IP."""
        try:
            addr = ip_address(ip)
        except ValueError:
            return None

        for provider, networks in self._ranges.items():
            for network in networks:
                if addr in network:
                    return (provider, network)
        return None


@dataclass
class CloudProviderFilter:
    """Filter for blocking cloud provider IPs."""

    config: CloudProviderConfig
    range_provider: CloudIPRangeProvider = field(
        default_factory=InMemoryCloudRangeProvider
    )

    async def check(self, ip: str) -> CloudProviderResult:
        """Check if an IP should be blocked based on cloud provider.

        Args:
            ip: IP address to check.

        Returns:
            CloudProviderResult indicating if access is allowed.
        """
        # Check IP allowlist first
        if ip in self.config.allowed_ips:
            return CloudProviderResult.allow()

        # Check IP blocklist
        if ip in self.config.blocked_ips:
            info = CloudProviderInfo(ip=ip, provider=CloudProvider.UNKNOWN)
            return CloudProviderResult.block("IP is in blocklist", info)

        # Identify provider
        provider = self.range_provider.identify_provider(ip)

        # Not a cloud IP
        if provider is None:
            return CloudProviderResult.allow()

        # Get network info
        network_info = self.range_provider.get_network_for_ip(ip)
        network_str = str(network_info[1]) if network_info else None

        info = CloudProviderInfo(
            ip=ip,
            provider=provider,
            network=network_str,
        )

        # Special handling for Cloudflare (often CDN, not bot)
        if provider == CloudProvider.CLOUDFLARE and self.config.allow_cloudflare:
            return CloudProviderResult.allow(info)

        # Check if provider is in allowlist
        if self.config.allowed_providers and provider in self.config.allowed_providers:
            return CloudProviderResult.allow(info)

        # Block all cloud providers
        if self.config.block_all_cloud:
            return CloudProviderResult.block(
                f"Cloud provider {provider.value} is blocked (block_all_cloud)",
                info,
            )

        # Check if provider is in blocklist
        if provider in self.config.blocked_providers:
            return CloudProviderResult.block(
                f"Cloud provider {provider.value} is blocked",
                info,
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
        """Initialize builder."""
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


__all__ = [
    "CloudIPRangeProvider",
    "CloudProvider",
    "CloudProviderConfig",
    "CloudProviderFilter",
    "CloudProviderFilterBuilder",
    "CloudProviderInfo",
    "CloudProviderResult",
    "DEFAULT_CLOUD_RANGES",
    "InMemoryCloudRangeProvider",
    "create_cloud_filter",
]
