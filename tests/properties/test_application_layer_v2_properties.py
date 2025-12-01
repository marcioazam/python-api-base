"""Property-based tests for Application Layer V2.

**Feature: application-layer-code-review-v2**
**Properties 1-8: Mapper and UseCase Properties**
**Validates: Requirements 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 3.3, 5.1, 5.2, 5.3, 6.2, 7.3**
"""

import logging
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from my_app.application.mappers.item_mapper import ItemMapper
from my_app.application.use_cases.item_use_case import ItemUseCase
from my_app.core.exceptions import ValidationError
from my_app.domain.entities.item import Item, ItemCreate, ItemResponse, ItemUpdate


# Strategies for valid item data
valid_names = st.text(min_size=1, max_size=255).filter(lambda x: x.strip())
valid_prices = st.floats(min_value=0.01, max_value=1_000_000.0, allow_nan=False)
valid_taxes = st.floats(min_value=0.0, max_value=100_000.0, allow_nan=False) | st.none()
valid_descriptions = st.text(max_size=1000) | st.none()

# Strategy for invalid types
invalid_types = st.one_of(
    st.integers(),
    st.text(),
    st.lists(st.integers()),
    st.dictionaries(st.text(), st.integers()),
    st.floats(allow_nan=False),
)


class TestProperty1MapperRoundTripConsistency:
    """Property 1: Mapper Round-Trip Consistency.

    **Feature: application-layer-code-review-v2, Property 1**
    **Validates: Requirements 5.1**

    For any valid Item entity, converting to DTO and back to entity
    should preserve essential data fields.
    """

    @given(
        name=valid_names,
        price=valid_prices,
        tax=valid_taxes,
        description=valid_descriptions,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_round_trip_preserves_essential_fields(
        self,
        name: str,
        price: float,
        tax: float | None,
        description: str | None,
    ) -> None:
        """Item -> ItemResponse -> Item preserves essential fields."""
        original = Item(
            name=name,
            price=price,
            tax=tax,
            description=description,
        )

        mapper = ItemMapper()

        dto = mapper.to_dto(original)
        back = mapper.to_entity(dto)

        assert back.name == original.name
        assert back.price == original.price
        assert back.tax == original.tax
        assert back.description == original.description
        assert back.id == original.id
        assert back.created_at == original.created_at
        assert back.updated_at == original.updated_at


class TestProperty2InputTypeValidation:
    """Property 2: Input Type Validation.

    **Feature: application-layer-code-review-v2, Property 2**
    **Validates: Requirements 2.1, 2.2**

    For any input that is not the expected type, mapper raises TypeError.
    For None inputs, mapper raises ValueError.
    """

    @given(invalid_input=invalid_types)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_to_dto_raises_type_error_for_invalid_types(
        self,
        invalid_input: Any,
    ) -> None:
        """to_dto raises TypeError with descriptive message for invalid types."""
        mapper = ItemMapper()

        with pytest.raises(TypeError) as exc_info:
            mapper.to_dto(invalid_input)

        assert "Expected Item instance" in str(exc_info.value)
        assert type(invalid_input).__name__ in str(exc_info.value)

    @given(invalid_input=invalid_types)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_to_entity_raises_type_error_for_invalid_types(
        self,
        invalid_input: Any,
    ) -> None:
        """to_entity raises TypeError with descriptive message for invalid types."""
        mapper = ItemMapper()

        with pytest.raises(TypeError) as exc_info:
            mapper.to_entity(invalid_input)

        assert "Expected ItemResponse instance" in str(exc_info.value)
        assert type(invalid_input).__name__ in str(exc_info.value)

    def test_to_dto_raises_value_error_for_none(self) -> None:
        """to_dto raises ValueError for None input."""
        mapper = ItemMapper()

        with pytest.raises(ValueError) as exc_info:
            mapper.to_dto(None)

        assert "entity parameter cannot be None" in str(exc_info.value)

    def test_to_entity_raises_value_error_for_none(self) -> None:
        """to_entity raises ValueError for None input."""
        mapper = ItemMapper()

        with pytest.raises(ValueError) as exc_info:
            mapper.to_entity(None)

        assert "dto parameter cannot be None" in str(exc_info.value)


class TestProperty3StructuredLoggingContext:
    """Property 3: Structured Logging Context.

    **Feature: application-layer-code-review-v2, Property 3**
    **Validates: Requirements 1.1, 1.2**

    For any mapping operation, logger receives structured context
    with entity_type, operation, and timestamp fields.
    """

    @given(
        name=valid_names,
        price=valid_prices,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_to_dto_logs_structured_context(
        self,
        name: str,
        price: float,
    ) -> None:
        """to_dto logs with structured context containing required fields."""
        item = Item(name=name, price=price)
        mapper = ItemMapper()

        with patch(
            "my_app.application.mappers.item_mapper.logger"
        ) as mock_logger:
            mapper.to_dto(item)

            assert mock_logger.debug.called
            call_args = mock_logger.debug.call_args_list[0]
            extra = call_args.kwargs.get("extra", {})
            context = extra.get("context", {})

            assert "entity_type" in context
            assert context["entity_type"] == "Item"
            assert "operation" in context
            assert context["operation"] == "to_dto"
            assert "timestamp" in context

    @given(
        name=valid_names,
        price=valid_prices,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_to_entity_logs_structured_context(
        self,
        name: str,
        price: float,
    ) -> None:
        """to_entity logs with structured context containing required fields."""
        item = Item(name=name, price=price)
        mapper = ItemMapper()
        dto = mapper.to_dto(item)

        with patch(
            "my_app.application.mappers.item_mapper.logger"
        ) as mock_logger:
            mapper.to_entity(dto)

            assert mock_logger.debug.called
            call_args = mock_logger.debug.call_args_list[0]
            extra = call_args.kwargs.get("extra", {})
            context = extra.get("context", {})

            assert "entity_type" in context
            assert context["entity_type"] == "ItemResponse"
            assert "operation" in context
            assert context["operation"] == "to_entity"
            assert "timestamp" in context


class TestProperty4ValidationHookInvocation:
    """Property 4: Validation Hook Invocation.

    **Feature: application-layer-code-review-v2, Property 4**
    **Validates: Requirements 3.1, 3.2, 3.3**

    For any create/update operation, validation hooks are invoked
    before repository operations.
    """

    def test_validate_create_called_with_invalid_price_low(self) -> None:
        """_validate_create raises ValidationError for price below minimum."""
        mock_repo = MagicMock()
        mock_mapper = MagicMock()
        use_case = ItemUseCase(repository=mock_repo, mapper=mock_mapper)

        data = ItemCreate(name="Test", price=0.02)
        # Manually set price below minimum to bypass Pydantic validation
        object.__setattr__(data, "price", 0.001)

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_create(data)

        errors = exc_info.value.details.get("errors", [])
        assert any(err["field"] == "price" for err in errors)

    def test_validate_create_called_with_invalid_price_high(self) -> None:
        """_validate_create raises ValidationError for price above maximum."""
        mock_repo = MagicMock()
        mock_mapper = MagicMock()
        use_case = ItemUseCase(repository=mock_repo, mapper=mock_mapper)

        data = ItemCreate(name="Test", price=100.0)
        # Manually set price above maximum to bypass Pydantic validation
        object.__setattr__(data, "price", 2_000_000.0)

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_create(data)

        errors = exc_info.value.details.get("errors", [])
        assert any(err["field"] == "price" for err in errors)

    def test_validate_create_called_with_long_name(self) -> None:
        """_validate_create raises ValidationError for name exceeding max length."""
        mock_repo = MagicMock()
        mock_mapper = MagicMock()
        use_case = ItemUseCase(repository=mock_repo, mapper=mock_mapper)

        data = ItemCreate(name="Test", price=10.0)
        # Manually set name to exceed max length
        object.__setattr__(data, "name", "x" * 300)

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_create(data)

        errors = exc_info.value.details.get("errors", [])
        assert any(err["field"] == "name" for err in errors)

    def test_validate_update_only_validates_present_fields(self) -> None:
        """_validate_update only validates fields that are not None."""
        mock_repo = MagicMock()
        mock_mapper = MagicMock()
        use_case = ItemUseCase(repository=mock_repo, mapper=mock_mapper)

        # None price should not trigger validation
        data = ItemUpdate(name="Valid Name", price=None)
        use_case._validate_update(data)  # Should not raise

    def test_validate_update_raises_for_invalid_price(self) -> None:
        """_validate_update raises ValidationError for invalid price when present."""
        mock_repo = MagicMock()
        mock_mapper = MagicMock()
        use_case = ItemUseCase(repository=mock_repo, mapper=mock_mapper)

        data = ItemUpdate(price=10.0)
        # Manually set price below minimum
        object.__setattr__(data, "price", 0.001)

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_update(data)

        errors = exc_info.value.details.get("errors", [])
        assert any(err["field"] == "price" for err in errors)

    def test_validation_error_has_field_level_details(self) -> None:
        """ValidationError contains field-level error details."""
        mock_repo = MagicMock()
        mock_mapper = MagicMock()
        use_case = ItemUseCase(repository=mock_repo, mapper=mock_mapper)

        data = ItemCreate(name="Test", price=10.0)
        # Manually set invalid values
        object.__setattr__(data, "name", "x" * 300)
        object.__setattr__(data, "price", 0.001)

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_create(data)

        errors = exc_info.value.details.get("errors", [])
        assert len(errors) >= 2
        fields = [err["field"] for err in errors]
        assert "name" in fields
        assert "price" in fields


class TestProperty5MapperStatelessness:
    """Property 5: Mapper Statelessness.

    **Feature: application-layer-code-review-v2, Property 5**
    **Validates: Requirements 6.2**

    For any sequence of mapping operations, each operation produces
    the same result for the same input.
    """

    @given(
        name=valid_names,
        price=valid_prices,
        tax=valid_taxes,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_mapper_produces_same_output_for_same_input(
        self,
        name: str,
        price: float,
        tax: float | None,
    ) -> None:
        """Same input produces same output regardless of previous operations."""
        item = Item(name=name, price=price, tax=tax)
        mapper = ItemMapper()

        # First conversion
        dto1 = mapper.to_dto(item)

        # Do some other operations
        other_item = Item(name="Other", price=99.99)
        mapper.to_dto(other_item)
        mapper.to_entity(dto1)

        # Second conversion of same input
        dto2 = mapper.to_dto(item)

        assert dto1.name == dto2.name
        assert dto1.price == dto2.price
        assert dto1.tax == dto2.tax
        assert dto1.id == dto2.id


class TestProperty6JSONSerializationRoundTrip:
    """Property 6: JSON Serialization Round-Trip.

    **Feature: application-layer-code-review-v2, Property 6**
    **Validates: Requirements 7.3**

    For any valid ItemResponse, serializing to JSON and parsing back
    preserves all fields.
    """

    @given(
        name=valid_names,
        price=valid_prices,
        tax=valid_taxes,
        description=valid_descriptions,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_json_round_trip_preserves_all_fields(
        self,
        name: str,
        price: float,
        tax: float | None,
        description: str | None,
    ) -> None:
        """ItemResponse -> JSON -> ItemResponse preserves all fields."""
        item = Item(name=name, price=price, tax=tax, description=description)
        mapper = ItemMapper()
        dto = mapper.to_dto(item)

        json_str = dto.model_dump_json()
        restored = ItemResponse.model_validate_json(json_str)

        assert restored.name == dto.name
        assert restored.price == dto.price
        assert restored.tax == dto.tax
        assert restored.description == dto.description
        assert restored.id == dto.id
        assert restored.price_with_tax == dto.price_with_tax


class TestProperty7TimestampTimezonePreservation:
    """Property 7: Timestamp Timezone Preservation.

    **Feature: application-layer-code-review-v2, Property 7**
    **Validates: Requirements 5.3**

    For any Item with timezone-aware timestamps, mapper preserves
    timezone information.
    """

    @given(
        name=valid_names,
        price=valid_prices,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_timezone_preserved_through_conversion(
        self,
        name: str,
        price: float,
    ) -> None:
        """Timezone-aware timestamps preserved through mapper conversion."""
        now = datetime.now(timezone.utc)
        item = Item(
            name=name,
            price=price,
            created_at=now,
            updated_at=now,
        )
        mapper = ItemMapper()

        dto = mapper.to_dto(item)
        back = mapper.to_entity(dto)

        assert back.created_at.tzinfo is not None
        assert back.updated_at.tzinfo is not None
        assert back.created_at == item.created_at
        assert back.updated_at == item.updated_at


class TestProperty8ComputedFieldExclusion:
    """Property 8: Computed Field Exclusion.

    **Feature: application-layer-code-review-v2, Property 8**
    **Validates: Requirements 5.2**

    For any ItemResponse with computed fields, to_entity excludes
    them without validation errors.
    """

    @given(
        name=valid_names,
        price=valid_prices,
        tax=valid_taxes,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_computed_fields_excluded_in_to_entity(
        self,
        name: str,
        price: float,
        tax: float | None,
    ) -> None:
        """to_entity excludes price_with_tax without validation errors."""
        item = Item(name=name, price=price, tax=tax)
        mapper = ItemMapper()

        dto = mapper.to_dto(item)
        assert hasattr(dto, "price_with_tax")
        assert dto.price_with_tax == price + (tax or 0)

        # Should not raise even though DTO has computed field
        back = mapper.to_entity(dto)

        assert not hasattr(back, "price_with_tax") or "price_with_tax" not in back.model_fields
        assert back.price == price
        assert back.tax == tax
