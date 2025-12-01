"""Cloud provider IP ranges and providers.

**Feature: shared-modules-refactoring**
**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 9.1, 9.2, 9.3**
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network, ip_address, ip_network
from typing import Protocol, Self, Union

from .enums import CloudProvider

logger = logging.getLogger(__name__)

IPNetwork = Union[IPv4Network, IPv6Network]

# Sample IP ranges for common cloud providers
DEFAULT_CLOUD_RANGES: dict[CloudProvider, list[str]] = {
    CloudProvider.AWS: [
        "3.0.0.0/8", "13.0.0.0/8", "15.0.0.0/8", "18.0.0.0/8",
        "35.0.0.0/8", "52.0.0.0/8", "54.0.0.0/8", "99.0.0.0/8",
    ],
    CloudProvider.GCP: [
        "34.0.0.0/8", "35.0.0.0/8", "104.196.0.0/14",
        "130.211.0.0/16", "142.250.0.0/15",
    ],
    CloudProvider.AZURE: [
        "13.64.0.0/11", "20.0.0.0/8", "40.64.0.0/10",
        "51.0.0.0/8", "52.224.0.0/11", "104.40.0.0/13",
    ],
    CloudProvider.DIGITALOCEAN: [
        "64.225.0.0/16", "134.209.0.0/16", "138.68.0.0/16",
        "139.59.0.0/16", "142.93.0.0/16", "157.245.0.0/16",
    ],
    CloudProvider.CLOUDFLARE: [
        "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22",
        "104.16.0.0/13", "104.24.0.0/14", "108.162.192.0/18",
        "131.0.72.0/22", "141.101.64.0/18", "162.158.0.0/15",
        "172.64.0.0/13", "173.245.48.0/20", "188.114.96.0/20",
    ],
}

# Sample IPv6 ranges
DEFAULT_IPV6_RANGES: dict[CloudProvider, list[str]] = {
    CloudProvider.AWS: [
        "2600:1f00::/24",
        "2600:1ff0::/24",
    ],
    CloudProvider.GCP: [
        "2600:1900::/28",
    ],
    CloudProvider.CLOUDFLARE: [
        "2400:cb00::/32",
        "2606:4700::/32",
        "2803:f800::/32",
    ],
}


class CloudRangeSource(Protocol):
    """Protocol for external cloud IP range data sources."""

    async def fetch_ranges(self, provider: CloudProvider) -> list[str]:
        """Fetch IP ranges for a cloud provider from external source."""
        ...

    def get_last_update(self) -> datetime | None:
        """Get the timestamp of the last successful update."""
        ...


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
    """In-memory cloud IP range provider with IPv4 and IPv6 support.

    Supports loading ranges from external sources and deduplication
    when merging ranges.
    """

    _ipv4_ranges: dict[CloudProvider, list[IPv4Network]] = field(default_factory=dict)
    _ipv6_ranges: dict[CloudProvider, list[IPv6Network]] = field(default_factory=dict)
    _last_update: datetime | None = field(default=None, init=False)
    _initialized: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        """Initialize with default ranges if empty."""
        if not self._ipv4_ranges:
            self._load_default_ranges()

    def _load_default_ranges(self) -> None:
        """Load default cloud provider ranges."""
        for provider, cidrs in DEFAULT_CLOUD_RANGES.items():
            networks: list[IPv4Network] = []
            for cidr in cidrs:
                try:
                    networks.append(ip_network(cidr, strict=False))
                except ValueError:
                    continue
            self._ipv4_ranges[provider] = networks

        for provider, cidrs in DEFAULT_IPV6_RANGES.items():
            networks_v6: list[IPv6Network] = []
            for cidr in cidrs:
                try:
                    networks_v6.append(ip_network(cidr, strict=False))
                except ValueError:
                    continue
            self._ipv6_ranges[provider] = networks_v6

        self._last_update = datetime.now(UTC)
        self._initialized = True

    def add_range(self, provider: CloudProvider, cidr: str) -> Self:
        """Add a CIDR range for a provider with deduplication."""
        try:
            network = ip_network(cidr, strict=False)
        except ValueError:
            return self

        if isinstance(network, IPv4Network):
            if provider not in self._ipv4_ranges:
                self._ipv4_ranges[provider] = []
            # Deduplicate
            if network not in self._ipv4_ranges[provider]:
                self._ipv4_ranges[provider].append(network)
        else:
            if provider not in self._ipv6_ranges:
                self._ipv6_ranges[provider] = []
            # Deduplicate
            if network not in self._ipv6_ranges[provider]:
                self._ipv6_ranges[provider].append(network)

        self._last_update = datetime.now(UTC)
        return self

    def merge_ranges(self, provider: CloudProvider, cidrs: list[str]) -> Self:
        """Merge multiple CIDR ranges for a provider without duplicates."""
        for cidr in cidrs:
            self.add_range(provider, cidr)
        return self

    def get_ranges(self, provider: CloudProvider) -> list[IPv4Network]:
        """Get IPv4 ranges for a cloud provider."""
        return self._ipv4_ranges.get(provider, [])

    def get_ipv6_ranges(self, provider: CloudProvider) -> list[IPv6Network]:
        """Get IPv6 ranges for a cloud provider."""
        return self._ipv6_ranges.get(provider, [])

    def identify_provider(self, ip: str) -> CloudProvider | None:
        """Identify which cloud provider owns an IP (IPv4 or IPv6).

        Returns None for invalid IP addresses without raising exceptions.
        """
        try:
            addr = ip_address(ip)
        except ValueError:
            return None

        if isinstance(addr, IPv4Address):
            for provider, networks in self._ipv4_ranges.items():
                for network in networks:
                    if addr in network:
                        return provider
        elif isinstance(addr, IPv6Address):
            for provider, networks in self._ipv6_ranges.items():
                for network in networks:
                    if addr in network:
                        return provider

        return None

    def get_network_for_ip(self, ip: str) -> tuple[CloudProvider, IPNetwork] | None:
        """Get the provider and network containing an IP."""
        try:
            addr = ip_address(ip)
        except ValueError:
            return None

        if isinstance(addr, IPv4Address):
            for provider, networks in self._ipv4_ranges.items():
                for network in networks:
                    if addr in network:
                        return (provider, network)
        elif isinstance(addr, IPv6Address):
            for provider, networks in self._ipv6_ranges.items():
                for network in networks:
                    if addr in network:
                        return (provider, network)

        return None

    def get_last_update(self) -> datetime | None:
        """Get the timestamp of the last update."""
        return self._last_update

    def is_stale(self, max_age: timedelta = timedelta(hours=24)) -> bool:
        """Check if the ranges are stale (older than max_age)."""
        if self._last_update is None:
            return True
        age = datetime.now(UTC) - self._last_update
        return age > max_age

    def check_staleness_warning(self) -> None:
        """Log a warning if ranges are stale."""
        if self.is_stale():
            logger.warning(
                "Cloud provider IP ranges are stale",
                extra={
                    "last_update": self._last_update.isoformat() if self._last_update else None,
                    "max_age_hours": 24,
                },
            )


@dataclass
class UpdatableCloudRangeProvider:
    """Cloud range provider that supports dynamic updates from external sources."""

    _base_provider: InMemoryCloudRangeProvider = field(
        default_factory=InMemoryCloudRangeProvider
    )
    _sources: list[CloudRangeSource] = field(default_factory=list)
    _update_interval: timedelta = field(default_factory=lambda: timedelta(hours=24))
    _last_fetch: datetime | None = field(default=None, init=False)

    def add_source(self, source: CloudRangeSource) -> Self:
        """Add an external range source."""
        self._sources.append(source)
        return self

    async def update_from_sources(self) -> bool:
        """Update ranges from all external sources.

        Returns True if any source was successfully fetched.
        """
        success = False
        for source in self._sources:
            try:
                for provider in CloudProvider:
                    ranges = await source.fetch_ranges(provider)
                    if ranges:
                        self._base_provider.merge_ranges(provider, ranges)
                        success = True
            except Exception as e:
                logger.warning(
                    "Failed to fetch ranges from source",
                    extra={"error": str(e)},
                )
                # Fall back to cached ranges - continue with other sources

        if success:
            self._last_fetch = datetime.now(UTC)

        return success

    def get_ranges(self, provider: CloudProvider) -> list[IPv4Network]:
        """Get IPv4 ranges for a cloud provider."""
        self._base_provider.check_staleness_warning()
        return self._base_provider.get_ranges(provider)

    def get_ipv6_ranges(self, provider: CloudProvider) -> list[IPv6Network]:
        """Get IPv6 ranges for a cloud provider."""
        return self._base_provider.get_ipv6_ranges(provider)

    def identify_provider(self, ip: str) -> CloudProvider | None:
        """Identify which cloud provider owns an IP."""
        return self._base_provider.identify_provider(ip)

    def get_network_for_ip(self, ip: str) -> tuple[CloudProvider, IPNetwork] | None:
        """Get the provider and network containing an IP."""
        return self._base_provider.get_network_for_ip(ip)
