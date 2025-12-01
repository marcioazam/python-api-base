"""API Key service implementation.

**Feature: full-codebase-review-2025, Task 1.2: Refactor api_key_service**
**Validates: Requirements 9.2**
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, UTC
from typing import Any

import bcrypt

from .enums import KeyScope, KeyStatus
from .models import APIKey, KeyRotationResult, KeyValidationResult


class APIKeyService:
    """Service for managing API keys with secure bcrypt hashing.

    **Feature: shared-modules-security-fixes**
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    """

    BCRYPT_COST_FACTOR = 12
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
        self._keys: dict[str, APIKey] = {}
        self._key_hashes: dict[str, str] = {}
        self._usage: dict[str, list[datetime]] = {}

    def _generate_key(self) -> str:
        """Generate a new API key."""
        random_part = secrets.token_urlsafe(32)
        return f"{self._key_prefix}{random_part}"

    def _hash_key(self, key: str) -> str:
        """Hash an API key using bcrypt with unique salt."""
        salt = bcrypt.gensalt(rounds=self.BCRYPT_COST_FACTOR)
        return bcrypt.hashpw(key.encode("utf-8"), salt).decode("utf-8")

    def _hash_key_sha256(self, key: str) -> str:
        """Legacy SHA256 hash (for migration support only)."""
        hash_value = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return f"{self.HASH_PREFIX_SHA256}{hash_value}"

    def _verify_key(self, key: str, key_hash: str) -> bool:
        """Verify key using constant-time comparison."""
        if key_hash.startswith(self.HASH_PREFIX_BCRYPT):
            return bcrypt.checkpw(key.encode("utf-8"), key_hash.encode("utf-8"))
        elif key_hash.startswith(self.HASH_PREFIX_SHA256):
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
        """Create a new API key."""
        raw_key = self._generate_key()
        key_hash = self._hash_key(raw_key)
        key_id = self._generate_key_id()

        expiry_days = expires_in_days or self._default_expiry_days
        expires_at = None
        if expiry_days > 0:
            expires_at = datetime.now(UTC) + timedelta(days=expiry_days)

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
        """Validate an API key using constant-time comparison."""
        key_id = self._find_key_id(raw_key)
        if key_id is None:
            return KeyValidationResult(valid=False, error="Invalid API key")

        api_key = self._keys.get(key_id)
        if api_key is None:
            return KeyValidationResult(valid=False, error="Key not found")

        error = self._check_key_status(api_key, required_scope)
        if error:
            return KeyValidationResult(valid=False, error=error)

        remaining = self._check_rate_limit(key_id, api_key.rate_limit)
        if remaining <= 0:
            return KeyValidationResult(
                valid=False, error="Rate limit exceeded", remaining_requests=0
            )

        api_key.last_used_at = datetime.now(UTC)
        self._record_usage(key_id)
        return KeyValidationResult(valid=True, key=api_key, remaining_requests=remaining - 1)

    def _find_key_id(self, raw_key: str) -> str | None:
        """Find key ID by verifying against stored hashes."""
        for stored_hash, stored_key_id in self._key_hashes.items():
            if self._verify_key(raw_key, stored_hash):
                return stored_key_id
        return None

    def _check_key_status(self, api_key: APIKey, required_scope: KeyScope | None) -> str | None:
        """Check key status and return error message if invalid."""
        if api_key.status == KeyStatus.REVOKED:
            return "Key has been revoked"
        if api_key.status == KeyStatus.ROTATED:
            return "Key has been rotated"
        if api_key.is_expired:
            return "Key has expired"
        if required_scope and not api_key.has_scope(required_scope):
            return f"Key does not have required scope: {required_scope.value}"
        return None

    def _check_rate_limit(self, key_id: str, limit: int) -> int:
        """Check rate limit and return remaining requests."""
        now = datetime.now(UTC)
        hour_ago = now - timedelta(hours=1)
        usage = self._usage.get(key_id, [])
        usage = [ts for ts in usage if ts > hour_ago]
        self._usage[key_id] = usage
        return limit - len(usage)

    def _record_usage(self, key_id: str) -> None:
        """Record API key usage."""
        if key_id not in self._usage:
            self._usage[key_id] = []
        self._usage[key_id].append(datetime.now(UTC))

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

        new_raw_key, new_api_key = self.create_key(
            client_id=old_key.client_id,
            name=old_key.name,
            scopes=old_key.scopes,
            rate_limit=old_key.rate_limit,
            metadata=old_key.metadata,
        )
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
            api_key.expires_at = datetime.now(UTC) + timedelta(days=days)
        else:
            api_key.expires_at = api_key.expires_at + timedelta(days=days)
        return True

    def get_usage_stats(self, key_id: str) -> dict[str, Any]:
        """Get usage statistics for a key."""
        api_key = self._keys.get(key_id)
        if api_key is None:
            return {}
        now = datetime.now(UTC)
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
            "last_used": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
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
    return APIKeyService(key_prefix=key_prefix, default_expiry_days=default_expiry_days)
