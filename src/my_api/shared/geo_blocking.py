"""IP Geolocation Blocking middleware and utilities.

Provides IP-based geolocation blocking to restrict access by country/region,
with support for allowlists, blocklists, and configurable providers.

**Feature: api-architecture-analysis, Task 6.2: IP Geolocation Blocking**
**Validates: Requirements 5.3**

Usage:
    from my_api.shared.geo_blocking import (
        GeoBlockConfig,
        GeoBlockMiddleware,
        GeoLocation,
        InMemoryGeoProvider,
    )

    config = GeoBlockConfig(
        blocked_countries=["CN", "RU"],
        allowed_countries=["US", "BR", "GB"],
    )
    middleware = GeoBlockMiddleware(config)
"""

from dataclasses import dataclass, field
from enum import Enum
from ipaddress import ip_address
from typing import Protocol, Self

from pydantic import BaseModel


class BlockMode(str, Enum):
    """Mode for geo blocking behavior."""

    ALLOWLIST = "allowlist"  # Only allow listed countries
    BLOCKLIST = "blocklist"  # Block listed countries
    DISABLED = "disabled"  # No blocking


class GeoLocation(BaseModel):
    """Geographic location information for an IP address."""

    ip: str
    country_code: str | None = None
    country_name: str | None = None
    region_code: str | None = None
    region_name: str | None = None
    city: str | None = None
    postal_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None
    isp: str | None = None
    organization: str | None = None
    is_proxy: bool = False
    is_vpn: bool = False
    is_tor: bool = False
    is_datacenter: bool = False

    @property
    def is_anonymous(self) -> bool:
        """Check if IP is using anonymization."""
        return self.is_proxy or self.is_vpn or self.is_tor

    def is_in_country(self, country_codes: set[str]) -> bool:
        """Check if location is in any of the specified countries."""
        if not self.country_code:
            return False
        return self.country_code.upper() in {c.upper() for c in country_codes}

    def is_in_region(self, regions: set[str]) -> bool:
        """Check if location is in any of the specified regions."""
        if not self.region_code:
            return False
        return self.region_code.upper() in {r.upper() for r in regions}


class GeoBlockResult(BaseModel):
    """Result of a geo blocking check."""

    allowed: bool
    reason: str | None = None
    location: GeoLocation | None = None
    matched_rule: str | None = None

    @classmethod
    def allow(cls, location: GeoLocation | None = None) -> "GeoBlockResult":
        """Create an allow result."""
        return cls(allowed=True, location=location)

    @classmethod
    def block(
        cls,
        reason: str,
        location: GeoLocation | None = None,
        matched_rule: str | None = None,
    ) -> "GeoBlockResult":
        """Create a block result."""
        return cls(
            allowed=False,
            reason=reason,
            location=location,
            matched_rule=matched_rule,
        )


class GeoProvider(Protocol):
    """Protocol for geolocation data providers."""

    async def lookup(self, ip: str) -> GeoLocation | None:
        """Look up geographic location for an IP address."""
        ...


@dataclass
class GeoBlockConfig:
    """Configuration for geo blocking."""

    mode: BlockMode = BlockMode.BLOCKLIST
    blocked_countries: set[str] = field(default_factory=set)
    allowed_countries: set[str] = field(default_factory=set)
    blocked_regions: set[str] = field(default_factory=set)
    allowed_regions: set[str] = field(default_factory=set)
    blocked_cities: set[str] = field(default_factory=set)
    allowed_ips: set[str] = field(default_factory=set)
    blocked_ips: set[str] = field(default_factory=set)
    block_anonymous: bool = False
    block_datacenter: bool = False
    block_unknown: bool = False
    log_blocked: bool = True
    custom_block_message: str | None = None

    def with_blocked_countries(self, *countries: str) -> Self:
        """Add countries to blocklist."""
        self.blocked_countries.update(c.upper() for c in countries)
        return self

    def with_allowed_countries(self, *countries: str) -> Self:
        """Add countries to allowlist."""
        self.allowed_countries.update(c.upper() for c in countries)
        return self

    def with_blocked_ips(self, *ips: str) -> Self:
        """Add IPs to blocklist."""
        self.blocked_ips.update(ips)
        return self

    def with_allowed_ips(self, *ips: str) -> Self:
        """Add IPs to allowlist."""
        self.allowed_ips.update(ips)
        return self


@dataclass
class InMemoryGeoProvider:
    """In-memory geo provider for testing and development."""

    _data: dict[str, GeoLocation] = field(default_factory=dict)
    default_country: str = "US"

    def add_location(self, ip: str, location: GeoLocation) -> Self:
        """Add a location mapping."""
        self._data[ip] = location
        return self

    def add_country(self, ip: str, country_code: str, country_name: str = "") -> Self:
        """Add a simple country mapping."""
        self._data[ip] = GeoLocation(
            ip=ip,
            country_code=country_code.upper(),
            country_name=country_name or country_code,
        )
        return self

    async def lookup(self, ip: str) -> GeoLocation | None:
        """Look up geographic location for an IP address."""
        if ip in self._data:
            return self._data[ip]
        # Return default for private/local IPs
        if self._is_private_ip(ip):
            return GeoLocation(
                ip=ip,
                country_code=self.default_country,
                country_name="Local",
            )
        return None

    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP is private/local."""
        try:
            addr = ip_address(ip)
            return addr.is_private or addr.is_loopback or addr.is_reserved
        except ValueError:
            return False


@dataclass
class GeoBlocker:
    """Core geo blocking logic."""

    config: GeoBlockConfig
    provider: GeoProvider

    async def check(self, ip: str) -> GeoBlockResult:
        """Check if an IP should be blocked.

        Args:
            ip: IP address to check.

        Returns:
            GeoBlockResult indicating if access is allowed.
        """
        # Disabled mode - allow all
        if self.config.mode == BlockMode.DISABLED:
            return GeoBlockResult.allow()

        # Check IP allowlist first (always allowed)
        if ip in self.config.allowed_ips:
            return GeoBlockResult.allow()

        # Check IP blocklist
        if ip in self.config.blocked_ips:
            return GeoBlockResult.block(
                reason="IP address is blocked",
                matched_rule=f"blocked_ip:{ip}",
            )

        # Look up location
        location = await self.provider.lookup(ip)

        # Handle unknown location
        if location is None or location.country_code is None:
            if self.config.block_unknown:
                return GeoBlockResult.block(
                    reason="Unknown location",
                    matched_rule="block_unknown",
                )
            return GeoBlockResult.allow()

        # Check anonymous/proxy
        if self.config.block_anonymous and location.is_anonymous:
            return GeoBlockResult.block(
                reason="Anonymous proxy detected",
                location=location,
                matched_rule="block_anonymous",
            )

        # Check datacenter
        if self.config.block_datacenter and location.is_datacenter:
            return GeoBlockResult.block(
                reason="Datacenter IP detected",
                location=location,
                matched_rule="block_datacenter",
            )

        # Allowlist mode - only allow listed countries
        if self.config.mode == BlockMode.ALLOWLIST:
            if self.config.allowed_countries:
                if not location.is_in_country(self.config.allowed_countries):
                    return GeoBlockResult.block(
                        reason=f"Country {location.country_code} not in allowlist",
                        location=location,
                        matched_rule="country_allowlist",
                    )
            return GeoBlockResult.allow(location)

        # Blocklist mode - block listed countries
        if self.config.mode == BlockMode.BLOCKLIST:
            if location.is_in_country(self.config.blocked_countries):
                return GeoBlockResult.block(
                    reason=f"Country {location.country_code} is blocked",
                    location=location,
                    matched_rule=f"blocked_country:{location.country_code}",
                )

            if location.is_in_region(self.config.blocked_regions):
                return GeoBlockResult.block(
                    reason=f"Region {location.region_code} is blocked",
                    location=location,
                    matched_rule=f"blocked_region:{location.region_code}",
                )

            if location.city and location.city.lower() in {
                c.lower() for c in self.config.blocked_cities
            }:
                return GeoBlockResult.block(
                    reason=f"City {location.city} is blocked",
                    location=location,
                    matched_rule=f"blocked_city:{location.city}",
                )

        return GeoBlockResult.allow(location)


class GeoBlockConfigBuilder:
    """Fluent builder for GeoBlockConfig."""

    def __init__(self) -> None:
        """Initialize builder with default config."""
        self._config = GeoBlockConfig()

    def mode(self, mode: BlockMode) -> Self:
        """Set blocking mode."""
        self._config.mode = mode
        return self

    def allowlist_mode(self) -> Self:
        """Set to allowlist mode."""
        self._config.mode = BlockMode.ALLOWLIST
        return self

    def blocklist_mode(self) -> Self:
        """Set to blocklist mode."""
        self._config.mode = BlockMode.BLOCKLIST
        return self

    def disabled(self) -> Self:
        """Disable geo blocking."""
        self._config.mode = BlockMode.DISABLED
        return self

    def block_countries(self, *countries: str) -> Self:
        """Add countries to blocklist."""
        self._config.blocked_countries.update(c.upper() for c in countries)
        return self

    def allow_countries(self, *countries: str) -> Self:
        """Add countries to allowlist."""
        self._config.allowed_countries.update(c.upper() for c in countries)
        return self

    def block_regions(self, *regions: str) -> Self:
        """Add regions to blocklist."""
        self._config.blocked_regions.update(r.upper() for r in regions)
        return self

    def block_cities(self, *cities: str) -> Self:
        """Add cities to blocklist."""
        self._config.blocked_cities.update(cities)
        return self

    def block_ips(self, *ips: str) -> Self:
        """Add IPs to blocklist."""
        self._config.blocked_ips.update(ips)
        return self

    def allow_ips(self, *ips: str) -> Self:
        """Add IPs to allowlist."""
        self._config.allowed_ips.update(ips)
        return self

    def block_anonymous(self, block: bool = True) -> Self:
        """Block anonymous proxies/VPNs."""
        self._config.block_anonymous = block
        return self

    def block_datacenter(self, block: bool = True) -> Self:
        """Block datacenter IPs."""
        self._config.block_datacenter = block
        return self

    def block_unknown(self, block: bool = True) -> Self:
        """Block unknown locations."""
        self._config.block_unknown = block
        return self

    def custom_message(self, message: str) -> Self:
        """Set custom block message."""
        self._config.custom_block_message = message
        return self

    def build(self) -> GeoBlockConfig:
        """Build the configuration."""
        return self._config


def create_geo_blocker(
    config: GeoBlockConfig | None = None,
    provider: GeoProvider | None = None,
) -> GeoBlocker:
    """Create a GeoBlocker with optional config and provider."""
    return GeoBlocker(
        config=config or GeoBlockConfig(),
        provider=provider or InMemoryGeoProvider(),
    )


__all__ = [
    "BlockMode",
    "GeoBlockConfig",
    "GeoBlockConfigBuilder",
    "GeoBlockResult",
    "GeoBlocker",
    "GeoLocation",
    "GeoProvider",
    "InMemoryGeoProvider",
    "create_geo_blocker",
]
