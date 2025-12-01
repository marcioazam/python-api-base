"""Property-based tests for Domain-DTO mapper round-trip.

**Feature: architecture-restructuring-2025, Property 6: Domain-DTO Mapper Round-Trip**
**Validates: Requirements 3.5**
"""

from datetime import datetime, UTC, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

try:
    from my_app.application.users.mappers import UserMapper
    from my_app.application.users.dto import UserDTO
    from my_app.domain.users.aggregates import UserAggregate
except ImportError:
    pytest.skip("my_app modules not available", allow_module_level=True)


# Strategies for generating test data
email_strategy = st.emails()
username_strategy = st.text(min_size=3, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_")
display_name_strategy = st.text(min_size=1, max_size=100, alphabet="abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ")
user_id_strategy = st.text(min_size=10, max_size=26, alphabet="0123456789ABCDEFGHJKMNPQRSTVWXYZ")
datetime_strategy = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 12, 31),
    timezones=st.just(UTC),
)


class TestUserMapperRoundTrip:
    """Property tests for UserMapper round-trip conversion."""

    @settings(max_examples=20)
    @given(
        user_id=user_id_strategy,
        email=email_strategy,
        username=username_strategy,
        display_name=display_name_strategy,
        is_active=st.booleans(),
        is_verified=st.booleans(),
        created_at=datetime_strategy,
        updated_at=datetime_strategy,
    )
    def test_aggregate_to_dto_preserves_data(
        self,
        user_id: str,
        email: str,
        username: str,
        display_name: str,
        is_active: bool,
        is_verified: bool,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        """
        **Feature: architecture-restructuring-2025, Property 6: Domain-DTO Mapper Round-Trip**
        
        For any UserAggregate, converting to DTO SHALL preserve all
        public fields that are part of the DTO contract.
        **Validates: Requirements 3.5**
        """
        aggregate = UserAggregate(
            id=user_id,
            email=email,
            password_hash="hashed_password_123",
            username=username,
            display_name=display_name,
            is_active=is_active,
            is_verified=is_verified,
            created_at=created_at,
            updated_at=updated_at,
        )
        
        mapper = UserMapper()
        dto = mapper.to_dto(aggregate)
        
        # Verify all fields are preserved
        assert dto.id == user_id
        assert dto.email == email
        assert dto.username == username
        assert dto.display_name == display_name
        assert dto.is_active == is_active
        assert dto.is_verified == is_verified
        assert dto.created_at == created_at
        assert dto.updated_at == updated_at

    @settings(max_examples=20)
    @given(
        user_id=user_id_strategy,
        email=email_strategy,
        username=username_strategy,
        display_name=display_name_strategy,
        is_active=st.booleans(),
        is_verified=st.booleans(),
        created_at=datetime_strategy,
        updated_at=datetime_strategy,
    )
    def test_dto_to_aggregate_preserves_data(
        self,
        user_id: str,
        email: str,
        username: str,
        display_name: str,
        is_active: bool,
        is_verified: bool,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        """
        For any UserDTO, converting to aggregate SHALL preserve all
        fields that are part of the aggregate.
        **Validates: Requirements 3.5**
        """
        dto = UserDTO(
            id=user_id,
            email=email,
            username=username,
            display_name=display_name,
            is_active=is_active,
            is_verified=is_verified,
            created_at=created_at,
            updated_at=updated_at,
        )
        
        mapper = UserMapper()
        aggregate = mapper.to_entity(dto)
        
        # Verify all fields are preserved (except password_hash)
        assert aggregate.id == user_id
        assert aggregate.email == email
        assert aggregate.username == username
        assert aggregate.display_name == display_name
        assert aggregate.is_active == is_active
        assert aggregate.is_verified == is_verified
        assert aggregate.created_at == created_at
        assert aggregate.updated_at == updated_at

    @settings(max_examples=20)
    @given(
        user_id=user_id_strategy,
        email=email_strategy,
        username=username_strategy,
        display_name=display_name_strategy,
        is_active=st.booleans(),
        is_verified=st.booleans(),
        created_at=datetime_strategy,
        updated_at=datetime_strategy,
    )
    def test_round_trip_aggregate_dto_aggregate(
        self,
        user_id: str,
        email: str,
        username: str,
        display_name: str,
        is_active: bool,
        is_verified: bool,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        """
        For any UserAggregate, converting to DTO and back SHALL produce
        an equivalent aggregate (excluding password_hash which is not in DTO).
        **Validates: Requirements 3.5**
        """
        original = UserAggregate(
            id=user_id,
            email=email,
            password_hash="hashed_password_123",
            username=username,
            display_name=display_name,
            is_active=is_active,
            is_verified=is_verified,
            created_at=created_at,
            updated_at=updated_at,
        )
        
        mapper = UserMapper()
        dto = mapper.to_dto(original)
        restored = mapper.to_entity(dto)
        
        # Verify round-trip preserves all DTO-visible fields
        assert restored.id == original.id
        assert restored.email == original.email
        assert restored.username == original.username
        assert restored.display_name == original.display_name
        assert restored.is_active == original.is_active
        assert restored.is_verified == original.is_verified
        assert restored.created_at == original.created_at
        assert restored.updated_at == original.updated_at

    def test_none_aggregate_raises_value_error(self) -> None:
        """
        For None aggregate input, to_dto SHALL raise ValueError.
        **Validates: Requirements 3.5**
        """
        mapper = UserMapper()
        
        with pytest.raises(ValueError, match="cannot be None"):
            mapper.to_dto(None)

    def test_none_dto_raises_value_error(self) -> None:
        """
        For None DTO input, to_entity SHALL raise ValueError.
        **Validates: Requirements 3.5**
        """
        mapper = UserMapper()
        
        with pytest.raises(ValueError, match="cannot be None"):
            mapper.to_entity(None)

    def test_wrong_type_aggregate_raises_type_error(self) -> None:
        """
        For wrong type aggregate input, to_dto SHALL raise TypeError.
        **Validates: Requirements 3.5**
        """
        mapper = UserMapper()
        
        with pytest.raises(TypeError, match="Expected UserAggregate"):
            mapper.to_dto("not an aggregate")

    def test_wrong_type_dto_raises_type_error(self) -> None:
        """
        For wrong type DTO input, to_entity SHALL raise TypeError.
        **Validates: Requirements 3.5**
        """
        mapper = UserMapper()
        
        with pytest.raises(TypeError, match="Expected UserDTO"):
            mapper.to_entity("not a dto")
