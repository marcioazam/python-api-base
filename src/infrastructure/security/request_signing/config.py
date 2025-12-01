"""request_signing configuration.

**Feature: shared-modules-code-review-fixes, Task 8.2**
**Validates: Requirements 3.2**
"""

from dataclasses import dataclass

from .enums import HashAlgorithm


@dataclass(frozen=True, slots=True)
class SignatureConfig:
    """HMAC signature configuration.

    Attributes:
        algorithm: Hash algorithm to use.
        timestamp_tolerance: Max age of request in seconds.
        signature_header: Header name for signature.
        timestamp_header: Header name for timestamp.
        nonce_header: Header name for nonce (replay protection).
        include_body: Whether to include body in signature.
        include_path: Whether to include path in signature.
        include_method: Whether to include HTTP method in signature.
    """

    algorithm: HashAlgorithm = HashAlgorithm.SHA256
    timestamp_tolerance: int = 300  # 5 minutes
    signature_header: str = "X-Signature"
    timestamp_header: str = "X-Timestamp"
    nonce_header: str = "X-Nonce"
    include_body: bool = True
    include_path: bool = True
    include_method: bool = True
