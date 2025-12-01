# ADR-003: API Versioning Strategy

## Status

Accepted

## Context

The Base API needs a versioning strategy to:

- Allow breaking changes without disrupting existing clients
- Provide clear migration paths for API consumers
- Support multiple versions simultaneously during transitions
- Communicate deprecation timelines clearly

## Decision

We will implement URL path versioning with the following approach:

1. **Versioning Scheme**: URL path prefix `/api/v{major}/`
2. **Version Format**: Major version only (v1, v2, etc.)
3. **Deprecation Headers**: RFC 8594 compliant headers
4. **Router Pattern**: VersionedRouter wrapper class

### URL Structure

```
/api/v1/items
/api/v1/users
/api/v2/items  (future)
```

### Deprecation Headers

When a version is deprecated:

```http
Deprecation: true
Sunset: Sat, 01 Jan 2025 00:00:00 GMT
X-API-Deprecation-Info: API version v1 is deprecated. Please migrate to v2.
```

### Implementation

```python
class VersionedRouter:
    def __init__(self, version: APIVersion, config: VersionConfig):
        self.version = version
        self.config = config
        self.prefix = f"/api/{version.value}"
```

## Consequences

### Positive

- Clear, visible versioning in URLs
- Easy to route and document
- Standard approach understood by API consumers
- Supports parallel version deployment
- RFC-compliant deprecation communication

### Negative

- URL changes between versions
- May lead to code duplication across versions
- Requires maintaining multiple codepaths

### Neutral

- Requires planning for version transitions
- Documentation must cover all active versions

## Alternatives Considered

### Alternative 1: Header-Based Versioning

Using `Accept` or custom header for version. Rejected because:
- Less visible to developers
- Harder to test in browser
- Can be accidentally omitted

### Alternative 2: Query Parameter Versioning

Using `?version=1` parameter. Rejected because:
- Mixes versioning with query parameters
- Less RESTful
- Can conflict with other parameters

### Alternative 3: Content Negotiation

Using media types like `application/vnd.api.v1+json`. Rejected because:
- More complex to implement
- Less intuitive for developers
- Harder to document

### Alternative 4: No Versioning (Evolutionary)

Evolving API without explicit versions. Rejected because:
- Harder to make breaking changes
- Less predictable for consumers
- Requires careful backward compatibility

## References

- [RFC 8594 - The Sunset HTTP Header Field](https://tools.ietf.org/html/rfc8594)
- [API Versioning Best Practices](https://www.postman.com/api-platform/api-versioning/)
- [Microsoft REST API Guidelines - Versioning](https://github.com/microsoft/api-guidelines/blob/vNext/Guidelines.md#12-versioning)
