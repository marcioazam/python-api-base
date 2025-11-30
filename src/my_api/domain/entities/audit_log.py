"""Audit log domain entity.

**Feature: api-base-improvements**
**Validates: Requirements 4.4**
"""

from datetime import datetime, UTC

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel

from my_api.shared.utils.ids import generate_ulid


class AuditLogDB(SQLModel, table=True):
    """Audit log database model.

    Stores immutable audit trail for security-relevant events.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_timestamp", "timestamp"),
        Index("ix_audit_logs_resource_type", "resource_type"),
    )

    id: str = SQLField(
        default_factory=generate_ulid,
        primary_key=True,
        description="ULID identifier",
    )
    timestamp: datetime = SQLField(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
        description="When the action occurred",
    )
    user_id: str | None = SQLField(
        default=None,
        sa_column=Column(String(26), nullable=True, index=True),
        description="User who performed the action",
    )
    action: str = SQLField(
        sa_column=Column(String(100), nullable=False, index=True),
        description="Action type (login, create, update, etc.)",
    )
    resource_type: str = SQLField(
        sa_column=Column(String(100), nullable=False, index=True),
        description="Type of resource affected",
    )
    resource_id: str | None = SQLField(
        default=None,
        max_length=26,
        description="ID of the affected resource",
    )
    details: str = SQLField(
        default="{}",
        sa_column=Column(Text, nullable=False),
        description="JSON-encoded action details",
    )
    ip_address: str | None = SQLField(
        default=None,
        max_length=45,
        description="Client IP address (IPv4 or IPv6)",
    )
    user_agent: str | None = SQLField(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Client user agent string",
    )
    result: str = SQLField(
        sa_column=Column(String(20), nullable=False),
        description="Action result (success, failure, error)",
    )
    request_id: str | None = SQLField(
        default=None,
        max_length=36,
        description="Request correlation ID",
    )
    created_at: datetime = SQLField(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="Record creation timestamp",
    )
