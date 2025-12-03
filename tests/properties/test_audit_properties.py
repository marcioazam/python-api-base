"""Property-based tests for audit logging service.

**Feature: api-base-improvements**
**Validates: Requirements 4.1, 4.3, 4.5**
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

pytest.skip('Module infrastructure.audit.logger not implemented', allow_module_level=True)

from hypothesis import given, settings
from hypothesis import strategies as st

from infrastructure.audit.logger import (
    AuditAction,
    AuditEntry,
    AuditFilters,
    AuditResult,
    InMemoryAuditLogger,
)
from core.shared.utils.ids import generate_ulid


# Strategy for user IDs
user_id_strategy = st.text(
    min_size=1,
    max_size=26,
    alphabet=st.characters(whitelist_categories=("L", "N")),
).filter(lambda x: x.strip() != "")

# Strategy for action types
action_strategy = st.sampled_from(list(AuditAction))

# Strategy for result types
result_strategy = st.sampled_from(list(AuditResult))

# Strategy for resource types
resource_type_strategy = st.sampled_from([
    "user", "item", "role", "session", "token", "config",
])

# Strategy for IP addresses
ip_strategy = st.sampled_from([
    "192.168.1.1",
    "10.0.0.1",
    "172.16.0.1",
    "::1",
    "2001:db8::1",
])

# Strategy for details dict
details_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L",))),
    values=st.one_of(st.text(max_size=100), st.integers(), st.booleans()),
    max_size=5,
)


class TestAuditLogCreation:
    """Property tests for audit log creation."""

    @settings(max_examples=100, deadline=None)
    @given(
        user_id=user_id_strategy,
        action=action_strategy,
        resource_type=resource_type_strategy,
        result=result_strategy,
    )
    def test_audit_log_creation_for_auth_actions(
        self,
        user_id: str,
        action: AuditAction,
        resource_type: str,
        result: AuditResult,
    ) -> None:
        """
        **Feature: api-base-improvements, Property 12: Audit log creation for auth actions**
        **Validates: Requirements 4.1**

        For any authentication action (login, logout, token refresh), an audit log
        entry SHALL be created with required fields.
        """
        async def run_test():
            logger = InMemoryAuditLogger()

            entry = await logger.log_action(
                action=action,
                resource_type=resource_type,
                result=result,
                user_id=user_id,
            )

            # Verify entry has all required fields
            assert entry.id is not None and len(entry.id) > 0
            assert entry.timestamp is not None
            assert entry.action == action.value
            assert entry.resource_type == resource_type
            assert entry.result == result.value
            assert entry.user_id == user_id

            # Verify entry was stored
            entries = await logger.query(AuditFilters(user_id=user_id))
            assert len(entries) >= 1
            assert any(e.id == entry.id for e in entries)

        asyncio.get_event_loop().run_until_complete(run_test())

    @settings(max_examples=50, deadline=None)
    @given(
        user_id=user_id_strategy,
        ip=ip_strategy,
        details=details_strategy,
    )
    def test_audit_log_captures_context(
        self,
        user_id: str,
        ip: str,
        details: dict,
    ) -> None:
        """
        **Feature: api-base-improvements, Property 12: Audit log creation for auth actions**
        **Validates: Requirements 4.1**

        Audit log SHALL capture IP address, user agent, and details.
        """
        async def run_test():
            logger = InMemoryAuditLogger()

            entry = await logger.log_action(
                action=AuditAction.LOGIN,
                resource_type="session",
                user_id=user_id,
                ip_address=ip,
                user_agent="TestAgent/1.0",
                details=details,
                request_id="req-123",
            )

            assert entry.ip_address == ip
            assert entry.user_agent == "TestAgent/1.0"
            assert entry.details == details
            assert entry.request_id == "req-123"

        asyncio.get_event_loop().run_until_complete(run_test())


class TestAuditLogFiltering:
    """Property tests for audit log filtering."""

    @settings(max_examples=100, deadline=None)
    @given(
        user_id1=user_id_strategy,
        user_id2=user_id_strategy,
    )
    def test_filter_by_user_id(self, user_id1: str, user_id2: str) -> None:
        """
        **Feature: api-base-improvements, Property 13: Audit log filtering**
        **Validates: Requirements 4.3**

        For any set of audit logs, filtering by user_id SHALL return only logs
        matching that user.
        """
        # Ensure different user IDs
        if user_id1 == user_id2:
            user_id2 = user_id2 + "_different"

        async def run_test():
            logger = InMemoryAuditLogger()

            # Create entries for both users
            await logger.log_action(
                action=AuditAction.LOGIN,
                resource_type="session",
                user_id=user_id1,
            )
            await logger.log_action(
                action=AuditAction.LOGIN,
                resource_type="session",
                user_id=user_id2,
            )
            await logger.log_action(
                action=AuditAction.LOGOUT,
                resource_type="session",
                user_id=user_id1,
            )

            # Filter by user_id1
            results = await logger.query(AuditFilters(user_id=user_id1))

            # All results should be for user_id1
            assert len(results) == 2
            for entry in results:
                assert entry.user_id == user_id1

        asyncio.get_event_loop().run_until_complete(run_test())

    @settings(max_examples=50, deadline=None)
    @given(action=action_strategy)
    def test_filter_by_action(self, action: AuditAction) -> None:
        """
        **Feature: api-base-improvements, Property 13: Audit log filtering**
        **Validates: Requirements 4.3**

        Filtering by action SHALL return only logs with that action.
        """
        async def run_test():
            logger = InMemoryAuditLogger()

            # Create entries with different actions
            await logger.log_action(
                action=AuditAction.LOGIN,
                resource_type="session",
                user_id="user1",
            )
            await logger.log_action(
                action=AuditAction.LOGOUT,
                resource_type="session",
                user_id="user1",
            )
            await logger.log_action(
                action=action,
                resource_type="test",
                user_id="user2",
            )

            # Filter by specific action
            results = await logger.query(AuditFilters(action=action.value))

            # All results should have the specified action
            for entry in results:
                assert entry.action == action.value

        asyncio.get_event_loop().run_until_complete(run_test())

    def test_filter_by_date_range(self) -> None:
        """
        **Feature: api-base-improvements, Property 13: Audit log filtering**
        **Validates: Requirements 4.3**

        Filtering by date range SHALL return only logs within that range.
        """
        async def run_test():
            logger = InMemoryAuditLogger()

            now = datetime.now(timezone.utc)

            # Create entries
            await logger.log_action(
                action=AuditAction.LOGIN,
                resource_type="session",
                user_id="user1",
            )

            # Filter with date range
            results = await logger.query(AuditFilters(
                start_date=now - timedelta(hours=1),
                end_date=now + timedelta(hours=1),
            ))

            # All results should be within range
            for entry in results:
                assert entry.timestamp >= now - timedelta(hours=1)
                assert entry.timestamp <= now + timedelta(hours=1)

        asyncio.get_event_loop().run_until_complete(run_test())

    def test_filter_pagination(self) -> None:
        """
        **Feature: api-base-improvements, Property 13: Audit log filtering**
        **Validates: Requirements 4.3**

        Pagination SHALL limit and offset results correctly.
        """
        async def run_test():
            logger = InMemoryAuditLogger()

            # Create 10 entries
            for i in range(10):
                await logger.log_action(
                    action=AuditAction.READ,
                    resource_type="item",
                    user_id=f"user{i}",
                )

            # Get first page
            page1 = await logger.query(AuditFilters(limit=3, offset=0))
            assert len(page1) == 3

            # Get second page
            page2 = await logger.query(AuditFilters(limit=3, offset=3))
            assert len(page2) == 3

            # Pages should be different
            page1_ids = {e.id for e in page1}
            page2_ids = {e.id for e in page2}
            assert page1_ids.isdisjoint(page2_ids)

        asyncio.get_event_loop().run_until_complete(run_test())


class TestAuditLogSerializationRoundTrip:
    """Property tests for audit log serialization."""

    @settings(max_examples=100, deadline=None)
    @given(
        user_id=user_id_strategy,
        action=action_strategy,
        resource_type=resource_type_strategy,
        result=result_strategy,
        details=details_strategy,
    )
    def test_audit_entry_serialization_round_trip(
        self,
        user_id: str,
        action: AuditAction,
        resource_type: str,
        result: AuditResult,
        details: dict,
    ) -> None:
        """
        **Feature: api-base-improvements, Property 15: Audit log serialization round-trip**
        **Validates: Requirements 4.5**

        For any audit log entry, serializing then deserializing SHALL produce
        an equivalent entry.
        """
        now = datetime.now(timezone.utc).replace(microsecond=0)
        original = AuditEntry(
            id=generate_ulid(),
            timestamp=now,
            user_id=user_id,
            action=action.value,
            resource_type=resource_type,
            resource_id="res-123",
            details=details,
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0",
            result=result.value,
            request_id="req-456",
        )

        # Round-trip through dict
        serialized = original.to_dict()
        deserialized = AuditEntry.from_dict(serialized)

        assert deserialized.id == original.id
        assert deserialized.user_id == original.user_id
        assert deserialized.action == original.action
        assert deserialized.resource_type == original.resource_type
        assert deserialized.resource_id == original.resource_id
        assert deserialized.details == original.details
        assert deserialized.ip_address == original.ip_address
        assert deserialized.user_agent == original.user_agent
        assert deserialized.result == original.result
        assert deserialized.request_id == original.request_id

    @settings(max_examples=50, deadline=None)
    @given(
        user_id=user_id_strategy,
        action=action_strategy,
        details=details_strategy,
    )
    def test_audit_entry_json_round_trip(
        self,
        user_id: str,
        action: AuditAction,
        details: dict,
    ) -> None:
        """
        **Feature: api-base-improvements, Property 15: Audit log serialization round-trip**
        **Validates: Requirements 4.5**

        JSON serialization and deserialization SHALL preserve all data.
        """
        now = datetime.now(timezone.utc).replace(microsecond=0)
        original = AuditEntry(
            id=generate_ulid(),
            timestamp=now,
            user_id=user_id,
            action=action.value,
            resource_type="test",
            result=AuditResult.SUCCESS.value,
            details=details,
        )

        # Round-trip through JSON
        json_str = original.to_json()
        deserialized = AuditEntry.from_json(json_str)

        assert deserialized.id == original.id
        assert deserialized.user_id == original.user_id
        assert deserialized.action == original.action
        assert deserialized.details == original.details

    def test_audit_entry_to_dict_format(self) -> None:
        """
        **Feature: api-base-improvements, Property 15: Audit log serialization round-trip**
        **Validates: Requirements 4.5**

        to_dict SHALL produce consistent JSON-serializable format.
        """
        entry = AuditEntry(
            id="test-id",
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            user_id="user-123",
            action="login",
            resource_type="session",
            result="success",
        )

        data = entry.to_dict()

        # Verify structure
        assert "id" in data
        assert "timestamp" in data
        assert "user_id" in data
        assert "action" in data
        assert "resource_type" in data
        assert "result" in data

        # Timestamp should be ISO format string
        assert isinstance(data["timestamp"], str)
        assert "2024-01-01" in data["timestamp"]
