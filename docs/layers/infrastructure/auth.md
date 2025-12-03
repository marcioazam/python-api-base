# Authentication Infrastructure

## Overview

Authentication infrastructure provides JWT token management, password hashing, and token revocation capabilities.

## Location

```
src/infrastructure/auth/
├── __init__.py
├── jwt_providers.py    # JWT creation/validation
├── jwt_validator.py    # Token validation
├── password_policy.py  # Password requirements
├── jwt/                # JWT utilities
├── oauth/              # OAuth providers
└── token_store/        # Token storage/revocation
```

## JWT Service

### Token Creation

```python
class JWTService:
    """JWT token management service."""
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ):
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_expire = timedelta(minutes=access_token_expire_minutes)
        self._refresh_expire = timedelta(days=refresh_token_expire_days)
    
    def create_access_token(
        self,
        user_id: str,
        roles: list[str] = [],
        permissions: list[str] = [],
    ) -> str:
        """Create access token."""
        now = datetime.utcnow()
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + self._access_expire,
            "jti": str(uuid4()),
            "type": "access",
            "roles": roles,
            "permissions": permissions,
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create refresh token."""
        now = datetime.utcnow()
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + self._refresh_expire,
            "jti": str(uuid4()),
            "type": "refresh",
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)
    
    def create_token_pair(
        self,
        user_id: str,
        roles: list[str] = [],
    ) -> TokenPair:
        """Create access and refresh token pair."""
        return TokenPair(
            access_token=self.create_access_token(user_id, roles),
            refresh_token=self.create_refresh_token(user_id),
            expires_in=int(self._access_expire.total_seconds()),
        )
```

### Token Validation

```python
class JWTValidator:
    """JWT token validator."""
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        token_store: ITokenStore | None = None,
    ):
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._token_store = token_store
    
    async def validate(self, token: str) -> TokenPayload:
        """Validate token and return payload."""
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
            )
        except jwt.ExpiredSignatureError:
            raise UnauthorizedError("Token expired")
        except jwt.InvalidTokenError as e:
            raise UnauthorizedError(f"Invalid token: {e}")
        
        # Check revocation
        if self._token_store:
            jti = payload.get("jti")
            if jti and await self._token_store.is_revoked(jti):
                raise UnauthorizedError("Token revoked")
        
        return TokenPayload(
            sub=payload["sub"],
            exp=datetime.fromtimestamp(payload["exp"]),
            iat=datetime.fromtimestamp(payload["iat"]),
            jti=payload.get("jti", ""),
            roles=payload.get("roles", []),
            permissions=payload.get("permissions", []),
        )
```

## Token Store (Revocation)

```python
class RedisTokenStore:
    """Redis-based token store for revocation."""
    
    def __init__(self, redis: Redis, prefix: str = "revoked:"):
        self._redis = redis
        self._prefix = prefix
    
    async def revoke(self, jti: str, expires_at: datetime) -> None:
        """Revoke a token."""
        ttl = int((expires_at - datetime.utcnow()).total_seconds())
        if ttl > 0:
            await self._redis.setex(
                f"{self._prefix}{jti}",
                ttl,
                "1",
            )
    
    async def is_revoked(self, jti: str) -> bool:
        """Check if token is revoked."""
        return await self._redis.exists(f"{self._prefix}{jti}") > 0
    
    async def revoke_all_for_user(self, user_id: str) -> None:
        """Revoke all tokens for a user (logout all devices)."""
        # Store user revocation timestamp
        await self._redis.set(
            f"user_revoked:{user_id}",
            datetime.utcnow().isoformat(),
        )
```

## Password Policy

```python
@dataclass
class PasswordPolicy:
    """Password validation policy."""
    
    min_length: int = 12
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_special: bool = True
    special_chars: str = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    def validate(self, password: str) -> ValidationResult:
        """Validate password against policy."""
        errors = []
        
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters")
        
        if len(password) > self.max_length:
            errors.append(f"Password must be at most {self.max_length} characters")
        
        if self.require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain uppercase letter")
        
        if self.require_lowercase and not any(c.islower() for c in password):
            errors.append("Password must contain lowercase letter")
        
        if self.require_digit and not any(c.isdigit() for c in password):
            errors.append("Password must contain digit")
        
        if self.require_special and not any(c in self.special_chars for c in password):
            errors.append("Password must contain special character")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
        )
```

## Password Hashing

```python
from passlib.context import CryptContext

class PasswordHasher:
    """Argon2 password hasher."""
    
    def __init__(self):
        self._context = CryptContext(
            schemes=["argon2"],
            deprecated="auto",
        )
    
    def hash(self, password: str) -> str:
        """Hash password."""
        return self._context.hash(password)
    
    def verify(self, password: str, hash: str) -> bool:
        """Verify password against hash."""
        return self._context.verify(password, hash)
    
    def needs_rehash(self, hash: str) -> bool:
        """Check if hash needs to be updated."""
        return self._context.needs_update(hash)
```

## FastAPI Integration

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_validator: JWTValidator = Depends(get_jwt_validator),
    user_repository: IUserRepository = Depends(get_user_repository),
) -> User:
    """Get current authenticated user."""
    token = credentials.credentials
    
    try:
        payload = await jwt_validator.validate(token)
    except UnauthorizedError as e:
        raise HTTPException(status_code=401, detail=str(e))
    
    user = await user_repository.get(payload.sub)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    if not user.is_active:
        raise HTTPException(status_code=401, detail="User inactive")
    
    return user
```

## Security Considerations

1. **Secret Key**: Use strong, random key (min 32 chars)
2. **Token Expiry**: Short-lived access tokens (30 min)
3. **Refresh Rotation**: Rotate refresh tokens on use
4. **Revocation**: Implement token blacklist for logout
5. **HTTPS Only**: Never transmit tokens over HTTP
6. **Secure Storage**: Store tokens securely on client

## Related Documentation

- [RBAC](rbac.md)
- [Security Headers](../interface/middleware.md)
- [Configuration](../core/configuration.md)
