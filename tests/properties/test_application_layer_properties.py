"""Property-based tests for Application Layer.

**Feature: application-layer-review**
**Properties 1-2: Mapper and Module Properties**
**Validates: Requirements 1.1, 3.1, 3.2**
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from my_app.application.mappers.item_mapper import ItemMapper
from my_app.domain.entities.item import Item, ItemResponse
from my_app.application.common.mapper import MapperError


# Strategy for valid item data
valid_names = st.text(min_size=1, max_size=255).filter(lambda x: x.strip())
valid_prices = st.floats(min_value=0.01, max_value=10000.0, allow_nan=False)
valid_taxes = st.floats(min_value=0.0, max_value=1000.0, allow_nan=False) | st.none()
valid_descriptions = st.text(max_size=1000) | st.none()


class TestMapperRoundTripConsistency:
    """Property 1: Mapper Round-Trip Consistency.

    For any valid Item entity, converting to DTO and back to entity
    should preserve essential data fields.
    """

    @given(
        name=valid_names,
        price=valid_prices,
        tax=valid_taxes,
        description=valid_descriptions,
    )
    @settings(max_examples=100)
    def test_round_trip_preserves_data(
        self,
        name: str,
        price: float,
        tax: float | None,
        description: str | None,
    ) -> None:
        """Converting Item -> ItemResponse -> Item preserves data."""
        # Create original item
        original = Item(
            name=name,
            price=price,
            tax=tax,
            description=description,
        )

        mapper = ItemMapper()

        # Round trip: entity -> dto -> entity
        dto = mapper.to_dto(original)
        back = mapper.to_entity(dto)

        # Verify essential fields preserved
        assert back.name == original.name
        assert back.price == original.price
        assert back.tax == original.tax
        assert back.description == original.description
        assert back.id == original.id

    @given(
        name=valid_names,
        price=valid_prices,
    )
    @settings(max_examples=100)
    def test_to_dto_returns_valid_response(
        self,
        name: str,
        price: float,
    ) -> None:
        """to_dto returns valid ItemResponse with computed fields."""
        item = Item(name=name, price=price, tax=1.0)
        mapper = ItemMapper()

        dto = mapper.to_dto(item)

        assert isinstance(dto, ItemResponse)
        assert dto.name == name
        assert dto.price == price
        assert dto.price_with_tax == price + 1.0

    def test_mapper_handles_none_tax(self) -> None:
        """Mapper handles None tax correctly."""
        item = Item(name="Test", price=10.0, tax=None)
        mapper = ItemMapper()

        dto = mapper.to_dto(item)

        assert dto.tax is None
        assert dto.price_with_tax == 10.0


class TestModuleExportCompleteness:
    """Property 2: Module Export Completeness.

    For any public class in the application layer, it should be
    accessible via the module's __all__ export.
    """

    def test_application_module_exports_mapper(self) -> None:
        """Application module exports ItemMapper."""
        from my_app import application

        assert hasattr(application, "__all__")
        assert "ItemMapper" in application.__all__
        assert hasattr(application, "ItemMapper")

    def test_application_module_exports_use_case(self) -> None:
        """Application module exports ItemUseCase."""
        from my_app import application

        assert hasattr(application, "__all__")
        assert "ItemUseCase" in application.__all__
        assert hasattr(application, "ItemUseCase")

    def test_mappers_submodule_exports(self) -> None:
        """Mappers submodule has proper exports."""
        from my_app.application import mappers

        assert hasattr(mappers, "__all__")
        assert "ItemMapper" in mappers.__all__

    def test_use_cases_submodule_exports(self) -> None:
        """Use cases submodule has proper exports."""
        from my_app.application import use_cases

        assert hasattr(use_cases, "__all__")
        assert "ItemUseCase" in use_cases.__all__

    def test_dtos_submodule_exports(self) -> None:
        """DTOs submodule has proper exports."""
        from my_app.application import dtos

        assert hasattr(dtos, "__all__")


class TestMapperErrorHandling:
    """Test mapper error handling."""

    def test_mapper_logs_on_success(self, caplog: pytest.LogCaptureFixture) -> None:
        """Mapper logs debug message on successful conversion."""
        import logging

        caplog.set_level(logging.DEBUG)

        item = Item(name="Test", price=10.0)
        mapper = ItemMapper()

        mapper.to_dto(item)

        assert "Mapping entity to DTO" in caplog.text
