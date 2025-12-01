"""Property-based tests for mapper interface.

**Feature: generic-fastapi-crud, Property 4: Mapper Round-Trip Preservation**
**Feature: generic-fastapi-crud, Property 5: Mapper Error Descriptiveness**
**Validates: Requirements 2.1, 2.3, 2.4, 2.6**
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import BaseModel

from my_app.application.common.mapper import AutoMapper, BaseMapper, MapperError


# Test models
class EntityModel(BaseModel):
    """Entity model for testing."""

    id: int
    name: str
    value: float
    description: str | None = None


class DTOModel(BaseModel):
    """DTO model for testing."""

    id: int
    name: str
    value: float
    description: str | None = None


class NestedEntity(BaseModel):
    """Entity with nested object."""

    id: int
    name: str
    child: EntityModel | None = None


class NestedDTO(BaseModel):
    """DTO with nested object."""

    id: int
    name: str
    child: dict | None = None


class RequiredFieldDTO(BaseModel):
    """DTO with required field not in entity."""

    id: int
    name: str
    required_field: str


# Strategies
entity_strategy = st.builds(
    EntityModel,
    id=st.integers(min_value=1, max_value=10000),
    name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
    value=st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False),
    description=st.text(min_size=0, max_size=100, alphabet=st.characters(whitelist_categories=("L", "N"))) | st.none(),
)


class TestMapperRoundTrip:
    """Property tests for mapper round-trip preservation."""

    @settings(max_examples=50)
    @given(entity=entity_strategy)
    def test_auto_mapper_round_trip(self, entity: EntityModel) -> None:
        """
        **Feature: generic-fastapi-crud, Property 4: Mapper Round-Trip Preservation**

        For any entity instance, mapping to DTO and back to entity SHALL
        preserve all field values for fields with matching names.
        """
        mapper = AutoMapper(EntityModel, DTOModel)

        # Entity -> DTO -> Entity
        dto = mapper.to_dto(entity)
        restored = mapper.to_entity(dto)

        # Verify all fields preserved
        assert restored.id == entity.id
        assert restored.name == entity.name
        assert restored.value == entity.value
        assert restored.description == entity.description

    @settings(max_examples=50)
    @given(entity=entity_strategy)
    def test_base_mapper_round_trip(self, entity: EntityModel) -> None:
        """
        BaseMapper SHALL preserve field values through round-trip.
        """
        mapper = BaseMapper(EntityModel, DTOModel)

        dto = mapper.to_dto(entity)
        restored = mapper.to_entity(dto)

        assert restored.id == entity.id
        assert restored.name == entity.name
        assert restored.value == entity.value
        assert restored.description == entity.description

    @settings(max_examples=30)
    @given(
        entities=st.lists(entity_strategy, min_size=1, max_size=10),
    )
    def test_mapper_list_round_trip(self, entities: list[EntityModel]) -> None:
        """
        For collections, mapping SHALL preserve structure and values.
        """
        mapper = AutoMapper(EntityModel, DTOModel)

        dtos = mapper.to_dto_list(entities)
        restored = mapper.to_entity_list(dtos)

        assert len(restored) == len(entities)
        for original, result in zip(entities, restored, strict=True):
            assert result.id == original.id
            assert result.name == original.name

    @settings(max_examples=30)
    @given(
        id_val=st.integers(min_value=1, max_value=10000),
        name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
        child_id=st.integers(min_value=1, max_value=10000),
        child_name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
    )
    def test_nested_object_mapping(
        self, id_val: int, name: str, child_id: int, child_name: str
    ) -> None:
        """
        For nested objects, mapping SHALL recursively preserve structure.
        """
        child = EntityModel(id=child_id, name=child_name, value=0.0)
        entity = NestedEntity(id=id_val, name=name, child=child)

        mapper = BaseMapper(NestedEntity, NestedDTO)
        dto = mapper.to_dto(entity)

        # Nested object should be converted to dict
        assert dto.id == entity.id
        assert dto.name == entity.name
        assert dto.child is not None
        assert dto.child["id"] == child_id
        assert dto.child["name"] == child_name


class TestMapperErrorHandling:
    """Property tests for mapper error handling."""

    @settings(max_examples=30)
    @given(entity=entity_strategy)
    def test_missing_required_field_raises_error(self, entity: EntityModel) -> None:
        """
        **Feature: generic-fastapi-crud, Property 5: Mapper Error Descriptiveness**

        For any mapping where required target fields cannot be populated,
        the raised exception SHALL include the field name and context.
        """
        mapper = BaseMapper(EntityModel, RequiredFieldDTO)

        with pytest.raises(MapperError) as exc_info:
            mapper.to_dto(entity)

        error = exc_info.value
        # Error should mention the missing field
        assert error.field == "required_field"
        assert "required_field" in str(error)
        # Context should include type information
        assert "source_type" in error.context or "target_type" in error.context

    def test_mapper_error_contains_field_info(self) -> None:
        """
        MapperError SHALL contain field name and context.
        """
        error = MapperError(
            message="Test error",
            field="test_field",
            context={"source_type": "Entity", "target_type": "DTO"},
        )

        assert error.field == "test_field"
        assert error.context["source_type"] == "Entity"
        assert error.context["target_type"] == "DTO"
