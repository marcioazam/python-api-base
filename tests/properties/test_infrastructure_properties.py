"""Property-based tests for infrastructure layer.

**Feature: infrastructure-code-review**
Tests correctness properties for database, token store, audit, telemetry, and logging.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from hypothesis import given, settings, strategies as st


@st.composite
def valid_jti_strategy(draw):
    return draw(st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
    ).filter(lambda x: x.strip() != ""))


@st.composite
def valid_user_id_strategy(draw):
    return draw(st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
    ).filter(lambda x: x.strip() != ""))


@settings(max_examples=100)
@given(st.text(max_size=50))
def test_empty_database_url_raises_value_error(url):
    from my_app.infrastructure.database.session import DatabaseSession
    if not url or not url.strip():
        with pytest.raises(ValueError, match="database_url cannot be empty"):
            DatabaseSession(database_url=url)


@settings(max_examples=100)
@given(st.integers(max_value=0))
def test_invalid_pool_size_raises_value_error(pool_size):
    from my_app.infrastructure.database.session import DatabaseSession
    with pytest.raises(ValueError, match="pool_size must be >= 1"):
        DatabaseSession(
            database_url="postgresql+asyncpg://localhost/test",
            pool_size=pool_size,
        )


@settings(max_examples=100)
@given(st.integers(max_value=-1))
def test_invalid_max_overflow_raises_value_error(max_overflow):
    from my_app.infrastructure.database.session import DatabaseSession
    with pytest.raises(ValueError, match="max_overflow must be >= 0"):
        DatabaseSession(
            database_url="postgresql+asyncpg://localhost/test",
            max_overflow=max_overflow,
        )


@settings(max_examples=100)
@given(st.text(max_size=50))
def test_empty_jti_raises_value_error(jti):
    from my_app.infrastructure.auth.token_store import InMemoryTokenStore
    if not jti or not jti.strip():
        store = InMemoryTokenStore()
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        with pytest.raises(ValueError, match="jti"):
            asyncio.get_event_loop().run_until_complete(
                store.store(jti=jti, user_id="user123", expires_at=expires)
            )


@settings(max_examples=100)
@given(st.text(max_size=50))
def test_empty_user_id_raises_value_error(user_id):
    from my_app.infrastructure.auth.token_store import InMemoryTokenStore
    if not user_id or not user_id.strip():
        store = InMemoryTokenStore()
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        with pytest.raises(ValueError, match="user_id"):
            asyncio.get_event_loop().run_until_complete(
                store.store(jti="token123", user_id=user_id, expires_at=expires)
            )


@settings(max_examples=100)
@given(
    jti=valid_jti_strategy(),
    user_id=valid_user_id_strategy(),
    revoked=st.booleans(),
)
def test_stored_token_round_trip(jti, user_id, revoked):
    from my_app.infrastructure.auth.token_store import StoredToken
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=1)
    original = StoredToken(jti=jti, user_id=user_id, created_at=now, expires_at=expires, revoked=revoked)
    data = original.to_dict()
    restored = StoredToken.from_dict(data)
    assert restored.jti == original.jti
    assert restored.user_id == original.user_id
    assert restored.revoked == original.revoked


@settings(max_examples=50)
@given(num_tokens=st.integers(min_value=1, max_value=10))
def test_revoke_all_for_user_revokes_all_tokens(num_tokens):
    from my_app.infrastructure.auth.token_store import InMemoryTokenStore
    store = InMemoryTokenStore()
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    user_id = "test_user"
    for i in range(num_tokens):
        asyncio.get_event_loop().run_until_complete(
            store.store(jti=f"token_{i}", user_id=user_id, expires_at=expires)
        )
    count = asyncio.get_event_loop().run_until_complete(store.revoke_all_for_user(user_id))
    assert count == num_tokens


@settings(max_examples=100)
@given(
    entry_id=valid_jti_strategy(),
    action=st.sampled_from(["login", "logout", "create", "update", "delete"]),
    resource_type=valid_jti_strategy(),
    result=st.sampled_from(["success", "failure", "error"]),
)
def test_audit_entry_round_trip(entry_id, action, resource_type, result):
    from my_app.infrastructure.audit import AuditEntry
    original = AuditEntry(
        id=entry_id,
        timestamp=datetime.now(timezone.utc),
        action=action,
        resource_type=resource_type,
        result=result,
        details={"key": "value"},
    )
    data = original.to_dict()
    restored = AuditEntry.from_dict(data)
    assert restored.id == original.id
    assert restored.action == original.action


@settings(max_examples=50)
@given(
    action=st.sampled_from(["login", "logout", "create"]),
    resource_type=valid_jti_strategy(),
)
def test_log_action_creates_utc_timestamp(action, resource_type):
    from my_app.infrastructure.audit import InMemoryAuditLogger
    logger = InMemoryAuditLogger()
    entry = asyncio.get_event_loop().run_until_complete(
        logger.log_action(action=action, resource_type=resource_type)
    )
    assert entry.timestamp.tzinfo is not None
    assert entry.timestamp.tzinfo == timezone.utc


@settings(max_examples=20)
@given(num_calls=st.integers(min_value=1, max_value=5))
def test_multiple_initialize_calls_are_idempotent(num_calls):
    from my_app.infrastructure.observability.telemetry import TelemetryProvider
    provider = TelemetryProvider(service_name="test", enable_tracing=False, enable_metrics=False)
    for _ in range(num_calls):
        provider.initialize()
    assert provider._initialized is True


def test_traced_decorator_preserves_sync_function():
    from my_app.infrastructure.observability.telemetry import traced
    @traced(name="test_sync")
    def sync_func(x):
        return x * 2
    result = sync_func(5)
    assert result == 10


def test_traced_decorator_preserves_async_function():
    from my_app.infrastructure.observability.telemetry import traced
    @traced(name="test_async")
    async def async_func(x):
        return x * 2
    result = asyncio.get_event_loop().run_until_complete(async_func(5))
    assert result == 10


@settings(max_examples=100)
@given(
    pii_key=st.sampled_from(["password", "secret", "token", "api_key", "credential"]),
    value=st.text(min_size=1, max_size=50),
)
def test_pii_keys_are_redacted(pii_key, value):
    from my_app.infrastructure.logging.config import redact_pii
    import logging
    event_dict = {pii_key: value, "safe_key": "safe_value"}
    result = redact_pii(logging.getLogger(), "info", event_dict)
    assert result[pii_key] == "[REDACTED]"
    assert result["safe_key"] == "safe_value"


@settings(max_examples=100)
@given(request_id=valid_jti_strategy())
def test_request_id_is_retrievable_after_set(request_id):
    from my_app.infrastructure.logging.config import set_request_id, get_request_id, clear_request_id
    try:
        set_request_id(request_id)
        retrieved = get_request_id()
        assert retrieved == request_id
    finally:
        clear_request_id()


def test_request_id_is_none_after_clear():
    from my_app.infrastructure.logging.config import set_request_id, get_request_id, clear_request_id
    set_request_id("test-id")
    clear_request_id()
    assert get_request_id() is None


def test_database_session_raises_value_error_for_invalid_input():
    from my_app.infrastructure.database.session import DatabaseSession
    with pytest.raises(ValueError):
        DatabaseSession(database_url="")
    with pytest.raises(ValueError):
        DatabaseSession(database_url="valid", pool_size=0)
    with pytest.raises(ValueError):
        DatabaseSession(database_url="valid", max_overflow=-1)
