"""Request signing service.

**Feature: full-codebase-review-2025, Task 1.6: Refactor request_signing**
**Validates: Requirements 9.2**
"""

import hashlib
import hmac
import secrets
import time
from typing import Any

from .config import SignatureConfig
from .errors import ExpiredTimestampError, InvalidSignatureError, ReplayedRequestError
from .models import SignedRequest
from .nonce_store import NonceStore

MIN_SECRET_KEY_LENGTH = 32


class RequestSigner:
    """HMAC request signer."""

    def __init__(self, secret_key: str | bytes, config: SignatureConfig | None = None) -> None:
        """Initialize request signer."""
        self._secret_key = secret_key.encode() if isinstance(secret_key, str) else secret_key
        if len(self._secret_key) < MIN_SECRET_KEY_LENGTH:
            raise ValueError(f"Secret key must be at least {MIN_SECRET_KEY_LENGTH} bytes")
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
        """Build canonical string for signing."""
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
        """Sign a request."""
        timestamp = timestamp or int(time.time())
        nonce = nonce or secrets.token_hex(16)
        canonical = self._build_canonical_string(
            method=method, path=path, timestamp=timestamp, nonce=nonce, body=body, headers=headers
        )
        signature = hmac.new(self._secret_key, canonical.encode(), self._get_hash_func()).hexdigest()
        return SignedRequest(signature=signature, timestamp=timestamp, nonce=nonce, canonical_string=canonical)

    def get_signature_headers(self, signed: SignedRequest) -> dict[str, str]:
        """Get headers to add to request."""
        return {
            self._config.signature_header: signed.signature,
            self._config.timestamp_header: str(signed.timestamp),
            self._config.nonce_header: signed.nonce,
        }


class RequestVerifier:
    """HMAC request verifier."""

    def __init__(
        self,
        secret_key: str | bytes,
        config: SignatureConfig | None = None,
        nonce_store: NonceStore | None = None,
    ) -> None:
        """Initialize request verifier."""
        encoded_key = secret_key.encode() if isinstance(secret_key, str) else secret_key
        if len(encoded_key) < MIN_SECRET_KEY_LENGTH:
            raise ValueError(f"Secret key must be at least {MIN_SECRET_KEY_LENGTH} bytes")
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
        """Verify request signature."""
        current_time = int(time.time())
        if abs(current_time - timestamp) > self._config.timestamp_tolerance:
            raise ExpiredTimestampError(timestamp, self._config.timestamp_tolerance)
        if not self._nonce_store.check_and_store(nonce, timestamp):
            raise ReplayedRequestError(nonce)
        signed = self._signer.sign(
            method=method, path=path, body=body, headers=headers, timestamp=timestamp, nonce=nonce
        )
        if not hmac.compare_digest(signature, signed.signature):
            raise InvalidSignatureError()
        return True

    def verify_from_headers(
        self, method: str, path: str, headers: dict[str, str], body: str | bytes | None = None
    ) -> bool:
        """Verify request from headers."""
        signature = headers.get(self._config.signature_header)
        timestamp_str = headers.get(self._config.timestamp_header)
        nonce = headers.get(self._config.nonce_header)
        if not signature or not timestamp_str or not nonce:
            raise InvalidSignatureError("Missing required signature headers")
        try:
            timestamp = int(timestamp_str)
        except ValueError:
            raise InvalidSignatureError("Invalid timestamp format")
        return self.verify(method=method, path=path, signature=signature, timestamp=timestamp, nonce=nonce, body=body, headers=headers)


def create_signer_verifier_pair(
    secret_key: str | bytes, config: SignatureConfig | None = None
) -> tuple[RequestSigner, RequestVerifier]:
    """Create a matched signer/verifier pair."""
    config = config or SignatureConfig()
    signer = RequestSigner(secret_key, config)
    verifier = RequestVerifier(secret_key, config)
    return signer, verifier
