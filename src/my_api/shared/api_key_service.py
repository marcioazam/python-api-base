"""API Key Management - Secure API key service with rotation.

**Feature: api-architecture-analysis, Priority 11.3: API Key Management**
**Validates: Requirements 5.1, 5.4**

Provides:
- APIKeyService with key generation and rotation
- Scoped API keys per client
- Key validation and rate limiting
- Key expiration and revocation
"""

import hashlib
import hmac
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import bcrypt


class KeyStatus(str, Enum):
    """Status of an API key."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ROTATED = "rotated"


class KeyScope(str, Enum):
    """Scope/permission level for API keys."""

    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    FULL = "full"


@dataclass
class APIKey:
    """API key entity."""

    key_id: str
    key_hash: str
    client_id: str
    name: str
    scopes: list[KeyScope] = field(default_factory=list)
    status: KeyStatus = KeyStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    rate_limit: int = 1000  # requests per hour
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if key is expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_active(self) -> bool:
        """Check if key is active and not expired."""
        return self.status == KeyStatus.ACTIVE and not self.is_expired

    def has_scope(self, scope: KeyScope) -> bool:
        """Check if key has a specific scope."""
        if KeyScope.FULL in self.scopes:
            return True
        if KeyScope.ADMIN in self.scopes and scope in [KeyScope.READ, KeyScope.WRITE]:
            return True
        return scope in self.scopes


@dataclass
class KeyValidationResult:
    """Result of API key validation."""

    valid: bool
    key: APIKey | None = None
    error: str | None = None
    remaining_requests: int | None = None


@dataclass
class KeyRotationResult:
    """Result of key rotation."""

    success: bool
    old_key_id: str | None = None
    new_key: str | None = None
    new_key_id: str | None = None
    error: str | None = None


class APIKeyService:
    """Service for managing API keys with secure bcrypt hashing.

    **Feature: shared-modules-security-fixes**
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    """

    # Bcrypt cost factor (12 is recommended minimum for security)
    BCRYPT_COST_FACTOR = 12
    # Hash format prefixes for migration support
    HASH_PREFIX_BCRYPT = "$2b$"
    HASH_PREFIX_SHA256 = "sha256:"

    def __init__(
        self,
        key_prefix: str = "ak_",
        default_expiry_days: int = 365,
        default_rate_limit: int = 1000,
    ) -> None:
        """Initialize API key service."""
        self._key_prefix = key_prefix
        self._default_expiry_days = default_expiry_days
        self._default_rate_limit = default_rate_limit
        self._keys: dict[str, APIKey] = {}  # key_id -> APIKey
        self._key_hashes: dict[str, str] = {}  # hash -> key_id
        self._usage: dict[str, list[datetime]] = {}  # key_id -> usage timestamps

    def _generate_key(self) -> str:
        """Generate a new API key."""
        random_part = secrets.token_urlsafe(32)
        return f"{self._key_prefix}{random_part}"

    def _hash_key(self, key: str) -> str:
        """Hash an API key using bcrypt with unique salt.

        Each call generates a unique salt, so the same key will produce
        different hashes (this is expected and correct for bcrypt).

        Args:
            key: The API key to hash.

        Returns:
            Bcrypt hash string (starts with $2b$).
        """
        salt = bcrypt.gensalt(rounds=self.BCRYPT_COST_FACTOR)
        return bcrypt.hashpw(key.encode("utf-8"), salt).decode("utf-8")

    def _hash_key_sha256(self, key: str) -> str:
        """Legacy SHA256 hash (for migration support only).

        Args:
            key: The API key to hash.

        Returns:
            SHA256 hash with prefix.
        """
        hash_value = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return f"{self.HASH_PREFIX_SHA256}{hash_value}"

    def _verify_key(self, key: str, key_hash: str) -> bool:
        """Verify key using constant-time comparison.

        Supports both bcrypt (new) and SHA256 (legacy) formats.

        Args:
            key: The API key to verify.
            key_hash: The stored hash to verify against.

        Returns:
            True if key matches hash, False otherwise.
        """
        if key_hash.startswith(self.HASH_PREFIX_BCRYPT):
            # Bcrypt verification (already constant-time)
            return bcrypt.checkpw(key.encode("utf-8"), key_hash.encode("utf-8"))
        elif key_hash.startswith(self.HASH_PREFIX_SHA256):
            # Legacy SHA256 with constant-time comparison
            computed = hashlib.sha256(key.encode("utf-8")).hexdigest()
            stored = key_hash[len(self.HASH_PREFIX_SHA256):]
            return hmac.compare_digest(computed, stored)
        return False

    def _generate_key_id(self) -> str:
        """Generate a unique key ID."""
        return f"key_{secrets.token_hex(8)}"

    def create_key(
        self,
        client_id: str,
        name: str,
        scopes: list[KeyScope] | None = None,
        expires_in_days: int | None = None,
        rate_limit: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[str, APIKey]:
        """Create a new API key.

        Returns:
            Tuple of (raw_key, APIKey object)
        """
        raw_key = self._generate_key()
        key_hash = self._hash_key(raw_key)
        key_id = self._generate_key_id()

        expiry_days = expires_in_days or self._default_expiry_days
        expires_at = None
        if expiry_days > 0:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expiry_days)

        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            client_id=client_id,
            name=name,
            scopes=scopes or [KeyScope.READ],
            status=KeyStatus.ACTIVE,
            expires_at=expires_at,
            rate_limit=rate_limit or self._default_rate_limit,
            metadata=metadata or {},
        )

        self._keys[key_id] = api_key
        self._key_hashes[key_hash] = key_id
        self._usage[key_id] = []

        return raw_key, api_key

    def validate_key(
        self,
        raw_key: str,
        required_scope: KeyScope | None = None,
    ) -> KeyValidationResult:
        """Validate an API key using constant-time comparison.

        Supports both bcrypt (new) and SHA256 (legacy) hash formats.
        """
        # Find matching key by verifying against all stored hashes
        key_id = None
        for stored_hash, stored_key_id in self._key_hashes.items():
            if self._verify_key(raw_key, stored_hash):
                key_id = stored_key_id
                break

        if key_id is None:
            return KeyValidationResult(valid=False, error="Invalid API key")

        api_key = self._keys.get(key_id)
        if api_key is None:
            return KeyValidationResult(valid=False, error="Key not found")

        if api_key.status == KeyStatus.REVOKED:
            return KeyValidationResult(valid=False, error="Key has been revoked")

        if api_key.status == KeyStatus.ROTATED:
            return KeyValidationResult(valid=False, error="Key has been rotated")

        if api_key.is_expired:
            return KeyValidationResult(valid=False, error="Key has expired")

        if required_scope and not api_key.has_scope(required_scope):
            return KeyValidationResult(
                valid=False,
                error=f"Key does not have required scope: {required_scope.value}",
            )

        # Check rate limit
        remaining = self._check_rate_limit(key_id, api_key.rate_limit)
        if remaining <= 0:
            return KeyValidationResult(
                valid=False,
                error="Rate limit exceeded",
                remaining_requests=0,
            )

        # Update last used
        api_key.last_used_at = datetime.now(timezone.utc)
        self._record_usage(key_id)

        return KeyValidationResult(
            valid=True,
            key=api_key,
            remaining_requests=remaining - 1,
        )

    def _check_rate_limit(self, key_id: str, limit: int) -> int:
        """Check rate limit and return remaining requests."""
        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)

        # Clean old entries
        usage = self._usage.get(key_id, [])
        usage = [ts for ts in usage if ts > hour_ago]
        self._usage[key_id] = usage

        return limit - len(usage)

    def _record_usage(self, key_id: str) -> None:
        """Record API key usage."""
        if key_id not in self._usage:
            self._usage[key_id] = []
        self._usage[key_id].append(datetime.now(timezone.utc))

    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        api_key = self._keys.get(key_id)
        if api_key is None:
            return False

        api_key.status = KeyStatus.REVOKED
        return True

    def rotate_key(self, key_id: str) -> KeyRotationResult:
        """Rotate an API key, creating a new one."""
        old_key = self._keys.get(key_id)
        if old_key is None:
            return KeyRotationResult(success=False, error="Key not found")

        if old_key.status != KeyStatus.ACTIVE:
            return KeyRotationResult(success=False, error="Can only rotate active keys")

        # Create new key with same properties
        new_raw_key, new_api_key = self.create_key(
            client_id=old_key.client_id,
            name=old_key.name,
            scopes=old_key.scopes,
            rate_limit=old_key.rate_limit,
            metadata=old_key.metadata,
        )

        # Mark old key as rotated
        old_key.status = KeyStatus.ROTATED

        return KeyRotationResult(
            success=True,
            old_key_id=key_id,
            new_key=new_raw_key,
            new_key_id=new_api_key.key_id,
        )

    def get_key(self, key_id: str) -> APIKey | None:
        """Get API key by ID."""
        return self._keys.get(key_id)

    def get_keys_for_client(self, client_id: str) -> list[APIKey]:
        """Get all keys for a client."""
        return [k for k in self._keys.values() if k.client_id == client_id]

    def get_active_keys_for_client(self, client_id: str) -> list[APIKey]:
        """Get active keys for a client."""
        return [k for k in self.get_keys_for_client(client_id) if k.is_active]

    def update_key_scopes(self, key_id: str, scopes: list[KeyScope]) -> bool:
        """Update scopes for a key."""
        api_key = self._keys.get(key_id)
        if api_key is None:
            return False
        api_key.scopes = scopes
        return True

    def update_key_rate_limit(self, key_id: str, rate_limit: int) -> bool:
        """Update rate limit for a key."""
        api_key = self._keys.get(key_id)
        if api_key is None:
            return False
        api_key.rate_limit = rate_limit
        return True

    def extend_key_expiry(self, key_id: str, days: int) -> bool:
        """Extend key expiry by specified days."""
        api_key = self._keys.get(key_id)
        if api_key is None:
            return False

        if api_key.expires_at is None:
            api_key.expires_at = datetime.now(timezone.utc) + timedelta(days=days)
        else:
            api_key.expires_at = api_key.expires_at + timedelta(days=days)
        return True

    def get_usage_stats(self, key_id: str) -> dict[str, Any]:
        """Get usage statistics for a key."""
        api_key = self._keys.get(key_id)
        if api_key is None:
            return {}

        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        usage = self._usage.get(key_id, [])
        hourly = len([ts for ts in usage if ts > hour_ago])
        daily = len([ts for ts in usage if ts > day_ago])

        return {
            "key_id": key_id,
            "client_id": api_key.client_id,
            "status": api_key.status.value,
            "requests_last_hour": hourly,
            "requests_last_day": daily,
            "rate_limit": api_key.rate_limit,
            "remaining_requests": api_key.rate_limit - hourly,
            "last_used": (
                api_key.last_used_at.isoformat() if api_key.last_used_at else None
            ),
        }

    def cleanup_expired_keys(self) -> int:
        """Mark expired keys and return count."""
        count = 0
        for api_key in self._keys.values():
            if api_key.status == KeyStatus.ACTIVE and api_key.is_expired:
                api_key.status = KeyStatus.EXPIRED
                count += 1
        return count

    def get_stats(self) -> dict[str, Any]:
        """Get service statistics."""
        total = len(self._keys)
        active = len([k for k in self._keys.values() if k.is_active])
        revoked = len([k for k in self._keys.values() if k.status == KeyStatus.REVOKED])
        expired = len([k for k in self._keys.values() if k.status == KeyStatus.EXPIRED])

        return {
            "total_keys": total,
            "active_keys": active,
            "revoked_keys": revoked,
            "expired_keys": expired,
        }


def create_api_key_service(
    key_prefix: str = "ak_",
    default_expiry_days: int = 365,
) -> APIKeyService:
    """Factory function to create API key service."""
    return APIKeyService(
        key_prefix=key_prefix,
        default_expiry_days=default_expiry_days,
    )
