# ADR-004: Token Revocation with Redis Integration

## Status

Accepted

## Context

The API uses JWT tokens for authentication. JWTs are stateless by design, which means once issued, they remain valid until expiration. This creates a security concern when:

1. A user logs out and expects their session to be invalidated
2. A user's account is compromised and all sessions need to be terminated
3. An administrator needs to revoke access for a specific user
4. A refresh token is stolen and needs to be invalidated

Without token revocation, an attacker with a stolen token could continue accessing the API until the token naturally expires (up to 7 days for refresh tokens).

## Decision

We will implement token revocation using a Redis-backed blacklist with the following approach:

### Architecture

1. **Token Store Interface** (`RefreshTokenStore`)
   - Abstract interface for token storage operations
   - Methods: `store()`, `get()`, `revoke()`, `revoke_all_for_user()`, `is_valid()`

2. **In-Memory Implementation** (`InMemoryTokenStore`)
   - For development and testing
   - Not suitable for production (no persistence, no distribution)

3. **Redis Implementation** (`RedisTokenStore`)
   - Production-ready distributed storage
   - Automatic TTL expiration matching token lifetime
   - Blacklist prefix: `revoked:{jti}`

4. **Configuration**
   - `REDIS__ENABLED`: Toggle Redis usage (default: false)
   - `REDIS__URL`: Redis connection string
   - `REDIS__TOKEN_TTL`: Default token TTL in seconds

### API Endpoints

- `POST /auth/revoke` - Revoke a specific token
- `POST /auth/revoke-all` - Revoke all tokens for current user
- `POST /auth/logout` - Logout (revokes refresh token)

### Verification Flow

```
1. User presents token
2. JWT signature verified
3. Token expiration checked
4. Token JTI checked against blacklist
5. If not blacklisted, access granted
```

## Alternatives Considered

### 1. Short-Lived Tokens Only
- **Pros**: No revocation needed, simpler implementation
- **Cons**: Poor UX (frequent re-authentication), doesn't solve compromised token issue
- **Rejected**: Doesn't meet security requirements

### 2. Database-Backed Token Store
- **Pros**: Uses existing infrastructure, ACID guarantees
- **Cons**: Higher latency, database load on every request
- **Rejected**: Performance concerns for high-traffic APIs

### 3. Token Versioning (User-Level)
- **Pros**: Simple, no external storage needed
- **Cons**: Revokes ALL user tokens, can't revoke individual tokens
- **Rejected**: Too coarse-grained for our needs

### 4. Distributed Cache (Memcached)
- **Pros**: Fast, distributed
- **Cons**: No persistence, less feature-rich than Redis
- **Rejected**: Redis provides better feature set (TTL, persistence options)

## Consequences

### Positive

1. **Security**: Immediate token invalidation capability
2. **Flexibility**: Can revoke individual tokens or all user tokens
3. **Performance**: Redis provides sub-millisecond lookups
4. **Scalability**: Redis supports clustering for high availability
5. **Graceful Degradation**: Falls back to in-memory store if Redis unavailable

### Negative

1. **Infrastructure**: Requires Redis deployment in production
2. **Complexity**: Additional component to manage and monitor
3. **Latency**: Small overhead for blacklist check on each request
4. **Cost**: Redis hosting costs in cloud environments

### Neutral

1. **Testing**: In-memory store allows testing without Redis
2. **Migration**: Existing tokens remain valid until natural expiration

## Implementation Notes

- Redis keys use TTL matching token expiration to auto-cleanup
- Blacklist check is O(1) operation
- Factory function `create_token_store()` handles provider selection
- Property-based tests verify revocation consistency

## References

- [OWASP JWT Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [RFC 7009 - OAuth 2.0 Token Revocation](https://tools.ietf.org/html/rfc7009)
- [Redis Documentation](https://redis.io/documentation)
