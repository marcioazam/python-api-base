"""Webhook signature utilities using HMAC-SHA256.

This module provides cryptographic signature generation and verification
for webhook payloads, ensuring message integrity and authenticity.

Security Features:
    - HMAC-SHA256 for cryptographic signing
    - Timestamp-based replay attack prevention
    - Constant-time comparison to prevent timing attacks
    - Canonical JSON serialization for deterministic signatures

**Feature: enterprise-features-2025, Task 5.4: Implement HMAC-SHA256 signature**
**Validates: Requirements 5.4**

Example:
    >>> from pydantic import SecretStr
    >>> secret = SecretStr("my-webhook-secret-key-32chars!!")
    >>> payload = {"event": "user.created", "user_id": "123"}
    >>> headers = generate_signature_header(payload, secret)
    >>> # Send webhook with headers...
    >>> # On receiver side:
    >>> from datetime import datetime
    >>> timestamp = datetime.fromisoformat(headers["X-Webhook-Timestamp"])
    >>> is_valid = verify_signature(payload, headers["X-Webhook-Signature"], secret, timestamp)
"""

import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any

from pydantic import SecretStr


def sign_payload(
    payload: dict[str, Any],
    secret: SecretStr,
    timestamp: datetime | None = None,
) -> str:
    """Sign a webhook payload using HMAC-SHA256.

    Creates a cryptographic signature by combining the timestamp and
    canonicalized payload, then computing HMAC-SHA256 with the shared secret.

    The signature format is: HMAC-SHA256(secret, "{timestamp_iso}:{canonical_json}")

    Args:
        payload: The payload dictionary to sign. Will be serialized to JSON
            with sorted keys for deterministic output.
        secret: The shared secret for signing. Must be a SecretStr to prevent
            accidental logging of sensitive values.
        timestamp: Optional timestamp to include in signature. If None,
            current UTC time is used. Including timestamp prevents replay attacks.

    Returns:
        The hexadecimal signature string (64 characters for SHA-256).

    Raises:
        TypeError: If payload cannot be JSON serialized.

    Example:
        >>> secret = SecretStr("my-secret-key-at-least-32-chars!")
        >>> payload = {"user_id": "123", "action": "created"}
        >>> sig = sign_payload(payload, secret)
        >>> len(sig)
        64
    """
    if timestamp is None:
        timestamp = datetime.now(UTC)

    # Create canonical payload string with sorted keys for determinism
    canonical = json.dumps(payload, sort_keys=True, default=str)

    # Include timestamp in signed data to prevent replay attacks
    signed_data = f"{timestamp.isoformat()}:{canonical}"

    # Generate HMAC-SHA256 signature
    signature = hmac.new(
        secret.get_secret_value().encode("utf-8"),
        signed_data.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return signature


def verify_signature(
    payload: dict[str, Any],
    signature: str,
    secret: SecretStr,
    timestamp: datetime,
    tolerance_seconds: int = 300,
) -> bool:
    """Verify a webhook signature for authenticity and freshness.

    Performs two-step verification:
    1. Checks that the timestamp is within the tolerance window (prevents replay attacks)
    2. Recomputes the expected signature and compares using constant-time comparison

    Args:
        payload: The payload dictionary that was signed.
        signature: The signature string to verify (from X-Webhook-Signature header).
        secret: The shared secret used for signing.
        timestamp: The timestamp from the webhook header (X-Webhook-Timestamp).
            Must be timezone-aware (UTC recommended).
        tolerance_seconds: Maximum age of signature in seconds. Default is 300 (5 minutes).
            Signatures older than this are rejected to prevent replay attacks.

    Returns:
        True if signature is valid AND timestamp is within tolerance.
        False if signature is invalid OR timestamp is outside tolerance.

    Security Notes:
        - Uses hmac.compare_digest() for constant-time comparison to prevent timing attacks
        - Rejects signatures with timestamps in the future (beyond tolerance)
        - Rejects signatures with timestamps in the past (beyond tolerance)

    Example:
        >>> from datetime import datetime, UTC
        >>> secret = SecretStr("my-secret-key-at-least-32-chars!")
        >>> payload = {"user_id": "123"}
        >>> timestamp = datetime.now(UTC)
        >>> sig = sign_payload(payload, secret, timestamp)
        >>> verify_signature(payload, sig, secret, timestamp)
        True
        >>> verify_signature(payload, "invalid", secret, timestamp)
        False
    """
    # Check timestamp is within tolerance (prevents replay attacks)
    now = datetime.now(UTC)
    age = abs((now - timestamp).total_seconds())
    if age > tolerance_seconds:
        return False

    # Compute expected signature using same algorithm
    expected = sign_payload(payload, secret, timestamp)

    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(signature, expected)


def generate_signature_header(
    payload: dict[str, Any],
    secret: SecretStr,
) -> dict[str, str]:
    """Generate webhook signature headers for outgoing requests.

    Creates the standard webhook signature headers that should be included
    in webhook HTTP requests. The receiver can use these headers to verify
    the request authenticity.

    Args:
        payload: The payload dictionary to sign.
        secret: The shared secret for signing.

    Returns:
        Dictionary containing:
            - X-Webhook-Signature: The HMAC-SHA256 signature (hex string)
            - X-Webhook-Timestamp: The ISO 8601 timestamp used in signing

    Example:
        >>> secret = SecretStr("my-secret-key-at-least-32-chars!")
        >>> payload = {"event": "order.created", "order_id": "456"}
        >>> headers = generate_signature_header(payload, secret)
        >>> headers.keys()
        dict_keys(['X-Webhook-Signature', 'X-Webhook-Timestamp'])
        >>> len(headers["X-Webhook-Signature"])
        64
    """
    timestamp = datetime.now(UTC)
    signature = sign_payload(payload, secret, timestamp)

    return {
        "X-Webhook-Signature": signature,
        "X-Webhook-Timestamp": timestamp.isoformat(),
    }
