"""JWKS models and helper functions.

**Feature: api-best-practices-review-2025**
**Validates: Requirements 20.1, 20.2**

Extracted from jwks.py for better modularity and reusability.
"""

import base64
import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa


@dataclass(frozen=True, slots=True)
class JWK:
    """JSON Web Key representation.

    **Feature: api-best-practices-review-2025**
    **Validates: Requirements 20.2**
    
    Attributes:
        kty: Key type (RSA, EC).
        kid: Key ID.
        use: Key use (sig for signature).
        alg: Algorithm (RS256, ES256).
        n: RSA modulus (base64url).
        e: RSA exponent (base64url).
        crv: EC curve (P-256).
        x: EC x coordinate (base64url).
        y: EC y coordinate (base64url).
    """

    kty: str
    kid: str
    use: str
    alg: str
    n: str | None = None
    e: str | None = None
    crv: str | None = None
    x: str | None = None
    y: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert JWK to dictionary for JSON serialization."""
        result: dict[str, Any] = {
            "kty": self.kty,
            "kid": self.kid,
            "use": self.use,
            "alg": self.alg,
        }
        if self.kty == "RSA":
            result["n"] = self.n
            result["e"] = self.e
        elif self.kty == "EC":
            result["crv"] = self.crv
            result["x"] = self.x
            result["y"] = self.y
        return result


@dataclass(frozen=True, slots=True)
class JWKSResponse:
    """JWKS response containing multiple keys.

    **Feature: api-best-practices-review-2025**
    **Validates: Requirements 20.2, 20.3**
    """

    keys: tuple[JWK, ...]

    def to_dict(self) -> dict[str, Any]:
        """Convert JWKS to dictionary for JSON response."""
        return {"keys": [key.to_dict() for key in self.keys]}


@dataclass
class KeyEntry:
    """Internal key entry with metadata for rotation.
    
    Attributes:
        kid: Key ID.
        public_key_pem: Public key in PEM format.
        algorithm: Algorithm (RS256, ES256).
        created_at: When the key was created.
        revoked_at: When the key was revoked (None if active).
        expires_at: When the key expires (None if no expiration).
    """

    kid: str
    public_key_pem: str
    algorithm: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    revoked_at: datetime | None = None
    expires_at: datetime | None = None


def base64url_encode(data: bytes) -> str:
    """Encode bytes to base64url without padding.
    
    Args:
        data: Bytes to encode.
        
    Returns:
        Base64url encoded string.
    """
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def int_to_base64url(num: int) -> str:
    """Convert integer to base64url encoding.
    
    Args:
        num: Integer to encode.
        
    Returns:
        Base64url encoded string.
    """
    byte_length = (num.bit_length() + 7) // 8
    return base64url_encode(num.to_bytes(byte_length, byteorder="big"))


def generate_kid_from_public_key(public_key_pem: str) -> str:
    """Generate a deterministic key ID from public key.

    Uses SHA-256 hash of the public key PEM, truncated to 16 chars.

    **Feature: api-best-practices-review-2025**
    **Validates: Requirements 20.1**

    Args:
        public_key_pem: Public key in PEM format.

    Returns:
        Key ID string (16 hex characters).
    """
    key_hash = hashlib.sha256(public_key_pem.encode()).digest()
    return key_hash[:8].hex()


def create_jwk_from_rsa_public_key(public_key_pem: str, kid: str) -> JWK:
    """Create JWK from RSA public key PEM.

    **Feature: api-best-practices-review-2025**
    **Validates: Requirements 20.2**

    Args:
        public_key_pem: RSA public key in PEM format.
        kid: Key ID to use.

    Returns:
        JWK representation of the public key.
    """
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    public_key = load_pem_public_key(public_key_pem.encode())

    if not isinstance(public_key, rsa.RSAPublicKey):
        raise ValueError("Expected RSA public key")

    numbers = public_key.public_numbers()

    return JWK(
        kty="RSA",
        kid=kid,
        use="sig",
        alg="RS256",
        n=int_to_base64url(numbers.n),
        e=int_to_base64url(numbers.e),
    )


def create_jwk_from_ec_public_key(public_key_pem: str, kid: str) -> JWK:
    """Create JWK from EC public key PEM.

    **Feature: api-best-practices-review-2025**
    **Validates: Requirements 20.2**

    Args:
        public_key_pem: EC public key in PEM format.
        kid: Key ID to use.

    Returns:
        JWK representation of the public key.
    """
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    public_key = load_pem_public_key(public_key_pem.encode())

    if not isinstance(public_key, ec.EllipticCurvePublicKey):
        raise ValueError("Expected EC public key")

    numbers = public_key.public_numbers()

    return JWK(
        kty="EC",
        kid=kid,
        use="sig",
        alg="ES256",
        crv="P-256",
        x=base64url_encode(numbers.x.to_bytes(32, byteorder="big")),
        y=base64url_encode(numbers.y.to_bytes(32, byteorder="big")),
    )


def extract_public_key_from_private(private_key_pem: str) -> str:
    """Extract public key PEM from private key PEM.

    **Feature: api-best-practices-review-2025**
    **Validates: Requirements 20.1**

    Args:
        private_key_pem: Private key in PEM format.

    Returns:
        Public key in PEM format.
    """
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    private_key = load_pem_private_key(private_key_pem.encode(), password=None)
    public_key = private_key.public_key()

    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
