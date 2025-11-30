"""Field-level encryption with AES-256-GCM and key rotation support.

**Feature: shared-modules-security-fixes**
**Validates: Requirements 1.1, 1.2, 1.3, 1.4**
"""

from __future__ import annotations

import base64
import secrets
import warnings
from dataclasses import dataclass
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Protocol

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from my_api.shared.exceptions import (
    AuthenticationError,
    DecryptionError,
    EncryptionError,
)


class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms."""

    AES_256_GCM = "aes-256-gcm"
    AES_256_CBC = "aes-256-cbc"  # Legacy, not recommended
    CHACHA20_POLY1305 = "chacha20-poly1305"


# Constants for AES-256-GCM
NONCE_SIZE = 12  # 96 bits for GCM (recommended)
KEY_SIZE = 32    # 256 bits
TAG_SIZE = 16    # 128 bits


@dataclass
class EncryptionKey:
    """Encryption key metadata."""

    key_id: str
    algorithm: EncryptionAlgorithm
    created_at: datetime
    expires_at: datetime | None = None
    is_active: bool = True
    version: int = 1


@dataclass
class EncryptedValue:
    """Encrypted value with AES-GCM metadata."""

    ciphertext: bytes
    key_id: str
    algorithm: EncryptionAlgorithm
    nonce: bytes
    tag: bytes | None = None
    version: int = 2  # Version 2 for AES-GCM

    def to_string(self) -> str:
        """Serialize to storable string."""
        parts = [
            self.key_id,
            self.algorithm.value,
            str(self.version),
            base64.b64encode(self.nonce).decode("utf-8"),
            base64.b64encode(self.ciphertext).decode("utf-8"),
        ]
        if self.tag:
            parts.append(base64.b64encode(self.tag).decode("utf-8"))
        return ":".join(parts)

    @classmethod
    def from_string(cls, value: str) -> EncryptedValue:
        """Deserialize from stored string."""
        parts = value.split(":")
        if len(parts) < 5:
            raise DecryptionError(
                "Invalid encrypted value format",
                context={"parts_count": len(parts)},
            )
        return cls(
            key_id=parts[0],
            algorithm=EncryptionAlgorithm(parts[1]),
            version=int(parts[2]),
            nonce=base64.b64decode(parts[3]),
            ciphertext=base64.b64decode(parts[4]),
            tag=base64.b64decode(parts[5]) if len(parts) > 5 else None,
        )


class KeyProvider(Protocol):
    """Protocol for key management."""

    async def get_key(self, key_id: str) -> bytes | None:
        """Get key by ID."""
        ...

    async def get_active_key(self) -> tuple[str, bytes]:
        """Get active key for encryption."""
        ...

    async def rotate_key(self) -> tuple[str, bytes]:
        """Rotate to a new key."""
        ...

    async def list_keys(self) -> list[EncryptionKey]:
        """List all keys."""
        ...


class FieldEncryptor:
    """AES-256-GCM field-level encryption service.

    Provides authenticated encryption using AES-256-GCM algorithm.
    """

    def __init__(self, key_provider: KeyProvider) -> None:
        """Initialize field encryptor.

        Args:
            key_provider: Provider for encryption keys.
        """
        self._key_provider = key_provider

    async def encrypt(
        self,
        plaintext: str | bytes,
        algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM,
    ) -> EncryptedValue:
        """Encrypt a value using AES-256-GCM.

        Args:
            plaintext: Data to encrypt.
            algorithm: Encryption algorithm (must be AES_256_GCM).

        Returns:
            EncryptedValue with ciphertext and metadata.

        Raises:
            EncryptionError: If encryption fails.
        """
        if algorithm != EncryptionAlgorithm.AES_256_GCM:
            raise EncryptionError(
                f"Unsupported algorithm: {algorithm.value}. Use AES_256_GCM.",
                context={"algorithm": algorithm.value},
            )

        if isinstance(plaintext, str):
            plaintext = plaintext.encode("utf-8")

        try:
            key_id, key = await self._key_provider.get_active_key()
        except Exception as e:
            raise EncryptionError(
                "Failed to get encryption key",
                context={"error": str(e)},
            ) from e

        if len(key) != KEY_SIZE:
            raise EncryptionError(
                f"Invalid key size: expected {KEY_SIZE} bytes, got {len(key)}",
                context={"key_id": key_id, "key_size": len(key)},
            )

        nonce = secrets.token_bytes(NONCE_SIZE)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        # AES-GCM appends tag to ciphertext, extract it
        actual_ciphertext = ciphertext[:-TAG_SIZE]
        tag = ciphertext[-TAG_SIZE:]

        return EncryptedValue(
            ciphertext=actual_ciphertext,
            key_id=key_id,
            algorithm=algorithm,
            nonce=nonce,
            tag=tag,
            version=2,
        )


    async def decrypt(self, encrypted: EncryptedValue) -> bytes:
        """Decrypt a value and verify authentication tag.

        Args:
            encrypted: Encrypted value to decrypt.

        Returns:
            Decrypted plaintext bytes.

        Raises:
            DecryptionError: If key not found or decryption fails.
            AuthenticationError: If authentication tag verification fails.
        """
        key = await self._key_provider.get_key(encrypted.key_id)
        if not key:
            raise DecryptionError(
                f"Key not found: {encrypted.key_id}",
                context={"key_id": encrypted.key_id},
            )

        if len(key) != KEY_SIZE:
            raise DecryptionError(
                f"Invalid key size: expected {KEY_SIZE} bytes, got {len(key)}",
                context={"key_id": encrypted.key_id, "key_size": len(key)},
            )

        # Reconstruct ciphertext with tag for AESGCM
        if encrypted.tag:
            ciphertext_with_tag = encrypted.ciphertext + encrypted.tag
        else:
            ciphertext_with_tag = encrypted.ciphertext

        aesgcm = AESGCM(key)
        try:
            plaintext = aesgcm.decrypt(encrypted.nonce, ciphertext_with_tag, None)
            return plaintext
        except Exception as e:
            if "tag" in str(e).lower() or "authentication" in str(e).lower():
                raise AuthenticationError(
                    "Authentication tag verification failed - data may be tampered",
                    context={"key_id": encrypted.key_id},
                ) from e
            raise DecryptionError(
                f"Decryption failed: {e}",
                context={"key_id": encrypted.key_id},
            ) from e

    def _xor_encrypt(self, data: bytes, key: bytes, nonce: bytes) -> bytes:
        """Deprecated XOR encryption - DO NOT USE.

        This method is insecure and deprecated. It will raise a DeprecationWarning
        and then raise an EncryptionError to prevent usage.

        Args:
            data: Data to encrypt.
            key: Encryption key.
            nonce: Nonce value.

        Raises:
            DeprecationWarning: Always raised to warn about insecure method.
            EncryptionError: Always raised to prevent usage.
        """
        warnings.warn(
            "XOR encryption is insecure and deprecated. Use AES-256-GCM via encrypt().",
            DeprecationWarning,
            stacklevel=2,
        )
        raise EncryptionError(
            "XOR encryption is deprecated and disabled. Use AES-256-GCM.",
            context={"method": "_xor_encrypt"},
        )

    async def rotate_encrypted_value(self, encrypted: EncryptedValue) -> EncryptedValue:
        """Re-encrypt with new key.

        Args:
            encrypted: Value to re-encrypt.

        Returns:
            Newly encrypted value with current active key.
        """
        plaintext = await self.decrypt(encrypted)
        return await self.encrypt(plaintext, encrypted.algorithm)


@dataclass
class EncryptedField:
    """Descriptor for encrypted model fields."""

    field_name: str
    encryptor: FieldEncryptor | None = None

    def __set_name__(self, owner: type, name: str) -> None:
        """Set field name when descriptor is assigned."""
        self.field_name = name
        self._storage_name = f"_encrypted_{name}"

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        """Get encrypted field value."""
        if obj is None:
            return self
        return getattr(obj, self._storage_name, None)

    def __set__(self, obj: Any, value: Any) -> None:
        """Set encrypted field value."""
        setattr(obj, self._storage_name, value)


class InMemoryKeyProvider:
    """In-memory key provider for testing."""

    def __init__(self) -> None:
        """Initialize in-memory key provider."""
        self._keys: dict[str, tuple[bytes, EncryptionKey]] = {}
        self._active_key_id: str | None = None
        self._rotate_key_sync()

    def _rotate_key_sync(self) -> tuple[str, bytes]:
        """Rotate key synchronously."""
        import uuid

        key_id = str(uuid.uuid4())
        key = secrets.token_bytes(KEY_SIZE)
        metadata = EncryptionKey(
            key_id=key_id,
            algorithm=EncryptionAlgorithm.AES_256_GCM,
            created_at=datetime.now(UTC),
        )
        self._keys[key_id] = (key, metadata)
        self._active_key_id = key_id
        return key_id, key

    async def get_key(self, key_id: str) -> bytes | None:
        """Get key by ID."""
        if key_id in self._keys:
            return self._keys[key_id][0]
        return None

    async def get_active_key(self) -> tuple[str, bytes]:
        """Get active key for encryption."""
        if not self._active_key_id:
            return self._rotate_key_sync()
        return self._active_key_id, self._keys[self._active_key_id][0]

    async def rotate_key(self) -> tuple[str, bytes]:
        """Rotate to a new key."""
        return self._rotate_key_sync()

    async def list_keys(self) -> list[EncryptionKey]:
        """List all keys."""
        return [meta for _, meta in self._keys.values()]
