# ADR-003: API Versioning Strategy

## Status
Accepted

## Context

The API needs a versioning strategy that:
- Allows breaking changes without disrupting existing clients
- Provides clear migration paths
- Supports multiple versions simultaneously
- Follows industry standards for deprecation

## Decision

We implement URL path-based versioning as the primary strategy:

### URL Structure

```
/api/v1/users
/api/v2/users
```

### Version Support

- **Active versions**: Full support and bug fixes
- **Deprecated versions**: Security fixes only, sunset date announced
- **Sunset versions**: No longer available

### Deprecation Headers (RFC 8594)

```http
Deprecation: true
Sunset: Sat, 31 Dec 2025 23:59:59 GMT
Link: </api/v2/users>; rel="successor-version"
```

### Implementation

```python
# src/interface/versioning/generic.py
class URLVersioning:
    def get_version(self, request: Request) -> str: ...

# src/interface/router.py
app.include_router(v1_router, prefix="/api/v1")
app.include_router(v2_router, prefix="/api/v2")
```

### Version Lifecycle

```
Development → Active → Deprecated → Sunset
     │           │          │          │
     │           │          │          └── Removed from API
     │           │          └── 6 months notice
     │           └── Full support
     └── Not yet released
```

### Migration Strategy

1. Announce deprecation with sunset date
2. Add deprecation headers to responses
3. Document migration guide
4. Monitor usage of deprecated endpoints
5. Remove after sunset date

## Consequences

### Positive
- Clear, visible versioning in URLs
- Easy to route and document
- Standard deprecation headers
- Supports gradual migration

### Negative
- URL changes between versions
- Multiple codepaths to maintain
- Clients must update URLs for new versions

### Neutral
- OpenAPI spec generated per version
- Version-specific documentation

## Alternatives Considered

1. **Header-based versioning** (`X-API-Version: 1`) - Rejected as less visible and harder to test
2. **Query parameter versioning** (`?version=1`) - Rejected as non-standard
3. **Content negotiation** (`Accept: application/vnd.api.v1+json`) - Rejected as complex for clients

## References

- [src/interface/versioning/](../../src/interface/versioning/)
- [src/interface/v1/](../../src/interface/v1/)
- [src/interface/v2/](../../src/interface/v2/)
- [RFC 8594 - The Sunset HTTP Header Field](https://tools.ietf.org/html/rfc8594)

## History

| Date | Status | Notes |
|------|--------|-------|
| 2024-12-02 | Proposed | Initial proposal |
| 2024-12-02 | Accepted | Approved for implementation |
