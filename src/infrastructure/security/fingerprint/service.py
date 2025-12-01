"""Fingerprint service.

**Feature: file-size-compliance-phase2, Task 2.6**
**Validates: Requirements 1.6, 5.1, 5.2, 5.3**
"""

from .generators import FingerprintGenerator, SuspicionAnalyzer
from .models import Fingerprint, FingerprintConfig, RequestData, SuspicionAnalysis
from .store import FingerprintStore, InMemoryFingerprintStore


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


def create_fingerprint_service(
    config: FingerprintConfig | None = None,
    store: FingerprintStore | None = None,
) -> FingerprintService:
    """Create a FingerprintService with defaults."""
    return FingerprintService(config=config, store=store)
