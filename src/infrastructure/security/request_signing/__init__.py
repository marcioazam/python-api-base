"""Request signing with HMAC for integrity verification.

**Feature: api-architecture-analysis, Task 11.7: Request Signing**
**Validates: Requirements 5.5**

Provides HMAC-based request signing and verif

Feature: file-size-compliance-phase2
"""

from .config import SignatureConfig
from .enums import HashAlgorithm
from .errors import (
    ExpiredTimestampError,
    InvalidSignatureError,
    ReplayedRequestError,
    SignatureError,
)
from .models import SignedRequest
from .nonce_store import NonceStore
from .service import RequestSigner, RequestVerifier, create_signer_verifier_pair

__all__ = [
    "ExpiredTimestampError",
    "HashAlgorithm",
    "InvalidSignatureError",
    "NonceStore",
    "ReplayedRequestError",
    "RequestSigner",
    "RequestVerifier",
    "SignatureConfig",
    "SignatureError",
    "SignedRequest",
    "create_signer_verifier_pair",
]
