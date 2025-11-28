"""Field-level encryption with key rotation support."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, TypeVar, Generic, Any
from enum import Enum
import base64
import hashlib
import secrets


class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms."""
    AES_256_GCM = "aes-256-gcm"
    AES_256_CBC = "aes-256-cbc"
    CHACHA20_POLY1305 = "chacha20-poly1305"


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
    """Encrypted value with metadata."""
    ciphertext: bytes
    key_id: str
    algorithm: EncryptionAlgorithm
    nonce: bytes
    tag: bytes | None = None
    version: int = 1

    def to_string(self) -> str:
        """Serialize to storable string."""
        parts = [
            self.key_id,
            self.algorithm.value,
            str(self.version),
            base64.b64encode(self.nonce).decode(),
            base64.b64encode(self.ciphertext).decode(),
        ]
        if self.tag:
            parts.append(base64.b64encode(self.tag).decode())
        return ":".join(parts)

    @classmethod
    def from_string(cls, value: str) -> "EncryptedValue":
        """Deserialize from stored string."""
        parts = value.split(":")
        return cls(
            key_id=parts[0],
            algorithm=EncryptionAlgorithm(parts[1]),
            version=int(parts[2]),
            nonce=base64.b64decode(parts[3]),
            ciphertext=base64.b64decode(parts[4]),
            tag=base64.b64decode(parts[5]) if len(parts) > 5 else None
        )


class KeyProvider(Protocol):
    """Protocol for key management."""

    async def get_key(self, key_id: str) -> bytes | None: ...
    async def get_active_key(self) -> tuple[str, bytes]: ...
    async def rotate_key(self) -> tuple[str, bytes]: ...
    async def list_keys(self) -> list[EncryptionKey]: ...


class FieldEncryptor:
    """Field-level encryption service."""

    def __init__(self, key_provider: KeyProvider) -> None:
        self._key_provider = key_provider

    async def encrypt(
        self,
        plaintext: str | bytes,
        algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM
    ) -> EncryptedValue:
        """Encrypt a value."""
        if isinstance(plaintext, str):
            plaintext = plaintext.encode()

        key_id, key = await self._key_provider.get_active_key()
        nonce = secrets.token_bytes(12)

        # Simplified encryption (in production use cryptography library)
        ciphertext = self._xor_encrypt(plaintext, key, nonce)
        tag = self._compute_tag(ciphertext, key)

        return EncryptedValue(
            ciphertext=ciphertext,
            key_id=key_id,
            algorithm=algorithm,
            nonce=nonce,
            tag=tag
        )

    async def decrypt(self, encrypted: EncryptedValue) -> bytes:
        """Decrypt a value."""
        key = await self._key_provider.get_key(encrypted.key_id)
        if not key:
            raise ValueError(f"Key not found: {encrypted.key_id}")

        # Verify tag
        expected_tag = self._compute_tag(encrypted.ciphertext, key)
        if encrypted.tag and encrypted.tag != expected_tag:
            raise ValueError("Authentication failed")

        return self._xor_encrypt(encrypted.ciphertext, key, encrypted.nonce)

    def _xor_encrypt(self, data: bytes, key: bytes, nonce: bytes) -> bytes:
        """Simple XOR encryption (use proper crypto in production)."""
        key_stream = hashlib.sha256(key + nonce).digest()
        result = bytearray(len(data))
        for i, byte in enumerate(data):
            result[i] = byte ^ key_stream[i % len(key_stream)]
        return bytes(result)

    def _compute_tag(self, data: bytes, key: bytes) -> bytes:
        """Compute authentication tag."""
        return hashlib.sha256(key + data).digest()[:16]

    async def rotate_encrypted_value(
        self,
        encrypted: EncryptedValue
    ) -> EncryptedValue:
        """Re-encrypt with new key."""
        plaintext = await self.decrypt(encrypted)
        return await self.encrypt(plaintext, encrypted.algorithm)


@dataclass
class EncryptedField:
    """Descriptor for encrypted model fields."""
    field_name: str
    encryptor: FieldEncryptor | None = None

    def __set_name__(self, owner: type, name: str) -> None:
        self.field_name = name
        self._storage_name = f"_encrypted_{name}"

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        if obj is None:
            return self
        return getattr(obj, self._storage_name, None)

    def __set__(self, obj: Any, value: Any) -> None:
        setattr(obj, self._storage_name, value)


class InMemoryKeyProvider:
    """In-memory key provider for testing."""

    def __init__(self) -> None:
        self._keys: dict[str, tuple[bytes, EncryptionKey]] = {}
        self._active_key_id: str | None = None
        self._rotate_key_sync()

    def _rotate_key_sync(self) -> tuple[str, bytes]:
        import uuid
        key_id = str(uuid.uuid4())
        key = secrets.token_bytes(32)
        metadata = EncryptionKey(
            key_id=key_id,
            algorithm=EncryptionAlgorithm.AES_256_GCM,
            created_at=datetime.utcnow()
        )
        self._keys[key_id] = (key, metadata)
        self._active_key_id = key_id
        return key_id, key

    async def get_key(self, key_id: str) -> bytes | None:
        if key_id in self._keys:
            return self._keys[key_id][0]
        return None

    async def get_active_key(self) -> tuple[str, bytes]:
        if not self._active_key_id:
            return self._rotate_key_sync()
        return self._active_key_id, self._keys[self._active_key_id][0]

    async def rotate_key(self) -> tuple[str, bytes]:
        return self._rotate_key_sync()

    async def list_keys(self) -> list[EncryptionKey]:
        return [meta for _, meta in self._keys.values()]
