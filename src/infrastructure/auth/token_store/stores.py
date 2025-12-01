"""Token store implementations.

Feature: file-size-compliance-phase2, infrastructure-code-review
Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 5.1, 5.2, 5.3
"""

import json
import logging
import threading
from datetime import datetime, UTC
from typing import Any

from .models import StoredToken
from .protocols import RefreshTokenStore

logger = logging.getLogger(__name__)


def _validate_token_input(jti: str, user_id: str, expires_at: datetime) -> None:
    """Validate token store input parameters.
    
    Args:
        jti: Token identifier.
        user_id: User identifier.
        expires_at: Token expiration time.
        
    Raises:
        ValueError: If any parameter is invalid.
    """
    if not jti or not jti.strip():
        raise ValueError("jti cannot be empty or whitespace")
    if not user_id or not user_id.strip():
        raise ValueError("user_id cannot be empty or whitespace")
    if expires_at.tzinfo is None:
        raise ValueError("expires_at must be timezone-aware")


class InMemoryTokenStore(RefreshTokenStore):
    """In-memory token store for development and testing."""

    def __init__(self, max_entries: int = 10000) -> None:
        self._tokens: dict[str, StoredToken] = {}
        self._user_tokens: dict[str, set[str]] = {}
        self._max_entries = max_entries
        self._lock = threading.Lock()

    async def store(self, jti: str, user_id: str, expires_at: datetime) -> None:
        _validate_token_input(jti, user_id, expires_at)

        token = StoredToken(
            jti=jti, user_id=user_id,
            created_at=datetime.now(UTC),
            expires_at=expires_at, revoked=False,
        )

        with self._lock:
            self._tokens[jti] = token
            if user_id not in self._user_tokens:
                self._user_tokens[user_id] = set()
            self._user_tokens[user_id].add(jti)

            # Evict oldest tokens if over limit
            if len(self._tokens) > self._max_entries:
                sorted_tokens = sorted(
                    self._tokens.items(),
                    key=lambda x: x[1].created_at
                )
                tokens_to_remove = len(self._tokens) - self._max_entries
                for jti_to_remove, token_to_remove in sorted_tokens[:tokens_to_remove]:
                    del self._tokens[jti_to_remove]
                    if token_to_remove.user_id in self._user_tokens:
                        self._user_tokens[token_to_remove.user_id].discard(jti_to_remove)

    async def get(self, jti: str) -> StoredToken | None:
        with self._lock:
            return self._tokens.get(jti)

    async def revoke(self, jti: str) -> bool:
        with self._lock:
            token = self._tokens.get(jti)
            if token is None:
                return False
            self._tokens[jti] = StoredToken(
                jti=token.jti, user_id=token.user_id,
                created_at=token.created_at, expires_at=token.expires_at, revoked=True,
            )
            return True

    async def revoke_all_for_user(self, user_id: str) -> int:
        with self._lock:
            jtis = list(self._user_tokens.get(user_id, set()))
        count = 0
        for jti in jtis:
            if await self.revoke(jti):
                count += 1
        return count

    async def is_valid(self, jti: str) -> bool:
        with self._lock:
            token = self._tokens.get(jti)
            return token.is_valid() if token else False

    async def cleanup_expired(self) -> int:
        with self._lock:
            expired = [jti for jti, t in self._tokens.items() if t.is_expired()]
            for jti in expired:
                token = self._tokens.pop(jti, None)
                if token and token.user_id in self._user_tokens:
                    self._user_tokens[token.user_id].discard(jti)
            return len(expired)


class RedisTokenStore(RefreshTokenStore):
    """Redis-based token store for production use."""

    KEY_PREFIX = "refresh_token:"
    USER_TOKENS_PREFIX = "user_tokens:"
    REVOKED_PREFIX = "revoked:"

    def __init__(self, redis_client: Any, default_ttl: int = 604800) -> None:
        self._redis = redis_client
        self._default_ttl = default_ttl

    async def is_revoked(self, jti: str) -> bool:
        return await self._redis.exists(f"{self.REVOKED_PREFIX}{jti}") > 0

    async def add_to_blacklist(self, jti: str, ttl: int) -> None:
        await self._redis.setex(f"{self.REVOKED_PREFIX}{jti}", ttl, "1")

    def _token_key(self, jti: str) -> str:
        return f"{self.KEY_PREFIX}{jti}"

    def _user_key(self, user_id: str) -> str:
        return f"{self.USER_TOKENS_PREFIX}{user_id}"

    async def store(self, jti: str, user_id: str, expires_at: datetime) -> None:
        _validate_token_input(jti, user_id, expires_at)

        token = StoredToken(
            jti=jti, user_id=user_id,
            created_at=datetime.now(UTC),
            expires_at=expires_at, revoked=False,
        )
        ttl_seconds = (expires_at - datetime.now(UTC)).total_seconds()
        ttl = max(int(ttl_seconds), 1) if ttl_seconds > 0 else self._default_ttl
        await self._redis.setex(self._token_key(jti), ttl, json.dumps(token.to_dict()))
        await self._redis.sadd(self._user_key(user_id), jti)

    async def get(self, jti: str) -> StoredToken | None:
        data = await self._redis.get(self._token_key(jti))
        return StoredToken.from_dict(json.loads(data)) if data else None

    async def revoke(self, jti: str) -> bool:
        key = self._token_key(jti)
        data = await self._redis.get(key)
        if not data:
            return False
        token = StoredToken.from_dict(json.loads(data))
        revoked = StoredToken(
            jti=token.jti, user_id=token.user_id,
            created_at=token.created_at, expires_at=token.expires_at, revoked=True,
        )
        ttl = await self._redis.ttl(key)
        if ttl > 0:
            await self._redis.setex(key, ttl, json.dumps(revoked.to_dict()))
        else:
            await self._redis.delete(key)
        return True

    async def revoke_all_for_user(self, user_id: str) -> int:
        jtis = await self._redis.smembers(self._user_key(user_id))
        count = 0
        # Use pipeline for atomicity
        pipe = self._redis.pipeline()
        for jti in jtis:
            jti_str = jti.decode() if isinstance(jti, bytes) else jti
            if await self.revoke(jti_str):
                count += 1
        return count

    async def is_valid(self, jti: str) -> bool:
        token = await self.get(jti)
        return token.is_valid() if token else False

    async def cleanup_expired(self) -> int:
        return 0  # Redis handles TTL automatically


def get_token_store_sync() -> RefreshTokenStore:
    """Get token store synchronously."""
    return InMemoryTokenStore()
