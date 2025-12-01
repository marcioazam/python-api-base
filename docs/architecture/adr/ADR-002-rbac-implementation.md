# ADR-002: Role-Based Access Control Implementation

## Status

Accepted

## Context

The Base API needs an authorization system to control access to resources based on user roles and permissions. Requirements include:

- Support for multiple roles per user
- Fine-grained permission control
- Decorator-based endpoint protection
- Support for both role-based and scope-based authorization
- Audit logging of authorization failures

## Decision

We will implement RBAC using the following approach:

1. **Permission Model**: Enum-based permissions for type safety
2. **Role Model**: Dataclass with frozenset of permissions
3. **Service Pattern**: RBACService for permission checking
4. **Decorator Support**: `@require_permission` decorator for endpoints
5. **Scope Integration**: OAuth2 scopes add to role permissions

### Permission Enum

```python
class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    VIEW_AUDIT = "view_audit"
    EXPORT_DATA = "export_data"
```

### Predefined Roles

- **admin**: All permissions
- **user**: READ, WRITE
- **viewer**: READ only
- **moderator**: READ, WRITE, DELETE, VIEW_AUDIT

### Permission Combination

When a user has multiple roles, permissions are combined using set union:

```python
def get_user_permissions(user) -> set[Permission]:
    permissions = set()
    for role_name in user.roles:
        role = self._roles.get(role_name)
        if role:
            permissions.update(role.permissions)
    return permissions
```

## Consequences

### Positive

- Type-safe permissions with enum
- Flexible role composition
- Easy to add new permissions and roles
- Decorator pattern integrates well with FastAPI
- Scopes provide OAuth2 compatibility

### Negative

- Requires database tables for persistent roles
- Permission changes require code deployment
- Complex permission hierarchies may need extension

### Neutral

- Standard RBAC pattern familiar to developers
- Roles stored in database, permissions in code

## Alternatives Considered

### Alternative 1: Attribute-Based Access Control (ABAC)

Policy-based authorization using attributes. Rejected because:
- More complex to implement and understand
- Overkill for most API use cases
- Harder to audit and debug

### Alternative 2: ACL (Access Control Lists)

Per-resource access control lists. Rejected because:
- Doesn't scale well with many resources
- More complex permission management
- Better suited for file systems

### Alternative 3: External Authorization Service

Using Open Policy Agent or similar. Rejected because:
- Adds external dependency
- More complex deployment
- May be added later if needed

## References

- [NIST RBAC Model](https://csrc.nist.gov/projects/role-based-access-control)
- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
