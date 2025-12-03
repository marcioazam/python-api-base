"""Property-based tests for domain layer.

**Feature: domain-code-review-fixes**
"""

from __future__ import annotations

from datetime import timezone
from decimal import Decimal

import pytest
from hypothesis import given, settings, strategies as st


# **Feature: domain-code-review-fixes, Property 1: Entity Timestamps Are Timezone-Aware**
# **Validates: Requirements 1.1, 1.3**
class TestEntityTimestampsTimezoneAware:
    """Property tests for timezone-aware entity timestamps."""

    def test_audit_log_timestamp_is_timezone_aware(self) -> None:
        """AuditLogDB timestamp field has UTC timezone."""
        from domain.entities.audit_log import AuditLogDB

        audit_log = AuditLogDB(
            action="test_action",
            resource_type="test_resource",
            result="success",
        )

        assert audit_log.timestamp.tzinfo is not None
        assert audit_log.timestamp.tzinfo == timezone.utc
        assert audit_log.created_at.tzinfo is not None
        assert audit_log.created_at.tzinfo == timezone.utc

    def test_item_timestamps_are_timezone_aware(self) -> None:
        """Item timestamp fields have UTC timezone."""
        from domain.entities.item import Item

        item = Item(
            name="Test Item",
            price=10.0,
        )

        assert item.created_at.tzinfo is not None
        assert item.created_at.tzinfo == timezone.utc
        assert item.updated_at.tzinfo is not None
        assert item.updated_at.tzinfo == timezone.utc

    def test_role_timestamps_are_timezone_aware(self) -> None:
        """RoleDB timestamp fields have UTC timezone."""
        from domain.entities.role import RoleDB

        role = RoleDB(name="test_role")

        assert role.created_at.tzinfo is not None
        assert role.created_at.tzinfo == timezone.utc
        assert role.updated_at.tzinfo is not None
        assert role.updated_at.tzinfo == timezone.utc

    def test_user_role_timestamp_is_timezone_aware(self) -> None:
        """UserRoleDB assigned_at field has UTC timezone."""
        from domain.entities.role import UserRoleDB

        user_role = UserRoleDB(
            user_id="01HXYZ123456789ABCDEFGHIJK",
            role_id="01HXYZ123456789ABCDEFGHIJK",
        )

        assert user_role.assigned_at.tzinfo is not None
        assert user_role.assigned_at.tzinfo == timezone.utc

    @given(
        name=st.text(min_size=1, max_size=100),
        price=st.floats(min_value=0.01, max_value=10000, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_item_serialization_includes_timezone(
        self, name: str, price: float
    ) -> None:
        """Item datetime serialization includes timezone info."""
        from domain.entities.item import Item

        item = Item(name=name, price=price)
        
        # Serialize to ISO format
        created_iso = item.created_at.isoformat()
        updated_iso = item.updated_at.isoformat()

        # Should contain timezone indicator
        assert "+" in created_iso or "Z" in created_iso
        assert "+" in updated_iso or "Z" in updated_iso


# **Feature: domain-code-review-fixes, Property 2: Value Object Equality**
# **Validates: Requirements 4.3**
class TestValueObjectEquality:
    """Property tests for value object equality based on attributes."""

    @given(
        amount=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("999999.99"),
            allow_nan=False,
            allow_infinity=False,
            places=2,
        ),
        currency=st.sampled_from(["USD", "EUR", "GBP", "BRL"]),
    )
    @settings(max_examples=100)
    def test_money_equality_by_attributes(
        self, amount: Decimal, currency: str
    ) -> None:
        """Two Money objects with same attributes are equal."""
        from domain.value_objects.money import Money

        money1 = Money(amount, currency)
        money2 = Money(amount, currency)

        # Same attributes = equal
        assert money1 == money2
        assert hash(money1) == hash(money2)

    @given(
        amount1=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("999.99"),
            allow_nan=False,
            allow_infinity=False,
            places=2,
        ),
        amount2=st.decimals(
            min_value=Decimal("1000.00"),
            max_value=Decimal("9999.99"),
            allow_nan=False,
            allow_infinity=False,
            places=2,
        ),
    )
    @settings(max_examples=100)
    def test_money_inequality_different_amounts(
        self, amount1: Decimal, amount2: Decimal
    ) -> None:
        """Two Money objects with different amounts are not equal."""
        from domain.value_objects.money import Money

        money1 = Money(amount1, "USD")
        money2 = Money(amount2, "USD")

        assert money1 != money2

    @given(
        amount=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("999999.99"),
            allow_nan=False,
            allow_infinity=False,
            places=2,
        ),
    )
    @settings(max_examples=100)
    def test_money_inequality_different_currencies(self, amount: Decimal) -> None:
        """Two Money objects with different currencies are not equal."""
        from domain.value_objects.money import Money

        money_usd = Money(amount, "USD")
        money_eur = Money(amount, "EUR")

        assert money_usd != money_eur

    @given(
        ulid=st.from_regex(r"[0-9A-HJKMNP-TV-Z]{26}", fullmatch=True),
    )
    @settings(max_examples=100)
    def test_entity_id_equality_by_value(self, ulid: str) -> None:
        """Two EntityId objects with same value are equal."""
        from domain.value_objects.entity_id import EntityId

        id1 = EntityId(ulid)
        id2 = EntityId(ulid)

        assert id1 == id2
        assert hash(id1) == hash(id2)

    @given(
        ulid=st.from_regex(r"[0-9A-HJKMNP-TV-Z]{26}", fullmatch=True),
    )
    @settings(max_examples=100)
    def test_entity_id_case_insensitive(self, ulid: str) -> None:
        """EntityId normalizes to uppercase for consistent equality."""
        from domain.value_objects.entity_id import EntityId

        id_upper = EntityId(ulid.upper())
        id_lower = EntityId(ulid.lower())

        assert id_upper == id_lower
        assert id_upper.value == id_lower.value

    @given(
        ulid=st.from_regex(r"[0-9A-HJKMNP-TV-Z]{26}", fullmatch=True),
    )
    @settings(max_examples=100)
    def test_typed_ids_with_same_value_are_not_equal(self, ulid: str) -> None:
        """Different typed IDs with same value are not equal (type safety)."""
        from domain.value_objects.entity_id import ItemId, RoleId, UserId

        item_id = ItemId(ulid)
        role_id = RoleId(ulid)
        user_id = UserId(ulid)

        # Different types should not be equal
        assert item_id != role_id
        assert item_id != user_id
        assert role_id != user_id

    def test_entity_id_rejects_invalid_ulid(self) -> None:
        """EntityId rejects invalid ULID formats."""
        from domain.value_objects.entity_id import EntityId

        invalid_ulids = [
            "",  # Empty
            "123",  # Too short
            "01ARZ3NDEKTSV4RRFFQ69G5FAVX",  # Too long (27 chars)
            "01ARZ3NDEKTSV4RRFFQ69G5FA!",  # Invalid character
            "ILOU0000000000000000000000",  # Contains I, L, O, U
        ]

        for invalid in invalid_ulids:
            with pytest.raises(ValueError):
                EntityId(invalid)
