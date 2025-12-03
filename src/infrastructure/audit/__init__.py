"""Audit trail module.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 22.1-22.5**
"""

from infrastructure.audit.trail import AuditAction, AuditRecord, compute_changes
from infrastructure.audit.storage import AuditStore, InMemoryAuditStore
from infrastructure.audit.filters import (
    AuditQuery,
    AuditQueryFilters,
    AuditExporter,
    ExportFormat,
    JsonAuditExporter,
    JsonExportConfig,
    CsvAuditExporter,
    CsvExportConfig,
)

__all__ = [
    # Core
    "AuditAction",
    "AuditRecord",
    "compute_changes",
    # Storage
    "AuditStore",
    "InMemoryAuditStore",
    # Query and Filters
    "AuditQuery",
    "AuditQueryFilters",
    # Export
    "AuditExporter",
    "ExportFormat",
    "JsonAuditExporter",
    "JsonExportConfig",
    "CsvAuditExporter",
    "CsvExportConfig",
]
