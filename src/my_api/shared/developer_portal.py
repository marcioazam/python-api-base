"""Developer Portal with self-service API key management."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Protocol
import secrets
import hashlib


class SubscriptionTier(Enum):
    """API subscription tiers."""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


@dataclass
class TierLimits:
    """Rate limits per tier."""
    requests_per_minute: int
    requests_per_day: int
    max_api_keys: int
    features: list[str] = field(default_factory=list)


TIER_LIMITS: dict[SubscriptionTier, TierLimits] = {
    SubscriptionTier.FREE: TierLimits(60, 1000, 1, ["basic"]),
    SubscriptionTier.STARTER: TierLimits(300, 10000, 3, ["basic", "webhooks"]),
    SubscriptionTier.PROFESSIONAL: TierLimits(1000, 100000, 10, ["basic", "webhooks", "analytics"]),
    SubscriptionTier.ENTERPRISE: TierLimits(10000, 1000000, 100, ["basic", "webhooks", "analytics", "sla"]),
}


@dataclass
class Developer:
    """Developer account."""
    id: str
    email: str
    name: str
    tier: SubscriptionTier = SubscriptionTier.FREE
    created_at: datetime = field(default_factory=datetime.utcnow)
    api_keys: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class APIKeyInfo:
    """API key information."""
    key_id: str
    key_hash: str
    developer_id: str
    name: str
    created_at: datetime
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    scopes: list[str] = field(default_factory=list)
    is_active: bool = True


@dataclass
class UsageStats:
    """API usage statistics."""
    developer_id: str
    period_start: datetime
    period_end: datetime
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0
    endpoints: dict[str, int] = field(default_factory=dict)


class DeveloperStore(Protocol):
    """Protocol for developer storage."""

    async def get(self, developer_id: str) -> Developer | None: ...
    async def save(self, developer: Developer) -> None: ...
    async def get_by_email(self, email: str) -> Developer | None: ...


class APIKeyStore(Protocol):
    """Protocol for API key storage."""

    async def get(self, key_id: str) -> APIKeyInfo | None: ...
    async def get_by_hash(self, key_hash: str) -> APIKeyInfo | None: ...
    async def save(self, key_info: APIKeyInfo) -> None: ...
    async def list_by_developer(self, developer_id: str) -> list[APIKeyInfo]: ...
    async def delete(self, key_id: str) -> bool: ...


class UsageStore(Protocol):
    """Protocol for usage statistics storage."""

    async def record(self, developer_id: str, endpoint: str, success: bool, latency_ms: float) -> None: ...
    async def get_stats(self, developer_id: str, start: datetime, end: datetime) -> UsageStats: ...


class DeveloperPortal:
    """Self-service developer portal."""

    def __init__(
        self,
        developer_store: DeveloperStore,
        api_key_store: APIKeyStore,
        usage_store: UsageStore
    ) -> None:
        self._developers = developer_store
        self._api_keys = api_key_store
        self._usage = usage_store

    def _hash_key(self, key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()

    async def register_developer(
        self,
        email: str,
        name: str,
        tier: SubscriptionTier = SubscriptionTier.FREE
    ) -> Developer:
        """Register a new developer."""
        import uuid
        existing = await self._developers.get_by_email(email)
        if existing:
            raise ValueError("Email already registered")

        developer = Developer(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            tier=tier
        )
        await self._developers.save(developer)
        return developer

    async def create_api_key(
        self,
        developer_id: str,
        name: str,
        scopes: list[str] | None = None,
        expires_in_days: int | None = None
    ) -> tuple[str, APIKeyInfo]:
        """Create a new API key for developer."""
        import uuid
        developer = await self._developers.get(developer_id)
        if not developer:
            raise ValueError("Developer not found")

        limits = TIER_LIMITS[developer.tier]
        existing_keys = await self._api_keys.list_by_developer(developer_id)
        if len(existing_keys) >= limits.max_api_keys:
            raise ValueError(f"Maximum API keys ({limits.max_api_keys}) reached")

        raw_key = f"sk_{secrets.token_urlsafe(32)}"
        key_hash = self._hash_key(raw_key)

        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        key_info = APIKeyInfo(
            key_id=str(uuid.uuid4()),
            key_hash=key_hash,
            developer_id=developer_id,
            name=name,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            scopes=scopes or []
        )
        await self._api_keys.save(key_info)
        return raw_key, key_info

    async def validate_api_key(self, raw_key: str) -> APIKeyInfo | None:
        """Validate an API key."""
        key_hash = self._hash_key(raw_key)
        key_info = await self._api_keys.get_by_hash(key_hash)

        if not key_info or not key_info.is_active:
            return None

        if key_info.expires_at and key_info.expires_at < datetime.now(timezone.utc):
            return None

        return key_info

    async def revoke_api_key(self, developer_id: str, key_id: str) -> bool:
        """Revoke an API key."""
        key_info = await self._api_keys.get(key_id)
        if not key_info or key_info.developer_id != developer_id:
            return False
        return await self._api_keys.delete(key_id)

    async def get_usage_stats(
        self,
        developer_id: str,
        days: int = 30
    ) -> UsageStats:
        """Get usage statistics for developer."""
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        return await self._usage.get_stats(developer_id, start, end)

    async def upgrade_tier(
        self,
        developer_id: str,
        new_tier: SubscriptionTier
    ) -> Developer:
        """Upgrade developer subscription tier."""
        developer = await self._developers.get(developer_id)
        if not developer:
            raise ValueError("Developer not found")
        developer.tier = new_tier
        await self._developers.save(developer)
        return developer


class InMemoryDeveloperStore:
    """In-memory developer store for testing."""

    def __init__(self) -> None:
        self._developers: dict[str, Developer] = {}

    async def get(self, developer_id: str) -> Developer | None:
        return self._developers.get(developer_id)

    async def save(self, developer: Developer) -> None:
        self._developers[developer.id] = developer

    async def get_by_email(self, email: str) -> Developer | None:
        for dev in self._developers.values():
            if dev.email == email:
                return dev
        return None


class InMemoryAPIKeyStore:
    """In-memory API key store for testing."""

    def __init__(self) -> None:
        self._keys: dict[str, APIKeyInfo] = {}

    async def get(self, key_id: str) -> APIKeyInfo | None:
        return self._keys.get(key_id)

    async def get_by_hash(self, key_hash: str) -> APIKeyInfo | None:
        for key in self._keys.values():
            if key.key_hash == key_hash:
                return key
        return None

    async def save(self, key_info: APIKeyInfo) -> None:
        self._keys[key_info.key_id] = key_info

    async def list_by_developer(self, developer_id: str) -> list[APIKeyInfo]:
        return [k for k in self._keys.values() if k.developer_id == developer_id]

    async def delete(self, key_id: str) -> bool:
        if key_id in self._keys:
            del self._keys[key_id]
            return True
        return False
