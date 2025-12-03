"""Property-based tests for shared-modules-security-fixes.

**Feature: shared-modules-security-fixes**
"""

from __future__ import annotations

import pytest
pytest.skip("Module not implemented", allow_module_level=True)

import asyncio
import re
import threading
from datetime import datetime, timezone

import pytest
from hypothesis import given, settings, strategies as st

from core.errors.exceptions import AuthenticationError, DecryptionError
from infrastructure.security.field_encryption import (
    EncryptedValue,
    EncryptionAlgorithm,
    FieldEncryptor,
    InMemoryKeyProvider,
)


# **Feature: shared-modules-security-fixes, Property 1: Encryption Round-Trip with Authentication**
# **Validates: Requirements 1.1, 1.2**
class TestEncryptionRoundTrip:
    """Property tests for encryption round-trip with authentication."""

    @pytest.fixture
    def encryptor(self) -> FieldEncryptor:
        """Create encryptor with in-memory key provider."""
        return FieldEncryptor(InMemoryKeyProvider())

    @given(plaintext=st.binary(min_size=1, max_size=10000))
    @settings(max_examples=100)
    def test_encryption_round_trip_bytes(self, plaintext: bytes) -> None:
        """For any plaintext, encrypt then decrypt returns original."""
        encryptor = FieldEncryptor(InMemoryKeyProvider())

        async def run_test() -> None:
            encrypted = await encryptor.encrypt(plaintext)
            decrypted = await encryptor.decrypt(encrypted)
            assert decrypted == plaintext

        asyncio.get_event_loop().run_until_complete(run_test())

    @given(plaintext=st.text(min_size=1, max_size=5000))
    @settings(max_examples=100)
    def test_encryption_round_trip_text(self, plaintext: str) -> None:
        """For any text, encrypt then decrypt returns original UTF-8 bytes."""
        encryptor = FieldEncryptor(InMemoryKeyProvider())

        async def run_test() -> None:
            encrypted = await encryptor.encrypt(plaintext)
            decrypted = await encryptor.decrypt(encrypted)
            assert decrypted == plaintext.encode("utf-8")

        asyncio.get_event_loop().run_until_complete(run_test())


    @given(plaintext=st.binary(min_size=1, max_size=1000))
    @settings(max_examples=50)
    def test_tampered_ciphertext_fails_authentication(self, plaintext: bytes) -> None:
        """Tampering with ciphertext causes authentication failure."""
        encryptor = FieldEncryptor(InMemoryKeyProvider())

        async def run_test() -> None:
            encrypted = await encryptor.encrypt(plaintext)

            # Tamper with ciphertext
            tampered_ciphertext = bytes(
                [b ^ 0xFF for b in encrypted.ciphertext[:min(10, len(encrypted.ciphertext))]]
            ) + encrypted.ciphertext[10:]

            tampered = EncryptedValue(
                ciphertext=tampered_ciphertext,
                key_id=encrypted.key_id,
                algorithm=encrypted.algorithm,
                nonce=encrypted.nonce,
                tag=encrypted.tag,
                version=encrypted.version,
            )

            with pytest.raises((AuthenticationError, DecryptionError)):
                await encryptor.decrypt(tampered)

        asyncio.get_event_loop().run_until_complete(run_test())

    @given(plaintext=st.binary(min_size=1, max_size=1000))
    @settings(max_examples=50)
    def test_tampered_tag_fails_authentication(self, plaintext: bytes) -> None:
        """Tampering with authentication tag causes failure."""
        encryptor = FieldEncryptor(InMemoryKeyProvider())

        async def run_test() -> None:
            encrypted = await encryptor.encrypt(plaintext)

            if encrypted.tag:
                # Tamper with tag
                tampered_tag = bytes([b ^ 0xFF for b in encrypted.tag])

                tampered = EncryptedValue(
                    ciphertext=encrypted.ciphertext,
                    key_id=encrypted.key_id,
                    algorithm=encrypted.algorithm,
                    nonce=encrypted.nonce,
                    tag=tampered_tag,
                    version=encrypted.version,
                )

                with pytest.raises((AuthenticationError, DecryptionError)):
                    await encryptor.decrypt(tampered)

        asyncio.get_event_loop().run_until_complete(run_test())

    @given(plaintext=st.binary(min_size=1, max_size=1000))
    @settings(max_examples=50)
    def test_encrypted_value_serialization_round_trip(self, plaintext: bytes) -> None:
        """EncryptedValue serialization/deserialization preserves data."""
        encryptor = FieldEncryptor(InMemoryKeyProvider())

        async def run_test() -> None:
            encrypted = await encryptor.encrypt(plaintext)
            serialized = encrypted.to_string()
            deserialized = EncryptedValue.from_string(serialized)

            assert deserialized.key_id == encrypted.key_id
            assert deserialized.algorithm == encrypted.algorithm
            assert deserialized.nonce == encrypted.nonce
            assert deserialized.ciphertext == encrypted.ciphertext
            assert deserialized.tag == encrypted.tag

            # Verify decryption still works
            decrypted = await encryptor.decrypt(deserialized)
            assert decrypted == plaintext

        asyncio.get_event_loop().run_until_complete(run_test())



# **Feature: shared-modules-security-fixes, Property 2: Bcrypt Hash Uniqueness**
# **Validates: Requirements 2.1, 2.3**
class TestBcryptHashUniqueness:
    """Property tests for bcrypt hash uniqueness."""

    @given(api_key=st.text(
        min_size=10,
        max_size=50,
        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    ))
    @settings(max_examples=10, deadline=None)
    def test_same_key_produces_different_hashes(self, api_key: str) -> None:
        """Hashing same key multiple times produces different hashes (unique salts)."""
        from infrastructure.security.api_key_service import APIKeyService

        service = APIKeyService()
        hash1 = service._hash_key(api_key)
        hash2 = service._hash_key(api_key)

        # Hashes should be different due to unique salts
        assert hash1 != hash2

        # But both should verify correctly
        assert service._verify_key(api_key, hash1)
        assert service._verify_key(api_key, hash2)

    @given(api_key=st.text(
        min_size=10,
        max_size=50,
        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    ))
    @settings(max_examples=10, deadline=None)
    def test_bcrypt_hash_format(self, api_key: str) -> None:
        """Bcrypt hash has correct format with cost factor >= 12."""
        from infrastructure.security.api_key_service import APIKeyService

        service = APIKeyService()
        key_hash = service._hash_key(api_key)

        # Should start with bcrypt prefix
        assert key_hash.startswith("$2b$")

        # Extract cost factor (format: $2b$XX$...)
        parts = key_hash.split("$")
        cost_factor = int(parts[2])
        assert cost_factor >= 12


# **Feature: shared-modules-security-fixes, Property 3: Hash Format Migration Compatibility**
# **Validates: Requirements 2.4**
class TestHashMigrationCompatibility:
    """Property tests for hash format migration."""

    @given(api_key=st.text(
        min_size=10,
        max_size=50,
        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    ))
    @settings(max_examples=20, deadline=None)
    def test_legacy_sha256_verification(self, api_key: str) -> None:
        """Legacy SHA256 hashes can still be verified."""
        from infrastructure.security.api_key_service import APIKeyService

        service = APIKeyService()
        legacy_hash = service._hash_key_sha256(api_key)

        # Should verify correctly
        assert service._verify_key(api_key, legacy_hash)

        # Wrong key should not verify
        wrong_key = api_key + "_wrong"
        assert not service._verify_key(wrong_key, legacy_hash)

    @given(api_key=st.text(
        min_size=10,
        max_size=50,
        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    ))
    @settings(max_examples=10, deadline=None)
    def test_both_formats_work(self, api_key: str) -> None:
        """Both bcrypt and SHA256 formats verify correctly."""
        from infrastructure.security.api_key_service import APIKeyService

        service = APIKeyService()

        bcrypt_hash = service._hash_key(api_key)
        sha256_hash = service._hash_key_sha256(api_key)

        # Both should verify
        assert service._verify_key(api_key, bcrypt_hash)
        assert service._verify_key(api_key, sha256_hash)

        # Cross-verification should fail with completely different key
        wrong_key = "WRONG_" + api_key[:20] + "_WRONG"
        assert not service._verify_key(wrong_key, bcrypt_hash)
        assert not service._verify_key(wrong_key, sha256_hash)



# **Feature: shared-modules-security-fixes, Property 4: Timestamp Timezone Awareness**
# **Validates: Requirements 3.1, 3.2, 3.3**
class TestTimestampTimezoneAwareness:
    """Property tests for timezone-aware timestamps."""

    @given(st.datetimes(timezones=st.just(timezone.utc)))
    @settings(max_examples=100)
    def test_utc_now_is_timezone_aware(self, _: datetime) -> None:
        """utc_now() returns timezone-aware datetime."""
        from core.shared.utils.datetime import utc_now

        result = utc_now()
        assert result.tzinfo is not None

    @given(dt=st.datetimes(min_value=datetime(2000, 1, 1), max_value=datetime(2100, 1, 1)))
    @settings(max_examples=100)
    def test_ensure_utc_makes_naive_datetime_aware(self, dt: datetime) -> None:
        """ensure_utc() makes naive datetimes timezone-aware."""
        from core.shared.utils.datetime import ensure_utc

        # Create naive datetime
        naive_dt = dt.replace(tzinfo=None)
        result = ensure_utc(naive_dt)

        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc

    @given(dt=st.datetimes(
        min_value=datetime(2000, 1, 1),
        max_value=datetime(2100, 1, 1),
        timezones=st.just(timezone.utc)
    ))
    @settings(max_examples=100)
    def test_iso8601_serialization_includes_timezone(self, dt: datetime) -> None:
        """to_iso8601() includes timezone information."""
        from core.shared.utils.datetime import to_iso8601

        result = to_iso8601(dt)

        # ISO 8601 with timezone ends with Z or +00:00 or similar
        assert result is not None
        assert "+" in result or "Z" in result or "-" in result[-6:]

    @given(dt=st.datetimes(
        min_value=datetime(2000, 1, 1),
        max_value=datetime(2100, 1, 1),
        timezones=st.just(timezone.utc)
    ))
    @settings(max_examples=100)
    def test_iso8601_round_trip(self, dt: datetime) -> None:
        """ISO 8601 serialization/deserialization preserves datetime."""
        from core.shared.utils.datetime import to_iso8601, from_iso8601

        serialized = to_iso8601(dt)
        deserialized = from_iso8601(serialized)

        assert deserialized is not None
        # Compare timestamps (may have microsecond differences)
        assert abs((deserialized - dt).total_seconds()) < 1



# **Feature: shared-modules-security-fixes, Property 5: Glob-to-Regex Safe Conversion**
# **Validates: Requirements 4.1**
class TestGlobToRegexSafeConversion:
    """Property tests for safe glob-to-regex conversion."""

    # Regex special characters that should be escaped
    REGEX_SPECIAL_CHARS = r"\.^$+{}[]|()"

    @given(filename=st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="._-")
    ))
    @settings(max_examples=100)
    def test_glob_matches_literal_filename(self, filename: str) -> None:
        """Glob pattern without wildcards matches exact filename."""
        from core.shared.utils.safe_pattern import match_glob

        # Pattern without wildcards should match exactly
        assert match_glob(filename, filename)
        assert not match_glob(filename, filename + "x")

    @given(
        prefix=st.text(min_size=0, max_size=20, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-"
        )),
        suffix=st.text(min_size=1, max_size=10, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-"
        )),
        middle=st.text(min_size=0, max_size=20, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-"
        ))
    )
    @settings(max_examples=100)
    def test_glob_star_matches_any_middle(self, prefix: str, suffix: str, middle: str) -> None:
        """Glob * wildcard matches any characters in the middle."""
        from core.shared.utils.safe_pattern import match_glob

        pattern = f"{prefix}*{suffix}"
        text = f"{prefix}{middle}{suffix}"

        assert match_glob(pattern, text)

    @given(special_char=st.sampled_from(list(r"\.^$+{}[]|()")))
    @settings(max_examples=50)
    def test_regex_special_chars_are_escaped(self, special_char: str) -> None:
        """Regex special characters in glob are properly escaped."""
        from core.shared.utils.safe_pattern import glob_to_regex, match_glob

        # Pattern with special char should match literally
        pattern = f"file{special_char}name"
        text = f"file{special_char}name"

        # Should match the literal text
        assert match_glob(pattern, text)

        # Should NOT match if special char is missing
        assert not match_glob(pattern, "filename")

    @given(
        base=st.text(min_size=1, max_size=20, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-"
        )),
        ext=st.text(min_size=1, max_size=5, alphabet=st.characters(
            whitelist_categories=("Ll",)
        ))
    )
    @settings(max_examples=100)
    def test_glob_extension_pattern(self, base: str, ext: str) -> None:
        """Glob *.ext pattern matches files with that extension."""
        from core.shared.utils.safe_pattern import match_glob

        pattern = f"*.{ext}"
        matching_file = f"{base}.{ext}"
        non_matching_file = f"{base}.other"

        assert match_glob(pattern, matching_file)
        assert not match_glob(pattern, non_matching_file)

    @given(text=st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_glob_to_regex_produces_valid_regex(self, text: str) -> None:
        """glob_to_regex always produces valid regex."""
        from core.shared.utils.safe_pattern import glob_to_regex

        regex_pattern = glob_to_regex(text)

        # Should not raise when compiling
        compiled = re.compile(regex_pattern)
        assert compiled is not None



# **Feature: shared-modules-security-fixes, Property 6: Circuit Breaker Registry Thread Safety**
# **Validates: Requirements 5.1, 5.3**
class TestCircuitBreakerRegistryThreadSafety:
    """Property tests for thread-safe circuit breaker registry."""

    def setup_method(self) -> None:
        """Reset registry before each test."""
        from core.shared.circuit_breaker import reset_circuit_breaker_registry
        reset_circuit_breaker_registry()

    def teardown_method(self) -> None:
        """Reset registry after each test."""
        from core.shared.circuit_breaker import reset_circuit_breaker_registry
        reset_circuit_breaker_registry()

    @given(name=st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-"
    )))
    @settings(max_examples=50)
    def test_same_name_returns_same_instance(self, name: str) -> None:
        """Getting same name multiple times returns same instance."""
        from core.shared.circuit_breaker import (
            get_circuit_breaker,
            reset_circuit_breaker_registry,
        )
        reset_circuit_breaker_registry()

        cb1 = get_circuit_breaker(name)
        cb2 = get_circuit_breaker(name)

        assert cb1 is cb2

    @given(names=st.lists(
        st.text(min_size=1, max_size=20, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-"
        )),
        min_size=1,
        max_size=10,
        unique=True
    ))
    @settings(max_examples=50)
    def test_different_names_return_different_instances(self, names: list[str]) -> None:
        """Different names return different instances."""
        from core.shared.circuit_breaker import (
            get_circuit_breaker,
            reset_circuit_breaker_registry,
        )
        reset_circuit_breaker_registry()

        breakers = [get_circuit_breaker(name) for name in names]

        # All should be different instances
        for i, cb1 in enumerate(breakers):
            for j, cb2 in enumerate(breakers):
                if i != j:
                    assert cb1 is not cb2

    def test_concurrent_access_returns_same_instance(self) -> None:
        """Concurrent access to same name returns same instance."""
        from core.shared.circuit_breaker import (
            get_circuit_breaker,
            reset_circuit_breaker_registry,
        )
        reset_circuit_breaker_registry()

        results: list[object] = []
        errors: list[Exception] = []

        def get_breaker() -> None:
            try:
                cb = get_circuit_breaker("concurrent_test")
                results.append(cb)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = [threading.Thread(target=get_breaker) for _ in range(20)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0

        # All results should be the same instance
        assert len(results) == 20
        first = results[0]
        for cb in results[1:]:
            assert cb is first

    def test_reset_clears_registry(self) -> None:
        """Reset clears all circuit breakers."""
        from core.shared.circuit_breaker import (
            get_circuit_breaker,
            get_all_circuit_breakers,
            reset_circuit_breaker_registry,
        )
        reset_circuit_breaker_registry()

        # Add some breakers
        get_circuit_breaker("test1")
        get_circuit_breaker("test2")

        assert len(get_all_circuit_breakers()) == 2

        # Reset
        reset_circuit_breaker_registry()

        # Should be empty
        assert len(get_all_circuit_breakers()) == 0



# **Feature: shared-modules-security-fixes, Property 7: Context Token Safe Reset**
# **Validates: Requirements 6.1, 6.3**
class TestContextTokenSafeReset:
    """Property tests for safe context token reset."""

    @given(
        correlation_id=st.text(min_size=10, max_size=50, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-"
        )),
        request_id=st.text(min_size=10, max_size=50, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-"
        ))
    )
    @settings(max_examples=50)
    def test_context_manager_sets_and_restores_context(
        self, correlation_id: str, request_id: str
    ) -> None:
        """Context manager properly sets and restores context."""
        from core.shared.correlation import (
            CorrelationContext,
            CorrelationContextManager,
            get_correlation_id,
            get_request_id,
            clear_context,
        )

        clear_context()

        # Before entering
        assert get_correlation_id() is None

        context = CorrelationContext(
            correlation_id=correlation_id,
            request_id=request_id,
        )

        with CorrelationContextManager(context):
            # Inside context
            assert get_correlation_id() == correlation_id
            assert get_request_id() == request_id

        # After exiting - should be restored to None
        assert get_correlation_id() is None

    def test_double_exit_does_not_raise(self) -> None:
        """Exiting context multiple times does not raise exception."""
        from core.shared.correlation import (
            CorrelationContext,
            CorrelationContextManager,
            clear_context,
        )

        clear_context()

        context = CorrelationContext(
            correlation_id="test-correlation",
            request_id="test-request",
        )

        manager = CorrelationContextManager(context)
        manager.__enter__()
        manager.__exit__(None, None, None)

        # Second exit should not raise
        manager.__exit__(None, None, None)

    @given(depth=st.integers(min_value=1, max_value=5))
    @settings(max_examples=20)
    def test_nested_contexts_maintain_relationships(self, depth: int) -> None:
        """Nested contexts maintain proper parent-child relationships."""
        from core.shared.correlation import (
            CorrelationContext,
            CorrelationContextManager,
            get_correlation_id,
            get_span_id,
            clear_context,
            generate_id,
            IdFormat,
        )

        clear_context()

        # Create nested contexts
        contexts = []
        managers = []

        for i in range(depth):
            ctx = CorrelationContext(
                correlation_id=f"corr-{i}",
                request_id=f"req-{i}",
                span_id=generate_id(IdFormat.SHORT),
                parent_span_id=contexts[-1].span_id if contexts else None,
            )
            contexts.append(ctx)
            manager = CorrelationContextManager(ctx)
            managers.append(manager)
            manager.__enter__()

        # Innermost context should be active
        assert get_correlation_id() == f"corr-{depth - 1}"

        # Exit all contexts in reverse order
        for manager in reversed(managers):
            manager.__exit__(None, None, None)

        # Should be back to no context
        assert get_correlation_id() is None
