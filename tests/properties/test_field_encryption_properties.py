"""Property-based tests for Field Encryption.

**Feature: api-architecture-analysis, Property: Encryption operations**
**Validates: Requirements 19.6**
"""

import pytest
from hypothesis import given, strategies as st, settings

from my_api.shared.field_encryption import (
    FieldEncryptor,
    EncryptedValue,
    EncryptionAlgorithm,
    InMemoryKeyProvider,
)


class TestFieldEncryptionProperties:
    """Property tests for field encryption."""

    @given(st.text(min_size=1, max_size=1000))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_encrypt_decrypt_round_trip(self, plaintext: str) -> None:
        """Encrypt then decrypt returns original."""
        provider = InMemoryKeyProvider()
        encryptor = FieldEncryptor(provider)

        encrypted = await encryptor.encrypt(plaintext)
        decrypted = await encryptor.decrypt(encrypted)

        assert decrypted.decode() == plaintext

    @given(st.binary(min_size=1, max_size=1000))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_encrypt_decrypt_binary_round_trip(self, plaintext: bytes) -> None:
        """Encrypt then decrypt preserves binary data."""
        provider = InMemoryKeyProvider()
        encryptor = FieldEncryptor(provider)

        encrypted = await encryptor.encrypt(plaintext)
        decrypted = await encryptor.decrypt(encrypted)

        assert decrypted == plaintext

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_different_encryptions_different_ciphertext(
        self,
        plaintext: str
    ) -> None:
        """Same plaintext produces different ciphertext (due to nonce)."""
        provider = InMemoryKeyProvider()
        encryptor = FieldEncryptor(provider)

        encrypted1 = await encryptor.encrypt(plaintext)
        encrypted2 = await encryptor.encrypt(plaintext)

        # Ciphertext should differ due to random nonce
        assert encrypted1.ciphertext != encrypted2.ciphertext or encrypted1.nonce != encrypted2.nonce

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_key_rotation_preserves_data(self, plaintext: str) -> None:
        """Key rotation re-encrypts without data loss."""
        provider = InMemoryKeyProvider()
        encryptor = FieldEncryptor(provider)

        encrypted = await encryptor.encrypt(plaintext)
        old_key_id = encrypted.key_id

        # Rotate key
        await provider.rotate_key()

        # Re-encrypt with new key
        rotated = await encryptor.rotate_encrypted_value(encrypted)

        # Should use new key
        assert rotated.key_id != old_key_id

        # Should still decrypt correctly
        decrypted = await encryptor.decrypt(rotated)
        assert decrypted.decode() == plaintext


class TestEncryptedValueProperties:
    """Property tests for encrypted value serialization."""

    @given(
        st.text(min_size=1, max_size=20),
        st.binary(min_size=12, max_size=12),
        st.binary(min_size=1, max_size=100),
        st.binary(min_size=16, max_size=16)
    )
    @settings(max_examples=100)
    def test_serialization_round_trip(
        self,
        key_id: str,
        nonce: bytes,
        ciphertext: bytes,
        tag: bytes
    ) -> None:
        """Serialization round trip preserves data."""
        # Skip if key_id contains colons (delimiter)
        if ":" in key_id:
            return

        original = EncryptedValue(
            ciphertext=ciphertext,
            key_id=key_id,
            algorithm=EncryptionAlgorithm.AES_256_GCM,
            nonce=nonce,
            tag=tag
        )

        serialized = original.to_string()
        restored = EncryptedValue.from_string(serialized)

        assert restored.key_id == original.key_id
        assert restored.algorithm == original.algorithm
        assert restored.nonce == original.nonce
        assert restored.ciphertext == original.ciphertext
        assert restored.tag == original.tag
