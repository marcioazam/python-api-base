"""request_signing service.

**Feature: shared-modules-code-review-fixes, Task 4, 8.3**
**Validates: Requirements 6.1, 6.2, 6.3, 7.1, 7.2**
"""

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from typing import Any

from .config import SignatureConfig
from .enums import HashAlgorithm

# Minimum secret key length in bytes (256 bits)
MIN_SECRET_KEY_LENGTH = 32


@dataclass(frozen=True)
class SignedRequest:
    """Signed request data.

    Attributes:
        signature: HMAC signature.
        timestamp: Request timestamp.
        nonce: Unique nonce for replay protection.
        canonical_string: The string that was signed.
    """

    signature: str
    timestamp: int
    nonce: str
    canonical_string: str

class SignatureError(Exception):
    """Base signature error."""

    def __init__(self, message: str, error_code: str = "SIGNATURE_ERROR") -> None:
        super().__init__(message)
        self.error_code = error_code

class InvalidSignatureError(SignatureError):
    """Invalid signature error."""

    def __init__(self, reason: str = "Signature verification failed") -> None:
        super().__init__(reason, "INVALID_SIGNATURE")

class ExpiredTimestampError(SignatureError):
    """Expired timestamp error."""

    def __init__(self, timestamp: int, tolerance: int) -> None:
        super().__init__(
            f"Timestamp {timestamp} is outside tolerance of {tolerance}s",
            "EXPIRED_TIMESTAMP",
        )
        self.timestamp = timestamp
        self.tolerance = tolerance

class ReplayedRequestError(SignatureError):
    """Replayed request error (nonce reuse)."""

    def __init__(self, nonce: str) -> None:
        super().__init__(f"Nonce {nonce} has already been used", "REPLAYED_REQUEST")
        self.nonce = nonce

class NonceStore:
    """In-memory nonce store for replay protection."""

    def __init__(self, max_age: int = 300) -> None:
        """Initialize nonce store.

        Args:
            max_age: Maximum age of nonces to keep (seconds).
        """
        self._nonces: dict[str, int] = {}
        self._max_age = max_age

    def check_and_store(self, nonce: str, timestamp: int) -> bool:
        """Check if nonce is new and store it.

        Args:
            nonce: Request nonce.
            timestamp: Request timestamp.

        Returns:
            True if nonce is new, False if already used.
        """
        self._cleanup()

        if nonce in self._nonces:
            return False

        self._nonces[nonce] = timestamp
        return True

    def _cleanup(self) -> None:
        """Remove expired nonces."""
        current_time = int(time.time())
        cutoff = current_time - self._max_age

        expired = [k for k, v in self._nonces.items() if v < cutoff]
        for key in expired:
            del self._nonces[key]

    def clear(self) -> None:
        """Clear all stored nonces."""
        self._nonces.clear()

    @property
    def size(self) -> int:
        """Get number of stored nonces."""
        return len(self._nonces)

class RequestSigner:
    """HMAC request signer.

    Signs requests using HMAC with configurable algorithm and
    includes timestamp and nonce for replay protection.
    """

    def __init__(
        self,
        secret_key: str | bytes,
        config: SignatureConfig | None = None,
    ) -> None:
        """Initialize request signer.

        Args:
            secret_key: Secret key for HMAC.
            config: Signature configuration.

        Raises:
            ValueError: If secret key is shorter than MIN_SECRET_KEY_LENGTH bytes.
        """
        self._secret_key = (
            secret_key.encode() if isinstance(secret_key, str) else secret_key
        )
        if len(self._secret_key) < MIN_SECRET_KEY_LENGTH:
            raise ValueError(
                f"Secret key must be at least {MIN_SECRET_KEY_LENGTH} bytes"
            )
        self._config = config or SignatureConfig()

    @property
    def config(self) -> SignatureConfig:
        """Get signature configuration."""
        return self._config

    def _get_hash_func(self) -> Any:
        """Get hash function for configured algorithm."""
        return getattr(hashlib, self._config.algorithm.value)

    def _build_canonical_string(
        self,
        method: str,
        path: str,
        timestamp: int,
        nonce: str,
        body: str | bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        """Build canonical string for signing.

        Args:
            method: HTTP method.
            path: Request path.
            timestamp: Request timestamp.
            nonce: Request nonce.
            body: Request body.
            headers: Request headers to include.

        Returns:
            Canonical string for signing.
        """
        parts = [str(timestamp), nonce]

        if self._config.include_method:
            parts.append(method.upper())

        if self._config.include_path:
            parts.append(path)

        if self._config.include_body and body:
            body_str = body.decode() if isinstance(body, bytes) else body
            parts.append(body_str)

        return "\n".join(parts)

    def sign(
        self,
        method: str,
        path: str,
        body: str | bytes | None = None,
        headers: dict[str, str] | None = None,
        timestamp: int | None = None,
        nonce: str | None = None,
    ) -> SignedRequest:
        """Sign a request.

        Args:
            method: HTTP method.
            path: Request path.
            body: Request body.
            headers: Request headers.
            timestamp: Optional timestamp (default: current time).
            nonce: Optional nonce (default: generated).

        Returns:
            Signed request data.
        """
        timestamp = timestamp or int(time.time())
        nonce = nonce or secrets.token_hex(16)

        canonical = self._build_canonical_string(
            method=method,
            path=path,
            timestamp=timestamp,
            nonce=nonce,
            body=body,
            headers=headers,
        )

        signature = hmac.new(
            self._secret_key,
            canonical.encode(),
            self._get_hash_func(),
        ).hexdigest()

        return SignedRequest(
            signature=signature,
            timestamp=timestamp,
            nonce=nonce,
            canonical_string=canonical,
        )

    def get_signature_headers(self, signed: SignedRequest) -> dict[str, str]:
        """Get headers to add to request.

        Args:
            signed: Signed request data.

        Returns:
            Headers dictionary.
        """
        return {
            self._config.signature_header: signed.signature,
            self._config.timestamp_header: str(signed.timestamp),
            self._config.nonce_header: signed.nonce,
        }

class RequestVerifier:
    """HMAC request verifier.

    Verifies request signatures with timestamp and nonce validation.
    """

    def __init__(
        self,
        secret_key: str | bytes,
        config: SignatureConfig | None = None,
        nonce_store: NonceStore | None = None,
    ) -> None:
        """Initialize request verifier.

        Args:
            secret_key: Secret key for HMAC.
            config: Signature configuration.
            nonce_store: Optional nonce store for replay protection.

        Raises:
            ValueError: If secret key is shorter than MIN_SECRET_KEY_LENGTH bytes.
        """
        encoded_key = (
            secret_key.encode() if isinstance(secret_key, str) else secret_key
        )
        if len(encoded_key) < MIN_SECRET_KEY_LENGTH:
            raise ValueError(
                f"Secret key must be at least {MIN_SECRET_KEY_LENGTH} bytes"
            )
        self._signer = RequestSigner(secret_key, config)
        self._config = config or SignatureConfig()
        self._nonce_store = nonce_store or NonceStore(self._config.timestamp_tolerance)

    @property
    def config(self) -> SignatureConfig:
        """Get signature configuration."""
        return self._config

    def verify(
        self,
        method: str,
        path: str,
        signature: str,
        timestamp: int,
        nonce: str,
        body: str | bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> bool:
        """Verify request signature.

        Args:
            method: HTTP method.
            path: Request path.
            signature: Provided signature.
            timestamp: Request timestamp.
            nonce: Request nonce.
            body: Request body.
            headers: Request headers.

        Returns:
            True if signature is valid.

        Raises:
            ExpiredTimestampError: If timestamp is too old.
            ReplayedRequestError: If nonce was already used.
            InvalidSignatureError: If signature doesn't match.
        """
        # Validate timestamp
        current_time = int(time.time())
        if abs(current_time - timestamp) > self._config.timestamp_tolerance:
            raise ExpiredTimestampError(timestamp, self._config.timestamp_tolerance)

        # Check nonce for replay
        if not self._nonce_store.check_and_store(nonce, timestamp):
            raise ReplayedRequestError(nonce)

        # Compute expected signature
        signed = self._signer.sign(
            method=method,
            path=path,
            body=body,
            headers=headers,
            timestamp=timestamp,
            nonce=nonce,
        )

        # Constant-time comparison
        if not hmac.compare_digest(signature, signed.signature):
            raise InvalidSignatureError()

        return True

    def verify_from_headers(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body: str | bytes | None = None,
    ) -> bool:
        """Verify request from headers.

        Args:
            method: HTTP method.
            path: Request path.
            headers: Request headers (must contain signature headers).
            body: Request body.

        Returns:
            True if signature is valid.

        Raises:
            InvalidSignatureError: If required headers are missing.
        """
        signature = headers.get(self._config.signature_header)
        timestamp_str = headers.get(self._config.timestamp_header)
        nonce = headers.get(self._config.nonce_header)

        if not signature or not timestamp_str or not nonce:
            raise InvalidSignatureError("Missing required signature headers")

        try:
            timestamp = int(timestamp_str)
        except ValueError:
            raise InvalidSignatureError("Invalid timestamp format")

        return self.verify(
            method=method,
            path=path,
            signature=signature,
            timestamp=timestamp,
            nonce=nonce,
            body=body,
            headers=headers,
        )

def create_signer_verifier_pair(
    secret_key: str | bytes,
    config: SignatureConfig | None = None,
) -> tuple[RequestSigner, RequestVerifier]:
    """Create a matched signer/verifier pair.

    Args:
        secret_key: Shared secret key.
        config: Signature configuration.

    Returns:
        Tuple of (signer, verifier).
    """
    config = config or SignatureConfig()
    signer = RequestSigner(secret_key, config)
    verifier = RequestVerifier(secret_key, config)
    return signer, verifier
