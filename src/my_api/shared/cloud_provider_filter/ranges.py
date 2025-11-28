"""Cloud provider IP ranges and providers."""

from dataclasses import dataclass, field
from ipaddress import IPv4Network, ip_address, ip_network
from typing import Protocol, Self

from .enums import CloudProvider


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
