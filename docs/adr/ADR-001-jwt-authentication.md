# ADR-001: JWT Authentication Strategy

## Status
Accepted

## Context

The Python API Base framework requires a secure, stateless authentication mechanism that:
- Supports horizontal scaling without session affinity
- Provides short-lived access tokens for security
- Enables token refresh without re-authentication
- Integrates with RBAC for authorization

Traditional session-based authentication requires server-side state storage and doesn't scale well in distributed environments.

## Decision

We implement JWT (JSON Web Token) based authentication with the following characteristics:

### Token Structure

**Access Token:**
- Algorithm: HS256 (configurable)
- Expiration: 30 minutes (configurable)
- Claims: `sub` (user_id), `roles`, `exp`, `iat`, `jti`

**Refresh Token:**
- Algorithm: HS256
- Expiration: 7 days (configurable)
- Claims: `sub` (user_id), `exp`, `iat`, `jti`, `type: refresh`

### Implementation

```python
# src/infrastructure/auth/jwt_providers.py
class JWTProvider:
    def create_access_token(
        self,
        user_id: str,
        roles: list[str],
        extra_claims: dict | None = None,
    ) -> str: ...

    def create_refresh_token(self, user_id: str) -> str: ...

    def verify_token(self, token: str) -> TokenPayload: ...
```

### Security Measures

1. **Secret Key**: Minimum 32 characters, stored securely
2. **Token Rotation**: Refresh tokens are rotated on use
3. **Revocation**: Blacklist stored in Redis (see ADR-004)
4. **HTTPS Only**: Tokens transmitted only over TLS

## Consequences

### Positive
- Stateless authentication enables horizontal scaling
- Self-contained tokens reduce database lookups
- Standard format with wide library support
- Flexible claims for authorization data

### Negative
- Token size larger than session IDs
- Cannot invalidate tokens without blacklist
- Secret key rotation requires careful planning

### Neutral
- Requires Redis for token revocation
- Client must handle token refresh logic

## Alternatives Considered

1. **Session-based authentication** - Rejected due to scaling limitations and session affinity requirements
2. **OAuth 2.0 with external provider** - Rejected for initial implementation; may be added later
3. **Paseto tokens** - Rejected due to less library support compared to JWT

## References

- [src/infrastructure/auth/jwt_providers.py](../../src/infrastructure/auth/jwt_providers.py)
- [src/infrastructure/auth/jwt_validator.py](../../src/infrastructure/auth/jwt_validator.py)
- [src/core/config/security.py](../../src/core/config/security.py)
- [RFC 7519 - JSON Web Token](https://tools.ietf.org/html/rfc7519)

## History

| Date | Status | Notes |
|------|--------|-------|
| 2024-12-02 | Proposed | Initial proposal |
| 2024-12-02 | Accepted | Approved for implementation |
