"""Fingerprint generation and analysis.

**Feature: file-size-compliance-phase2, Task 2.6**
**Validates: Requirements 1.6, 5.1, 5.2, 5.3**
"""

import hashlib
import json
import re
from datetime import datetime, UTC

from .enums import FingerprintComponent, SuspicionLevel
from .models import (
    Fingerprint,
    FingerprintConfig,
    RequestData,
    SuspicionAnalysis,
    SuspicionIndicator,
)


class FingerprintGenerator:
    """Generates fingerprints from request data."""

    BOT_PATTERNS = [
        "bot", "crawler", "spider", "scraper", "curl", "wget",
        "python-requests", "httpx", "aiohttp", "axios", "fetch",
    ]

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
            created_at=datetime.now(UTC),
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
        normalized = re.sub(r"/[\d.]+", "/X", user_agent)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized.lower()

    def _compute_hash(self, components: dict[FingerprintComponent, str]) -> str:
        """Compute hash from components."""
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
        timestamp = datetime.now(UTC).isoformat()
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

        if not user_agent:
            indicators.append(
                SuspicionIndicator(
                    name="empty_user_agent",
                    description="User agent is empty",
                    severity=SuspicionLevel.HIGH,
                    weight=0.4,
                )
            )

        if fingerprint.confidence < 0.5:
            indicators.append(
                SuspicionIndicator(
                    name="low_confidence",
                    description=f"Low fingerprint confidence: {fingerprint.confidence:.2f}",
                    severity=SuspicionLevel.MEDIUM,
                    weight=0.2,
                )
            )

        score = min(sum(i.weight for i in indicators), 1.0)

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
