"""Generic RBAC infrastructure with PEP 695 type parameters.

**Feature: enterprise-generics-2025**
**Requirement: R14 - Generic RBAC System**

Exports:
    - Permission[TResource, TAction]: Generic permission
    - Role[TPermission]: Generic role
    - RBAC[TUser]: Generic RBAC checker
    - requires: Permission decorator
    - AuditEvent: Audit event model
"""

from infrastructure.rbac.permission import Permission, Action, Resource
from infrastructure.rbac.role import Role, RoleRegistry
from infrastructure.rbac.checker import RBAC, requires
from infrastructure.rbac.audit import AuditEvent, AuditLogger, InMemoryAuditSink

__all__ = [
    # Permission
    "Permission",
    "Action",
    "Resource",
    # Role
    "Role",
    "RoleRegistry",
    # RBAC
    "RBAC",
    "requires",
    # Audit
    "AuditEvent",
    "AuditLogger",
    "InMemoryAuditSink",
]
