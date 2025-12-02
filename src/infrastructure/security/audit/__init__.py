"""Audit logging and trail.

Provides audit capabilities:
- AuditLogger: Abstract base for audit logging
- InMemoryAuditLogger: Testing implementation
- AuditService: Enhanced audit with diff tracking
"""

from infrastructure.security.audit.log import (
    AuditAction,
    AuditResult,
    AuditEntry,
    AuditFilters,
    AuditLogger,
    InMemoryAuditLogger,
)
from infrastructure.security.audit.trail import (
    AuditService,
    DiffCalculator,
    FieldChange,
    InMemoryAuditBackend,
)

__all__ = [
    # Log
    "AuditAction",
    "AuditResult",
    "AuditEntry",
    "AuditFilters",
    "AuditLogger",
    "InMemoryAuditLogger",
    # Trail
    "AuditService",
    "DiffCalculator",
    "FieldChange",
    "InMemoryAuditBackend",
]
