# ADR-002: RBAC Implementation

## Status
Accepted

## Context

The system requires fine-grained access control that:
- Supports role-based permissions
- Allows permission composition
- Integrates with JWT authentication
- Enables endpoint-level protection
- Supports audit logging of access decisions

## Decision

We implement Role-Based Access Control (RBAC) with the following design:

### Role Hierarchy

```
SuperAdmin
    └── Admin
        └── Manager
            └── User
                └── Guest
```

### Permission Model

```python
# src/infrastructure/rbac/permission.py
@dataclass
class Permission:
    resource: str      # e.g., "users", "items"
    action: str        # e.g., "read", "write", "delete"
    scope: str = "*"   # e.g., "own", "*" (all)

# src/infrastructure/rbac/role.py
@dataclass
class Role:
    name: str
    permissions: list[Permission]
    inherits_from: list[str] = field(default_factory=list)
```

### Permission Checking

```python
# src/infrastructure/rbac/checker.py
class RBACChecker:
    def has_permission(
        self,
        user_roles: list[str],
        resource: str,
        action: str,
    ) -> bool: ...

    def require_permission(
        self,
        resource: str,
        action: str,
    ) -> Callable: ...  # FastAPI dependency
```

### Endpoint Protection

```python
@router.get("/users")
async def list_users(
    _: None = Depends(require_permission("users", "read")),
) -> list[UserDTO]:
    ...
```

## Consequences

### Positive
- Clear separation of roles and permissions
- Role inheritance reduces duplication
- Declarative endpoint protection
- Audit trail for access decisions

### Negative
- Additional complexity in permission management
- Role hierarchy must be carefully designed
- Permission changes require code deployment

### Neutral
- Permissions stored in code, not database
- Role assignment stored with user data

## Alternatives Considered

1. **ABAC (Attribute-Based Access Control)** - Rejected as overly complex for current needs; may be added later
2. **ACL (Access Control Lists)** - Rejected due to management complexity at scale
3. **External authorization service (OPA)** - Rejected for initial implementation; may be integrated later

## References

- [src/infrastructure/rbac/checker.py](../../src/infrastructure/rbac/checker.py)
- [src/infrastructure/rbac/permission.py](../../src/infrastructure/rbac/permission.py)
- [src/infrastructure/rbac/role.py](../../src/infrastructure/rbac/role.py)
- [src/infrastructure/rbac/audit.py](../../src/infrastructure/rbac/audit.py)

## History

| Date | Status | Notes |
|------|--------|-------|
| 2024-12-02 | Proposed | Initial proposal |
| 2024-12-02 | Accepted | Approved for implementation |
