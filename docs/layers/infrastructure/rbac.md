# RBAC (Role-Based Access Control)

## Overview

RBAC provides authorization through roles and permissions.

## Location

```
src/infrastructure/rbac/
├── __init__.py
├── audit.py        # RBAC audit logging
├── checker.py      # Permission checker
├── permission.py   # Permission model
└── role.py         # Role model
```

## Permission Model

```python
@dataclass
class Permission:
    """Permission definition."""
    resource: str
    action: str
    
    def __str__(self) -> str:
        return f"{self.resource}:{self.action}"
```

## Role Model

```python
@dataclass
class Role:
    """Role with permissions."""
    name: str
    permissions: list[Permission]
    parent: "Role | None" = None
    
    def has_permission(self, resource: str, action: str) -> bool:
        # Check own permissions
        for perm in self.permissions:
            if perm.resource == resource and perm.action == action:
                return True
        
        # Check parent role
        if self.parent:
            return self.parent.has_permission(resource, action)
        
        return False
```

## RBAC Service

```python
class RBACService:
    """RBAC service."""
    
    def __init__(self):
        self._roles: dict[str, Role] = {}
    
    def register_role(self, role: Role) -> None:
        self._roles[role.name] = role
    
    def has_permission(
        self,
        user_roles: list[str],
        resource: str,
        action: str,
    ) -> bool:
        for role_name in user_roles:
            role = self._roles.get(role_name)
            if role and role.has_permission(resource, action):
                return True
        return False
```

## Usage

```python
# Define roles
admin = Role("admin", [
    Permission("users", "read"),
    Permission("users", "write"),
    Permission("users", "delete"),
])

user = Role("user", [
    Permission("users", "read"),
])

# Check permission
rbac = RBACService()
rbac.register_role(admin)
rbac.register_role(user)

has_access = rbac.has_permission(["user"], "users", "delete")  # False
```

## FastAPI Integration

```python
def require_permission(resource: str, action: str):
    async def dependency(
        current_user: User = Depends(get_current_user),
        rbac: RBACService = Depends(get_rbac),
    ):
        if not rbac.has_permission(current_user.roles, resource, action):
            raise ForbiddenError("Insufficient permissions")
        return current_user
    return Depends(dependency)

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = require_permission("users", "delete"),
):
    ...
```

## Related

- [Authentication](auth.md)
- [Security](../../operations/security.md)
