"""Property-based tests for Distributed Locking.

**Feature: api-architecture-analysis, Property 8: Distributed locking**
**Validates: Requirements 9.3**
"""

import asyncio
from datetime import datetime, timedelta

import pytest
from hypothesis import given, settings, strategies as st

from my_api.shared.distributed_lock import (
    InMemoryDistributedLock,
    LockAcquisitionError,
    LockInfo,
    LockManager,
    LockRenewalError,
)


identifier_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz_"),
    min_size=1,
    max_size=20,
)


class TestLockInfo:
    """Tests for LockInfo."""

    def test_ttl_seconds_calculation(self):
        """ttl_seconds should calculate remaining time."""
        now = datetime.utcnow()
        info = LockInfo(
            key="test",
            token="token",
            acquired_at=now,
            expires_at=now + timedelta(seconds=30),
        )
        assert info.ttl_seconds > 0
        assert info.ttl_seconds <= 30

    def test_is_expired_false_when_valid(self):
        """is_expired should be False when not expired."""
        now = datetime.utcnow()
        info = LockInfo(
            key="test",
            token="token",
            acquired_at=now,
            expires_at=now + timedelta(seconds=30),
        )
        assert info.is_expired is False

    def test_is_expired_true_when_expired(self):
        """is_expired should be True when expired."""
        now = datetime.utcnow()
        info = LockInfo(
            key="test",
            token="token",
            acquired_at=now - timedelta(seconds=60),
            expires_at=now - timedelta(seconds=30),
        )
        assert info.is_expired is True


class TestInMemoryDistributedLock:
    """Tests for InMemoryDistributedLock."""

    @pytest.mark.asyncio
    @given(key=identifier_strategy)
    @settings(max_examples=20)
    async def test_acquire_returns_lock_info(self, key: str):
        """acquire should return LockInfo."""
        lock = InMemoryDistributedLock()
        info = await lock.acquire(key, ttl_seconds=10)
        assert info.key == key
        assert info.token is not None
        await lock.release(info)

    @pytest.mark.asyncio
    async def test_acquire_same_key_fails(self):
        """acquire should fail for already locked key."""
        lock = InMemoryDistributedLock()
        info = await lock.acquire("test", ttl_seconds=10)
        with pytest.raises(LockAcquisitionError):
            await lock.acquire("test", ttl_seconds=10)
        await lock.release(info)

    @pytest.mark.asyncio
    async def test_acquire_with_wait_timeout(self):
        """acquire should wait and timeout."""
        lock = InMemoryDistributedLock()
        info = await lock.acquire("test", ttl_seconds=10)
        with pytest.raises(LockAcquisitionError):
            await lock.acquire("test", ttl_seconds=10, wait_timeout=0.2)
        await lock.release(info)

    @pytest.mark.asyncio
    async def test_release_returns_true(self):
        """release should return True for valid lock."""
        lock = InMemoryDistributedLock()
        info = await lock.acquire("test", ttl_seconds=10)
        result = await lock.release(info)
        assert result is True

    @pytest.mark.asyncio
    async def test_release_wrong_token_returns_false(self):
        """release should return False for wrong token."""
        lock = InMemoryDistributedLock()
        info = await lock.acquire("test", ttl_seconds=10)
        fake_info = LockInfo(
            key="test",
            token="wrong-token",
            acquired_at=info.acquired_at,
            expires_at=info.expires_at,
        )
        result = await lock.release(fake_info)
        assert result is False
        await lock.release(info)


    @pytest.mark.asyncio
    async def test_renew_extends_ttl(self):
        """renew should extend lock TTL."""
        lock = InMemoryDistributedLock()
        info = await lock.acquire("test", ttl_seconds=5)
        original_expires = info.expires_at
        new_info = await lock.renew(info, ttl_seconds=30)
        assert new_info.expires_at > original_expires
        await lock.release(new_info)

    @pytest.mark.asyncio
    async def test_renew_wrong_token_raises(self):
        """renew should raise for wrong token."""
        lock = InMemoryDistributedLock()
        info = await lock.acquire("test", ttl_seconds=10)
        fake_info = LockInfo(
            key="test",
            token="wrong-token",
            acquired_at=info.acquired_at,
            expires_at=info.expires_at,
        )
        with pytest.raises(LockRenewalError):
            await lock.renew(fake_info, ttl_seconds=30)
        await lock.release(info)

    @pytest.mark.asyncio
    async def test_is_locked_true_when_locked(self):
        """is_locked should return True when locked."""
        lock = InMemoryDistributedLock()
        info = await lock.acquire("test", ttl_seconds=10)
        assert await lock.is_locked("test") is True
        await lock.release(info)

    @pytest.mark.asyncio
    async def test_is_locked_false_when_not_locked(self):
        """is_locked should return False when not locked."""
        lock = InMemoryDistributedLock()
        assert await lock.is_locked("test") is False

    @pytest.mark.asyncio
    async def test_lock_context_manager(self):
        """lock context manager should acquire and release."""
        lock = InMemoryDistributedLock()
        async with lock.lock("test", ttl_seconds=10) as info:
            assert info.key == "test"
            assert await lock.is_locked("test") is True
        assert await lock.is_locked("test") is False

    @pytest.mark.asyncio
    async def test_expired_lock_cleanup(self):
        """Expired locks should be cleaned up."""
        lock = InMemoryDistributedLock()
        info = await lock.acquire("test", ttl_seconds=0.1)
        await asyncio.sleep(0.2)
        assert await lock.is_locked("test") is False

    def test_get_lock_count(self):
        """get_lock_count should return correct count."""
        lock = InMemoryDistributedLock()
        assert lock.get_lock_count() == 0


class TestLockManager:
    """Tests for LockManager."""

    @pytest.mark.asyncio
    async def test_acquire_with_renewal(self):
        """acquire_with_renewal should acquire lock."""
        lock = InMemoryDistributedLock()
        manager = LockManager(lock, renewal_interval=1.0)
        info = await manager.acquire_with_renewal("test", ttl_seconds=10)
        assert info.key == "test"
        await manager.release_with_renewal(info)

    @pytest.mark.asyncio
    async def test_release_with_renewal(self):
        """release_with_renewal should release lock."""
        lock = InMemoryDistributedLock()
        manager = LockManager(lock, renewal_interval=1.0)
        info = await manager.acquire_with_renewal("test", ttl_seconds=10)
        result = await manager.release_with_renewal(info)
        assert result is True
        assert await lock.is_locked("test") is False

    @pytest.mark.asyncio
    async def test_lock_context_manager(self):
        """lock context manager should work with renewal."""
        lock = InMemoryDistributedLock()
        manager = LockManager(lock, renewal_interval=1.0)
        async with manager.lock("test", ttl_seconds=10) as info:
            assert info.key == "test"
            assert await lock.is_locked("test") is True
        assert await lock.is_locked("test") is False
