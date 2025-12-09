"""Property-based tests for domain layer.

**Feature: domain-code-review-fixes**
**Feature: python-api-base-2025-validation**
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass
from datetime import UTC
from decimal import Decimal

import pytest
from hypothesis import given, settings, strategies as st

from core.base.domain.aggregate_root import AggregateRoot
from core.base.domain.value_object import (
    BaseValueObject,
    EntityId,
    ItemId,
    RoleId,
    UserId,
)
from core.base.events.domain_event import EntityCreatedEvent
from domain.common.value_objects import Money
from domain.examples.item.entity import ItemExample
from domain.examples.item.entity import Money as ItemMoney


class TestEntityTimestampsTimezoneAware:
    """Property tests for timezone-aware entity timestamps."""

    def test_item_example_timestamps_are_timezone_aware(self) -> None:
        """ItemExample timestamp fields have UTC timezone."""
        item = ItemExample.create(
            name="Test Item",
            description="A test item",
            price=ItemMoney(Decimal("10.00")),
            sku="TEST-001",
        )

        assert item.created_at.tzinfo is not None
        assert item.created_at.tzinfo == UTC
        assert item.updated_at.tzinfo is not None
        assert item.updated_at.tzinfo == UTC

    @given(
        name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        price=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("10000"),
            allow_nan=False,
            places=2,
        ),
    )
    @settings(max_examples=50)
    def test_item_serialization_includes_timezone(
        self, name: str, price: Decimal
    ) -> None:
        """ItemExample datetime serialization includes timezone info."""
        item = ItemExample.create(
            name=name,
            description="Test",
            price=ItemMoney(price),
            sku="TEST-001",
        )

        created_iso = item.created_at.isoformat()
        updated_iso = item.updated_at.isoformat()

        assert "+" in created_iso or "Z" in created_iso
        assert "+" in updated_iso or "Z" in updated_iso


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
        money1 = Money(amount, currency)
        money2 = Money(amount, currency)

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
        money_usd = Money(amount, "USD")
        money_eur = Money(amount, "EUR")

        assert money_usd != money_eur

    @given(
        ulid=st.from_regex(r"[0-9A-HJKMNP-TV-Z]{26}", fullmatch=True),
    )
    @settings(max_examples=100)
    def test_entity_id_equality_by_value(self, ulid: str) -> None:
        """Two EntityId objects with same value are equal."""
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
        item_id = ItemId(ulid)
        role_id = RoleId(ulid)
        user_id = UserId(ulid)

        assert item_id != role_id
        assert item_id != user_id
        assert role_id != user_id

    def test_entity_id_rejects_invalid_ulid(self) -> None:
        """EntityId rejects invalid ULID formats."""
        invalid_ulids = [
            "",
            "123",
            "01ARZ3NDEKTSV4RRFFQ69G5FAVX",
            "01ARZ3NDEKTSV4RRFFQ69G5FA!",
            "ILOU0000000000000000000000",
        ]

        for invalid in invalid_ulids:
            with pytest.raises(ValueError):
                EntityId(invalid)


class TestAggregateRootEventCollection:
    """Property tests for aggregate root event collection."""

    @given(st.integers(min_value=0, max_value=20))
    @settings(max_examples=100)
    def test_events_added_are_retrievable(self, event_count: int) -> None:
        """Events added via add_event are retrievable via get_pending_events."""
        aggregate: AggregateRoot[str] = AggregateRoot(id="test-aggregate-id")

        for i in range(event_count):
            event = EntityCreatedEvent(entity_type=f"TestEntity_{i}", entity_id=str(i))
            aggregate.add_event(event)

        pending = aggregate.get_pending_events()
        assert len(pending) == event_count

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=100)
    def test_clear_removes_all_events(self, event_count: int) -> None:
        """clear_events removes all pending events."""
        aggregate: AggregateRoot[str] = AggregateRoot(id="test-aggregate-id")

        for i in range(event_count):
            event = EntityCreatedEvent(entity_type=f"TestEntity_{i}", entity_id=str(i))
            aggregate.add_event(event)

        aggregate.clear_events()

        assert len(aggregate.get_pending_events()) == 0

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=100)
    def test_events_order_preserved(self, event_count: int) -> None:
        """Event order is preserved when adding multiple events."""
        aggregate: AggregateRoot[str] = AggregateRoot(id="test-aggregate-id")

        for i in range(event_count):
            event = EntityCreatedEvent(entity_type=f"Entity_{i:03d}", entity_id=str(i))
            aggregate.add_event(event)

        pending = aggregate.get_pending_events()
        for i, event in enumerate(pending):
            assert event.entity_type == f"Entity_{i:03d}"


class TestValueObjectImmutability:
    """Property tests for value object immutability."""

    @given(
        st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        st.integers(),
    )
    @settings(max_examples=100)
    def test_frozen_dataclass_raises_on_modification(
        self, value: str, number: int
    ) -> None:
        """Frozen dataclass value objects raise error on modification."""

        @dataclass(frozen=True)
        class TestVO(BaseValueObject):
            value: str
            number: int

        vo = TestVO(value=value, number=number)

        with pytest.raises(FrozenInstanceError):
            vo.value = "modified"  # type: ignore[misc]

        with pytest.raises(FrozenInstanceError):
            vo.number = 999  # type: ignore[misc]

        assert vo.value == value
        assert vo.number == number

    @given(st.text(min_size=1, max_size=50).filter(lambda x: x.strip()))
    @settings(max_examples=100)
    def test_entity_created_event_immutable(self, entity_type: str) -> None:
        """EntityCreatedEvent (frozen dataclass) rejects modification."""
        event = EntityCreatedEvent(entity_type=entity_type, entity_id="test-id")

        with pytest.raises(FrozenInstanceError):
            event.entity_type = "modified"  # type: ignore[misc]

        with pytest.raises(FrozenInstanceError):
            event.entity_id = "new-id"  # type: ignore[misc]

        assert event.entity_type == entity_type
        assert event.entity_id == "test-id"
