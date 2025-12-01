"""Property-based tests for Audit Log Entry Persistence.

**Feature: architecture-restructuring-2025, Property 15: Audit Log Entry Persistence**
**Validates: Requirements 9.5**
"""

import pytest
from datetime import datetime, UTC, timedelta
from hypothesis import given, settings, assume
from hypothesis import strategies as st

try:
    from my_app.infrastructure.security.audit_log import (
        AuditEntry,
        AuditAction,
        AuditResult,
        AuditFilters,
        InMemoryAuditLogger,
    )
    from my_app.shared.utils.ids import generate_ulid
except ImportError:
    pytest.skip("my_app modules not available", allow_module_level=True)


# Strategies
user_id_strategy = st.text(min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_")
resource_type_strategy = st.sampled_from(["user", "order", "item", "config", "role"])
resource_id_strategy = st.text(min_size=1, max_size=30, alphabet="0123456789ABCDEFGHJKMNPQRSTVWXYZ")
action_strategy = st.sampled_from(list(AuditAction))
result_strategy = st.sampled_from(list(AuditResult))
ip_strategy = st.from_regex(r"^(\d{1,3}\.){3}\d{1,3}$", fullmatch=True)
details_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz_"),
    values=st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
    max_size=5,
)


class TestAuditLogPersistence:
    """Property tests for audit log entry persistence."""

    @settings(max_examples=50)
    @given(
        user_id=user_id_strategy,
        action=action_strategy,
        resource_type=resource_type_strategy,
        resource_id=resource_id_strategy,
        result=result_strategy,
    )
    @pytest.mark.asyncio
    async def test_logged_entry_is_retrievable(
        self,
        user_id: str,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        result: AuditResult,
    ) -> None:
        """
        **Feature: architecture-restructuring-2025, Property 15: Audit Log Entry Persistence**
        
        For any auditable action performed, an audit log entry SHALL be created
        and SHALL be retrievable by query.
        **Validates: Requirements 9.5**
        """
        logger = InMemoryAuditLogger()
        
        entry = await logger.log_action(
            action=action,
            resource_type=resource_type,
            result=result,
            user_id=user_id,
            resource_id=resource_id,
        )
        
        # Query by user_id
        filters = AuditFilters(user_id=user_id)
        results = await logger.query(filters)
        
        assert len(results) >= 1
        found = any(e.id == entry.id for e in results)
        assert found, "Logged entry should be retrievable"

    @settings(max_examples=50)
    @given(
        user_id=user_id_strategy,
        action=action_strategy,
        resource_type=resource_type_strategy,
        details=details_strategy,
    )
    @pytest.mark.asyncio
    async def test_entry_contains_required_fields(
        self,
        user_id: str,
        action: AuditAction,
        resource_type: str,
        details: dict,
    ) -> None:
        """
        For any audit entry, it SHALL contain action type, actor, timestamp, and context.
        **Validates: Requirements 9.5**
        """
        logger = InMemoryAuditLogger()
        
        entry = await logger.log_action(
            action=action,
            resource_type=resource_type,
            user_id=user_id,
            details=details,
        )
        
        # Verify required fields
        assert entry.id is not None
        assert entry.timestamp is not None
        assert entry.action == action.value
        assert entry.resource_type == resource_type
        assert entry.user_id == user_id
        assert entry.result is not None
        assert entry.details == details

    @settings(max_examples=30)
    @given(
        user_id=user_id_strategy,
        action=action_strategy,
        resource_type=resource_type_strategy,
        ip_address=ip_strategy,
    )
    @pytest.mark.asyncio
    async def test_query_by_action_type(
        self,
        user_id: str,
        action: AuditAction,
        resource_type: str,
        ip_address: str,
    ) -> None:
        """
        For any action type, querying by that action SHALL return matching entries.
        **Validates: Requirements 9.5**
        """
        logger = InMemoryAuditLogger()
        
        # Log entry with specific action
        await logger.log_action(
            action=action,
            resource_type=resource_type,
            user_id=user_id,
            ip_address=ip_address,
        )
        
        # Query by action
        filters = AuditFilters(action=action.value)
        results = await logger.query(filters)
        
        assert len(results) >= 1
        assert all(e.action == action.value for e in results)

    @settings(max_examples=30)
    @given(
        user_id=user_id_strategy,
        resource_type=resource_type_strategy,
    )
    @pytest.mark.asyncio
    async def test_query_by_resource_type(
        self,
        user_id: str,
        resource_type: str,
    ) -> None:
        """
        For any resource type, querying by that type SHALL return matching entries.
        **Validates: Requirements 9.5**
        """
        logger = InMemoryAuditLogger()
        
        await logger.log_action(
            action=AuditAction.CREATE,
            resource_type=resource_type,
            user_id=user_id,
        )
        
        filters = AuditFilters(resource_type=resource_type)
        results = await logger.query(filters)
        
        assert len(results) >= 1
        assert all(e.resource_type == resource_type for e in results)

    @settings(max_examples=20)
    @given(
        user_id=user_id_strategy,
        result=result_strategy,
    )
    @pytest.mark.asyncio
    async def test_query_by_result(
        self,
        user_id: str,
        result: AuditResult,
    ) -> None:
        """
        For any result type, querying by that result SHALL return matching entries.
        **Validates: Requirements 9.5**
        """
        logger = InMemoryAuditLogger()
        
        await logger.log_action(
            action=AuditAction.LOGIN,
            resource_type="session",
            user_id=user_id,
            result=result,
        )
        
        filters = AuditFilters(result=result.value)
        results = await logger.query(filters)
        
        assert len(results) >= 1
        assert all(e.result == result.value for e in results)

    @settings(max_examples=20)
    @given(
        action=action_strategy,
        resource_type=resource_type_strategy,
        details=details_strategy,
    )
    def test_entry_serialization_roundtrip(
        self,
        action: AuditAction,
        resource_type: str,
        details: dict,
    ) -> None:
        """
        For any audit entry, serializing to dict/JSON and back SHALL preserve all fields.
        **Validates: Requirements 9.5**
        """
        entry = AuditEntry(
            id=generate_ulid(),
            timestamp=datetime.now(UTC),
            action=action.value,
            resource_type=resource_type,
            result=AuditResult.SUCCESS.value,
            user_id="test_user",
            details=details,
        )
        
        # Dict round-trip
        entry_dict = entry.to_dict()
        restored = AuditEntry.from_dict(entry_dict)
        
        assert restored.id == entry.id
        assert restored.action == entry.action
        assert restored.resource_type == entry.resource_type
        assert restored.result == entry.result
        assert restored.user_id == entry.user_id
        assert restored.details == entry.details

    @settings(max_examples=20)
    @given(
        action=action_strategy,
        resource_type=resource_type_strategy,
    )
    def test_json_serialization_roundtrip(
        self,
        action: AuditAction,
        resource_type: str,
    ) -> None:
        """
        For any audit entry, JSON serialization round-trip SHALL preserve data.
        **Validates: Requirements 9.5**
        """
        entry = AuditEntry(
            id=generate_ulid(),
            timestamp=datetime.now(UTC),
            action=action.value,
            resource_type=resource_type,
            result=AuditResult.SUCCESS.value,
        )
        
        json_str = entry.to_json()
        restored = AuditEntry.from_json(json_str)
        
        assert restored.id == entry.id
        assert restored.action == entry.action
        assert restored.resource_type == entry.resource_type
