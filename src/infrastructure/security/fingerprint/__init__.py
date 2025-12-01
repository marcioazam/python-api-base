"""Request Fingerprinting for advanced client identification.

**Feature: file-size-compliance-phase2, Task 2.6**
**Validates: Requirements 1.6, 5.1, 5.2, 5.3**

Provides fingerprinting capabilities to identify clients based on
various request characteristics for security and analytics.
"""

from .enums import FingerprintComponent, SuspicionLevel
from .generators import FingerprintGenerator, SuspicionAnalyzer
from .models import (
    Fingerprint,
    FingerprintConfig,
    RequestData,
    SuspicionAnalysis,
    SuspicionIndicator,
)
from .service import FingerprintService, create_fingerprint_service
from .store import FingerprintStore, InMemoryFingerprintStore

__all__ = [
    "Fingerprint",
    "FingerprintComponent",
    "FingerprintConfig",
    "FingerprintGenerator",
    "FingerprintService",
    "FingerprintStore",
    "InMemoryFingerprintStore",
    "RequestData",
    "SuspicionAnalysis",
    "SuspicionAnalyzer",
    "SuspicionIndicator",
    "SuspicionLevel",
    "create_fingerprint_service",
]
