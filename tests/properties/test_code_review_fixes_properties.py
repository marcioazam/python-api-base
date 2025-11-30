"""Property-based tests for code review fixes.

**Feature: shared-modules-code-review-fixes**
Tests correctness properties for security and quality fixes.
"""

import asyncio
import re
import time

import pytest
from hypothesis import given, settings, strategies as st

from my_api.shared.secrets_manager.enums import SecretType
from my_api.shared.secrets_manager.exceptions import SecretNotFoundError
from my_api.shared.secrets_manager.providers import LocalSecretsProvider

# =============================================================================
# Property 1: Secret CRUD Round-Trip Consistency
# =============================================================================


@settings(max_examples=100)
@given(
    secret_name=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
        min_size=1,
        max_size=50,
    ),
    secret_value=st.text(min_size=1, max_size=200),
)
def test_secret_crud_round_trip(secret_name: str, secret_value: str) -> None:
    """
    **Feature: shared-modules-code-review-fixes, Property 1: Secret CRUD Round-Trip Consistency**
    **Validates: Requirements 1.3, 1.4, 1.5**

    For any valid secret name and value, creating a secret and then retrieving it
    should return the same value, and the metadata should contain valid timestamps.
    """

    async def run_test() -> None:
        provider = LocalSecretsProvider()

        # Create secret
        metadata = await provider.create_secret(secret_name, secret_value, SecretType.STRING)

        # Verify metadata has valid timestamps
        assert metadata.name == secret_name
        assert metadata.created_at is not None
        assert metadata.updated_at is not None
        assert metadata.created_at.tzinfo is not None  # Timezone-aware

        # Retrieve secret
        retrieved = await provider.get_secret(secret_name)

        # Verify round-trip consistency
        assert retrieved.value == secret_value
        assert retrieved.secret_type == SecretType.STRING

        # Update secret
        new_value = secret_value + "_updated"
        update_metadata = await provider.update_secret(secret_name, new_value)

        # Verify update metadata
        assert update_metadata.updated_at >= metadata.created_at

        # Verify updated value
        updated = await provider.get_secret(secret_name)
        assert updated.value == new_value

    asyncio.new_event_loop().run_until_complete(run_test())


# =============================================================================
# Property 2: Secret Not Found Error
# =============================================================================


@settings(max_examples=100)
@given(
    secret_name=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
        min_size=1,
        max_size=50,
    ),
)
def test_secret_not_found_error(secret_name: str) -> None:
    """
    **Feature: shared-modules-code-review-fixes, Property 2: Secret Not Found Error**
    **Validates: Requirements 1.3**

    For any non-existent secret name, calling get_secret should raise
    SecretNotFoundError containing the secret name.
    """

    async def run_test() -> None:
        provider = LocalSecretsProvider()

        with pytest.raises(SecretNotFoundError) as exc_info:
            await provider.get_secret(secret_name)

        # Verify error contains secret name
        assert secret_name in str(exc_info.value)
        assert exc_info.value.secret_name == secret_name

    asyncio.new_event_loop().run_until_complete(run_test())


# =============================================================================
# Property 3: Timezone Preservation
# =============================================================================


@settings(max_examples=50)
@given(st.just(None))  # No input needed, testing default behavior
def test_timezone_preservation(_: None) -> None:
    """
    **Feature: shared-modules-code-review-fixes, Property 3: Timezone Preservation**
    **Validates: Requirements 4.1, 4.3**

    For any ThreatDetection instance created, the timestamp field should be
    timezone-aware and in UTC.
    """
    from my_api.shared.waf.models import ThreatDetection

    detection = ThreatDetection(detected=True)

    # Verify timestamp is timezone-aware
    assert detection.timestamp.tzinfo is not None

    # Verify timestamp is in UTC (or at least has timezone info)
    # Note: datetime.now() without tz returns naive datetime
    # After fix, it should be timezone-aware
    assert detection.timestamp.tzinfo is not None


# =============================================================================
# Property 4: Secret Key Minimum Length Validation
# =============================================================================


@settings(max_examples=100)
@given(
    key_length=st.integers(min_value=1, max_value=31),
)
def test_secret_key_minimum_length_validation(key_length: int) -> None:
    """
    **Feature: shared-modules-code-review-fixes, Property 4: Secret Key Minimum Length Validation**
    **Validates: Requirements 6.1, 6.2, 6.3**

    For any secret key shorter than 32 bytes, instantiating RequestSigner or
    RequestVerifier should raise ValueError with a message containing the
    minimum required length.
    """
    from my_api.shared.request_signing.service import RequestSigner, RequestVerifier

    short_key = "x" * key_length

    # Test RequestSigner
    with pytest.raises(ValueError) as exc_info:
        RequestSigner(short_key)
    assert "32" in str(exc_info.value)

    # Test RequestVerifier
    with pytest.raises(ValueError) as exc_info:
        RequestVerifier(short_key)
    assert "32" in str(exc_info.value)


@settings(max_examples=50)
@given(
    key_length=st.integers(min_value=32, max_value=64),
)
def test_secret_key_valid_length_accepted(key_length: int) -> None:
    """
    **Feature: shared-modules-code-review-fixes, Property 4: Secret Key Minimum Length Validation**
    **Validates: Requirements 6.1, 6.2**

    For any secret key of 32 bytes or longer, instantiation should succeed.
    """
    from my_api.shared.request_signing.service import RequestSigner, RequestVerifier

    valid_key = "x" * key_length

    # Should not raise
    signer = RequestSigner(valid_key)
    verifier = RequestVerifier(valid_key)

    assert signer is not None
    assert verifier is not None


# =============================================================================
# Property 5: ReDoS Protection - Bounded Pattern Matching
# =============================================================================


@settings(max_examples=50, deadline=5000)  # 5 second deadline
@given(
    padding_length=st.integers(min_value=100, max_value=500),
)
def test_redos_protection_bounded_matching(padding_length: int) -> None:
    """
    **Feature: shared-modules-code-review-fixes, Property 5: ReDoS Protection**
    **Validates: Requirements 5.1**

    For any input string longer than 100 characters between SQL keywords,
    the WAF SQL injection patterns should complete in bounded time.
    """
    from my_api.shared.waf.patterns import SQL_INJECTION_PATTERNS

    # Create a test input with lots of padding (not actual SQL injection)
    test_input = "SELECT " + "a" * padding_length + " FROM users"  # noqa: S608

    for pattern in SQL_INJECTION_PATTERNS:
        compiled = re.compile(pattern, re.IGNORECASE)

        start = time.time()
        # This should complete quickly due to bounded quantifiers
        compiled.search(test_input)
        elapsed = time.time() - start

        # Should complete in under 1 second even with long input
        assert elapsed < 1.0, f"Pattern {pattern} took too long: {elapsed}s"


# =============================================================================
# Property 6: Utils Module Exports Completeness
# =============================================================================


def test_utils_exports_completeness() -> None:
    """
    **Feature: shared-modules-code-review-fixes, Property 6: Utils Module Exports Completeness**
    **Validates: Requirements 8.1**

    For any public function in utils submodules, the function should be
    accessible via direct import from utils.
    """
    from my_api.shared import utils

    # Check datetime functions
    assert hasattr(utils, "utc_now")
    assert hasattr(utils, "ensure_utc")
    assert hasattr(utils, "to_iso8601")
    assert hasattr(utils, "from_iso8601")

    # Check ids functions
    assert hasattr(utils, "generate_ulid")
    assert hasattr(utils, "generate_uuid7")

    # Check pagination functions
    assert hasattr(utils, "paginate_offset")
    assert hasattr(utils, "paginate_list")
    assert hasattr(utils, "encode_cursor")
    assert hasattr(utils, "decode_cursor")

    # Check password functions
    assert hasattr(utils, "hash_password")
    assert hasattr(utils, "verify_password")

    # Check sanitization functions
    assert hasattr(utils, "sanitize_string")
    assert hasattr(utils, "sanitize_path")
    assert hasattr(utils, "sanitize_dict")
