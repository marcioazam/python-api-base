"""Request Fingerprinting for advanced client identification.

This module provides fingerprinting capabilities to identify clients
based on various request characteristics for security and analytics.

**Feature: api-architecture-analysis**
**Validates: Requirements 5.5**
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class FingerprintComponent(Enum):
    """Components used in fingerprint generation."""

    IP_ADDRESS = "ip_address"
    USER_AGENT = "user_agent"
    ACCEPT_LANGUAGE = "accept_language"
    ACCEPT_ENCODING = "accept_encoding"
    ACCEPT = "accept"
    CONNECTION = "connection"
    CACHE_CONTROL = "cache_control"
    DNT = "dnt"
    UPGRADE_INSECURE = "upgrade_insecure"
    SEC_FETCH_SITE = "sec_fetch_site"
    SEC_FETCH_MODE = "sec_fetch_mode"
    SEC_FETCH_DEST = "sec_fetch_dest"
    SEC_CH_UA = "sec_ch_ua"
    SEC_CH_UA_MOBILE = "sec_ch_ua_mobile"
    SEC_CH_UA_PLATFORM = "sec_ch_ua_platform"
    TIMEZONE = "timezone"
    SCREEN_RESOLUTION = "screen_resolution"
    COLOR_DEPTH = "color_depth"
    PLUGINS = "plugins"
    FONTS = "fonts"
    CANVAS = "canvas"
    WEBGL = "webgl"
    AUDIO = "audio"


class SuspicionLevel(Enum):
    """Level of suspicion for a fingerprint."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class RequestData:
    """Data extracted from a request for fingerprinting."""

    ip_address: str
    user_agent: str = ""
    accept_language: str = ""
    accept_encoding: str = ""
    accept: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    client_hints: dict[str, str] = field(default_factory=dict)


@dataclass
class Fingerprint:
    """A computed fingerprint for a client."""

    fingerprint_id: str
    components: dict[FingerprintComponent, str]
    hash_value: str
    created_at: datetime
    confidence: float = 1.0

    @property
    def short_id(self) -> str:
        """Get short version of fingerprint ID."""
        return self.fingerprint_id[:16]


@dataclass
class SuspicionIndicator:
    """An indicator of suspicious behavior."""

    name: str
    description: str
    severity: SuspicionLevel
    weight: float = 1.0


@dataclass
class SuspicionAnalysis:
    """Analysis of suspicious indicators for a fingerprint."""

    fingerprint: Fingerprint
    indicators: list[SuspicionIndicator]
    overall_level: SuspicionLevel
    score: float  # 0.0 to 1.0
    details: str = ""

    @property
    def is_suspicious(self) -> bool:
        """Check if analysis indicates suspicion."""
        return self.overall_level not in (SuspicionLevel.NONE, SuspicionLevel.LOW)


@dataclass
class FingerprintConfig:
    """Configuration for fingerprint generation."""

    components: set[FingerprintComponent] = field(
        default_factory=lambda: {
            FingerprintComponent.IP_ADDRESS,
            FingerprintComponent.USER_AGENT,
            FingerprintComponent.ACCEPT_LANGUAGE,
            FingerprintComponent.ACCEPT_ENCODING,
        }
    )
    hash_algorithm: str = "sha256"
    include_ip_in_hash: bool = True
    normalize_user_agent: bool = True
    suspicion_thresholds: dict[SuspicionLevel, float] = field(
        default_factory=lambda: {
            SuspicionLevel.LOW: 0.2,
            SuspicionLevel.MEDIUM: 0.4,
            SuspicionLevel.HIGH: 0.6,
            SuspicionLevel.CRITICAL: 0.8,
        }
    )


@runtime_checkable
class FingerprintStore(Protocol):
    """Protocol for fingerprint storage."""

    async def get(self, fingerprint_id: str) -> Fingerprint | None: ...
    async def save(self, fingerprint: Fingerprint) -> None: ...
    async def get_by_ip(self, ip_address: str) -> list[Fingerprint]: ...
    async def get_recent(self, limit: int = 100) -> list[Fingerprint]: ...


class InMemoryFingerprintStore:
    """In-memory implementation of FingerprintStore."""

    def __init__(self) -> None:
        self._fingerprints: dict[str, Fingerprint] = {}
        self._by_ip: dict[str, list[str]] = {}

    async def get(self, fingerprint_id: str) -> Fingerprint | None:
        """Get fingerprint by ID."""
        return self._fingerprints.get(fingerprint_id)

    async def save(self, fingerprint: Fingerprint) -> None:
        """Save a fingerprint."""
        self._fingerprints[fingerprint.fingerprint_id] = fingerprint
        ip = fingerprint.components.get(FingerprintComponent.IP_ADDRESS, "")
        if ip:
            if ip not in self._by_ip:
                self._by_ip[ip] = []
            if fingerprint.fingerprint_id not in self._by_ip[ip]:
                self._by_ip[ip].append(fingerprint.fingerprint_id)

    async def get_by_ip(self, ip_address: str) -> list[Fingerprint]:
        """Get all fingerprints for an IP."""
        ids = self._by_ip.get(ip_address, [])
        return [self._fingerprints[fid] for fid in ids if fid in self._fingerprints]

    async def get_recent(self, limit: int = 100) -> list[Fingerprint]:
        """Get recent fingerprints."""
        sorted_fps = sorted(
            self._fingerprints.values(),
            key=lambda f: f.created_at,
            reverse=True,
        )
        return sorted_fps[:limit]


class FingerprintGenerator:
    """Generates fingerprints from request data."""

    # Known bot user agents patterns
    BOT_PATTERNS = [
        "bot", "crawler", "spider", "scraper", "curl", "wget",
        "python-requests", "httpx", "aiohttp", "axios", "fetch",
    ]

    # Known headless browser indicators
    HEADLESS_INDICATORS = [
        "headless", "phantomjs", "selenium", "puppeteer", "playwright",
    ]

    def __init__(self, config: FingerprintConfig | None = None) -> None:
        self._config = config or FingerprintConfig()

    def generate(self, request_data: RequestData) -> Fingerprint:
        """Generate a fingerprint from request data."""
        components = self._extract_components(request_data)
        hash_value = self._compute_hash(components)
        fingerprint_id = self._generate_id(hash_value, request_data)

        return Fingerprint(
            fingerprint_id=fingerprint_id,
            components=components,
            hash_value=hash_value,
            created_at=datetime.now(),
            confidence=self._calculate_confidence(components),
        )

    def _extract_components(
        self, request_data: RequestData
    ) -> dict[FingerprintComponent, str]:
        """Extract fingerprint components from request data."""
        components: dict[FingerprintComponent, str] = {}

        if FingerprintComponent.IP_ADDRESS in self._config.components:
            components[FingerprintComponent.IP_ADDRESS] = request_data.ip_address

        if FingerprintComponent.USER_AGENT in self._config.components:
            ua = request_data.user_agent
            if self._config.normalize_user_agent:
                ua = self._normalize_user_agent(ua)
            components[FingerprintComponent.USER_AGENT] = ua

        if FingerprintComponent.ACCEPT_LANGUAGE in self._config.components:
            components[FingerprintComponent.ACCEPT_LANGUAGE] = request_data.accept_language

        if FingerprintComponent.ACCEPT_ENCODING in self._config.components:
            components[FingerprintComponent.ACCEPT_ENCODING] = request_data.accept_encoding

        if FingerprintComponent.ACCEPT in self._config.components:
            components[FingerprintComponent.ACCEPT] = request_data.accept

        # Extract from headers
        header_mappings = {
            FingerprintComponent.CONNECTION: "connection",
            FingerprintComponent.CACHE_CONTROL: "cache-control",
            FingerprintComponent.DNT: "dnt",
            FingerprintComponent.UPGRADE_INSECURE: "upgrade-insecure-requests",
            FingerprintComponent.SEC_FETCH_SITE: "sec-fetch-site",
            FingerprintComponent.SEC_FETCH_MODE: "sec-fetch-mode",
            FingerprintComponent.SEC_FETCH_DEST: "sec-fetch-dest",
        }

        for component, header_name in header_mappings.items():
            if component in self._config.components:
                value = request_data.headers.get(header_name, "")
                if value:
                    components[component] = value

        # Extract client hints
        hint_mappings = {
            FingerprintComponent.SEC_CH_UA: "sec-ch-ua",
            FingerprintComponent.SEC_CH_UA_MOBILE: "sec-ch-ua-mobile",
            FingerprintComponent.SEC_CH_UA_PLATFORM: "sec-ch-ua-platform",
        }

        for component, hint_name in hint_mappings.items():
            if component in self._config.components:
                value = request_data.client_hints.get(hint_name, "")
                if value:
                    components[component] = value

        return components

    def _normalize_user_agent(self, user_agent: str) -> str:
        """Normalize user agent string."""
        # Remove version numbers for more stable fingerprinting
        import re
        normalized = re.sub(r"/[\d.]+", "/X", user_agent)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized.lower()

    def _compute_hash(self, components: dict[FingerprintComponent, str]) -> str:
        """Compute hash from components."""
        # Sort components for consistent hashing
        sorted_items = sorted(
            [(k.value, v) for k, v in components.items()],
            key=lambda x: x[0],
        )

        if not self._config.include_ip_in_hash:
            sorted_items = [
                (k, v) for k, v in sorted_items
                if k != FingerprintComponent.IP_ADDRESS.value
            ]

        data = json.dumps(sorted_items, sort_keys=True)
        hasher = hashlib.new(self._config.hash_algorithm)
        hasher.update(data.encode("utf-8"))
        return hasher.hexdigest()

    def _generate_id(self, hash_value: str, request_data: RequestData) -> str:
        """Generate unique fingerprint ID."""
        timestamp = datetime.now().isoformat()
        combined = f"{hash_value}:{request_data.ip_address}:{timestamp}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def _calculate_confidence(
        self, components: dict[FingerprintComponent, str]
    ) -> float:
        """Calculate confidence score based on available components."""
        total = len(self._config.components)
        available = len([c for c in components.values() if c])
        return available / total if total > 0 else 0.0


class SuspicionAnalyzer:
    """Analyzes fingerprints for suspicious patterns."""

    def __init__(self, config: FingerprintConfig | None = None) -> None:
        self._config = config or FingerprintConfig()

    def analyze(self, fingerprint: Fingerprint) -> SuspicionAnalysis:
        """Analyze a fingerprint for suspicious indicators."""
        indicators: list[SuspicionIndicator] = []

        # Check for bot patterns
        user_agent = fingerprint.components.get(FingerprintComponent.USER_AGENT, "").lower()
        for pattern in FingerprintGenerator.BOT_PATTERNS:
            if pattern in user_agent:
                indicators.append(
                    SuspicionIndicator(
                        name="bot_user_agent",
                        description=f"User agent contains bot pattern: {pattern}",
                        severity=SuspicionLevel.MEDIUM,
                        weight=0.3,
                    )
                )
                break

        # Check for headless browser
        for indicator in FingerprintGenerator.HEADLESS_INDICATORS:
            if indicator in user_agent:
                indicators.append(
                    SuspicionIndicator(
                        name="headless_browser",
                        description=f"Headless browser detected: {indicator}",
                        severity=SuspicionLevel.HIGH,
                        weight=0.5,
                    )
                )
                break

        # Check for missing common headers
        if not fingerprint.components.get(FingerprintComponent.ACCEPT_LANGUAGE):
            indicators.append(
                SuspicionIndicator(
                    name="missing_accept_language",
                    description="Accept-Language header is missing",
                    severity=SuspicionLevel.LOW,
                    weight=0.1,
                )
            )

        if not fingerprint.components.get(FingerprintComponent.ACCEPT_ENCODING):
            indicators.append(
                SuspicionIndicator(
                    name="missing_accept_encoding",
                    description="Accept-Encoding header is missing",
                    severity=SuspicionLevel.LOW,
                    weight=0.1,
                )
            )

        # Check for empty user agent
        if not user_agent:
            indicators.append(
                SuspicionIndicator(
                    name="empty_user_agent",
                    description="User agent is empty",
                    severity=SuspicionLevel.HIGH,
                    weight=0.4,
                )
            )

        # Check for low confidence
        if fingerprint.confidence < 0.5:
            indicators.append(
                SuspicionIndicator(
                    name="low_confidence",
                    description=f"Low fingerprint confidence: {fingerprint.confidence:.2f}",
                    severity=SuspicionLevel.MEDIUM,
                    weight=0.2,
                )
            )

        # Calculate overall score
        score = sum(i.weight for i in indicators)
        score = min(score, 1.0)  # Cap at 1.0

        # Determine overall level
        overall_level = SuspicionLevel.NONE
        for level, threshold in sorted(
            self._config.suspicion_thresholds.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            if score >= threshold:
                overall_level = level
                break

        return SuspicionAnalysis(
            fingerprint=fingerprint,
            indicators=indicators,
            overall_level=overall_level,
            score=score,
            details=f"Found {len(indicators)} suspicious indicators",
        )


class FingerprintService:
    """Service for fingerprint generation and analysis."""

    def __init__(
        self,
        config: FingerprintConfig | None = None,
        store: FingerprintStore | None = None,
    ) -> None:
        self._config = config or FingerprintConfig()
        self._store = store or InMemoryFingerprintStore()
        self._generator = FingerprintGenerator(self._config)
        self._analyzer = SuspicionAnalyzer(self._config)

    async def fingerprint_request(
        self, request_data: RequestData
    ) -> tuple[Fingerprint, SuspicionAnalysis]:
        """Generate fingerprint and analyze for suspicion."""
        fingerprint = self._generator.generate(request_data)
        await self._store.save(fingerprint)
        analysis = self._analyzer.analyze(fingerprint)
        return fingerprint, analysis

    async def get_fingerprint(self, fingerprint_id: str) -> Fingerprint | None:
        """Get a fingerprint by ID."""
        return await self._store.get(fingerprint_id)

    async def get_fingerprints_for_ip(self, ip_address: str) -> list[Fingerprint]:
        """Get all fingerprints for an IP address."""
        return await self._store.get_by_ip(ip_address)

    async def is_suspicious(self, request_data: RequestData) -> bool:
        """Quick check if request is suspicious."""
        fingerprint = self._generator.generate(request_data)
        analysis = self._analyzer.analyze(fingerprint)
        return analysis.is_suspicious

    def analyze_fingerprint(self, fingerprint: Fingerprint) -> SuspicionAnalysis:
        """Analyze an existing fingerprint."""
        return self._analyzer.analyze(fingerprint)


# Convenience factory
def create_fingerprint_service(
    config: FingerprintConfig | None = None,
    store: FingerprintStore | None = None,
) -> FingerprintService:
    """Create a FingerprintService with defaults."""
    return FingerprintService(config=config, store=store)
