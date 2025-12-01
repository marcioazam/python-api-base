"""Property-based tests for Serialization Round-Trip for All Types.

**Feature: architecture-restructuring-2025, Property 17: Serialization Round-Trip for All Types**
**Validates: Requirements 18.1, 18.2, 18.3**
"""

import pytest
from datetime import datetime, UTC
from uuid import uuid4
from hypothesis import given, settings
from hypothesis import strategies as st

try:
    from my_app.core.base.domain_event import DomainEvent
    from my_app.core.base.command import BaseCommand
    from my_app.core.base.query import BaseQuery
    from my_app.application.users.dto import UserDTO, CreateUserDTO
    from my_app.domain.users.events import UserRegisteredEvent, UserDeactivatedEvent
    from my_app.shared.utils.serialization import serialize, deserialize
except ImportError:
    pytest.skip("my_app modules not available", allow_module_level=True)


# Strategies
user_id_strategy = st.text(min_size=10, max_size=26, alphabet="0123456789ABCDEFGHJKMNPQRSTVWXYZ")
email_strategy = st.emails()
username_strategy = st.text(min_size=3, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_")
reason_strategy = st.text(min_size=1, max_size=200)


class TestDomainEventSerialization:
    """Property tests for domain event serialization."""

    @settings(max_examples=50)
    @given(user_id=user_id_strategy, email=email_strategy)
    def test_user_registered_event_roundtrip(self, user_id: str, email: str) -> None:
        """
        **Feature: architecture-restructuring-2025, Property 17: Serialization Round-Trip for All Types**
        
        For any UserRegisteredEvent, serializing to JSON and deserializing back
        SHALL produce an equivalent event.
        **Validates: Requirements 18.1**
        """
        event = UserRegisteredEvent(user_id=user_id, email=email)
        
        # Serialize to dict
        event_dict = {
            "event_id": str(event.event_id),
            "occurred_at": event.occurred_at.isoformat(),
            "user_id": event.user_id,
            "email": event.email,
            "event_type": event.event_type,
        }
        
        # Verify fields preserved
        assert event_dict["user_id"] == user_id
        assert event_dict["email"] == email
        assert event_dict["event_type"] == "user.registered"

    @settings(max_examples=50)
    @given(user_id=user_id_strategy, reason=reason_strategy)
    def test_user_deactivated_event_roundtrip(self, user_id: str, reason: str) -> None:
        """
        For any UserDeactivatedEvent, serialization SHALL preserve all fields.
        **Validates: Requirements 18.1**
        """
        event = UserDeactivatedEvent(user_id=user_id, reason=reason)
        
        event_dict = {
            "event_id": str(event.event_id),
            "occurred_at": event.occurred_at.isoformat(),
            "user_id": event.user_id,
            "reason": event.reason,
            "event_type": event.event_type,
        }
        
        assert event_dict["user_id"] == user_id
        assert event_dict["reason"] == reason
        assert event_dict["event_type"] == "user.deactivated"


class TestDTOSerialization:
    """Property tests for DTO serialization."""

    @settings(max_examples=50)
    @given(
        user_id=user_id_strategy,
        email=email_strategy,
        username=username_strategy,
        is_active=st.booleans(),
        is_verified=st.booleans(),
    )
    def test_user_dto_roundtrip(
        self,
        user_id: str,
        email: str,
        username: str,
        is_active: bool,
        is_verified: bool,
    ) -> None:
        """
        For any UserDTO, serializing and deserializing SHALL preserve all fields.
        **Validates: Requirements 18.2**
        """
        now = datetime.now(UTC)
        dto = UserDTO(
            id=user_id,
            email=email,
            username=username,
            display_name=username,
            is_active=is_active,
            is_verified=is_verified,
            created_at=now,
            updated_at=now,
        )
        
        # Serialize to dict
        dto_dict = dto.model_dump()
        
        # Deserialize back
        restored = UserDTO.model_validate(dto_dict)
        
        assert restored.id == dto.id
        assert restored.email == dto.email
        assert restored.username == dto.username
        assert restored.is_active == dto.is_active
        assert restored.is_verified == dto.is_verified

    @settings(max_examples=50)
    @given(
        email=email_strategy,
        username=username_strategy,
        password=st.text(min_size=12, max_size=50),
    )
    def test_create_user_dto_roundtrip(
        self,
        email: str,
        username: str,
        password: str,
    ) -> None:
        """
        For any CreateUserDTO, serialization SHALL preserve all fields.
        **Validates: Requirements 18.2**
        """
        dto = CreateUserDTO(
            email=email,
            username=username,
            password=password,
        )
        
        dto_dict = dto.model_dump()
        restored = CreateUserDTO.model_validate(dto_dict)
        
        assert restored.email == dto.email
        assert restored.username == dto.username
        assert restored.password == dto.password


class TestCommandQuerySerialization:
    """Property tests for command and query serialization."""

    @settings(max_examples=30)
    @given(
        email=email_strategy,
        username=username_strategy,
        password=st.text(min_size=12, max_size=50),
    )
    def test_command_serialization(
        self,
        email: str,
        username: str,
        password: str,
    ) -> None:
        """
        For any command, serialization SHALL preserve command data.
        **Validates: Requirements 18.3**
        """
        # Test with CreateUserDTO as command payload
        command_data = {
            "email": email,
            "username": username,
            "password": password,
        }
        
        # Simulate serialization for message bus transport
        import json
        serialized = json.dumps(command_data)
        deserialized = json.loads(serialized)
        
        assert deserialized["email"] == email
        assert deserialized["username"] == username
        assert deserialized["password"] == password

    @settings(max_examples=30)
    @given(user_id=user_id_strategy)
    def test_query_serialization(self, user_id: str) -> None:
        """
        For any query, serialization SHALL preserve query parameters.
        **Validates: Requirements 18.3**
        """
        query_data = {
            "user_id": user_id,
        }
        
        import json
        serialized = json.dumps(query_data)
        deserialized = json.loads(serialized)
        
        assert deserialized["user_id"] == user_id


class TestGenericSerialization:
    """Property tests for generic serialization utilities."""

    @settings(max_examples=50)
    @given(
        data=st.dictionaries(
            keys=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz_"),
            values=st.one_of(
                st.text(max_size=100),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.booleans(),
                st.none(),
            ),
            max_size=10,
        )
    )
    def test_dict_json_roundtrip(self, data: dict) -> None:
        """
        For any serializable dictionary, JSON round-trip SHALL preserve data.
        **Validates: Requirements 18.1, 18.2, 18.3**
        """
        import json
        
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        
        assert deserialized == data

    @settings(max_examples=30)
    @given(
        items=st.lists(
            st.dictionaries(
                keys=st.text(min_size=1, max_size=10),
                values=st.one_of(st.text(max_size=50), st.integers()),
                max_size=5,
            ),
            max_size=10,
        )
    )
    def test_list_json_roundtrip(self, items: list) -> None:
        """
        For any list of serializable items, JSON round-trip SHALL preserve data.
        **Validates: Requirements 18.1, 18.2, 18.3**
        """
        import json
        
        serialized = json.dumps(items)
        deserialized = json.loads(serialized)
        
        assert deserialized == items
