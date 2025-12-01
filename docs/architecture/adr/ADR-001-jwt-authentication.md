# ADR-001: JWT Authentication Strategy

## Status

Accepted

## Context

The Base API requires a secure, stateless authentication mechanism that can scale horizontally and integrate with modern frontend applications. We need to support:

- Token-based authentication for API access
- Refresh token mechanism for extended sessions
- Token revocation for logout functionality
- Support for role-based access control (RBAC)

## Decision

We will implement JWT (JSON Web Token) authentication using the following approach:

1. **Token Types**: Use separate access tokens (short-lived, 30 min) and refresh tokens (long-lived, 7 days)
2. **Algorithm**: HS256 for symmetric signing with a secure secret key (minimum 32 characters)
3. **Token Storage**: 
   - Access tokens: Client-side only (memory/localStorage)
   - Refresh tokens: Server-side storage in Redis with TTL
4. **Library**: python-jose for JWT operations
5. **Token Payload**: Include user_id (sub), expiration (exp), issued at (iat), JWT ID (jti), scopes, and token type

### Token Structure

```python
@dataclass
class TokenPayload:
    sub: str      # user_id
    exp: datetime # expiration
    iat: datetime # issued at
    jti: str      # JWT ID for revocation
    scopes: tuple[str, ...]
    token_type: str  # "access" or "refresh"
```

## Consequences

### Positive

- Stateless authentication enables horizontal scaling
- Short-lived access tokens limit exposure window
- Refresh tokens allow extended sessions without re-authentication
- JTI enables individual token revocation
- Scopes support fine-grained authorization

### Negative

- Requires Redis for refresh token storage
- Token revocation requires checking against storage
- Secret key rotation requires careful planning

### Neutral

- Standard JWT approach familiar to most developers
- Requires secure secret key management

## Alternatives Considered

### Alternative 1: Session-based Authentication

Traditional server-side sessions with cookies. Rejected because:
- Requires sticky sessions or shared session storage
- Less suitable for API-first architecture
- Harder to scale horizontally

### Alternative 2: OAuth2 with External Provider

Delegating authentication to external OAuth2 provider. Rejected because:
- Adds external dependency
- More complex setup for simple use cases
- May not be needed for all deployments

### Alternative 3: Opaque Tokens

Random tokens stored entirely server-side. Rejected because:
- Requires database lookup for every request
- Less information available to clients
- Higher latency for token validation

## References

- [RFC 7519 - JSON Web Token](https://tools.ietf.org/html/rfc7519)
- [OWASP JWT Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [python-jose Documentation](https://python-jose.readthedocs.io/)
