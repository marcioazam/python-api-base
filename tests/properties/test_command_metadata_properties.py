"""Property-based tests for CQRS Command metadata.

**Feature: python-api-base-2025-validation**
**Property 22: Command Metadata Presence**
**Validates: Requirements 3.1**
"""

from dataclasses import dataclass, field
from datetime import datetime

from hypothesis import given, settings, strategies as st

from core.base.cqrs.command import BaseCommand


# Test Command implementation - data must have default to follow parent defaults
@dataclass(frozen=True)
class TestCommand(BaseCommand):
    """Test command for property testing."""

    data: str = field(default="")


# =============================================================================
# Property 22: Command Metadata Presence
# **Feature: python-api-base-2025-validation, Property 22: Command Metadata Presence**
# **Validates: Requirements 3.1**
# =============================================================================


class TestCommandMetadataPresence:
    """Property tests for command metadata automatic population.

    **Feature: python-api-base-2025-validation, Property 22: Command Metadata Presence**
    **Validates: Requirements 3.1**
    """

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_command_id_auto_generated(self, data: str) -> None:
        """
        **Feature: python-api-base-2025-validation, Property 22: Command Metadata Presence**
        **Validates: Requirements 3.1**

        *For any* BaseCommand instance, command_id SHALL be automatically
        populated with a valid string (UUID format).
        """
        command = TestCommand(data=data)

        assert command.command_id is not None
        assert isinstance(command.command_id, str)
        assert len(command.command_id) > 0

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_timestamp_auto_generated(self, data: str) -> None:
        """
        **Feature: python-api-base-2025-validation, Property 22: Command Metadata Presence**
        **Validates: Requirements 3.1**

        *For any* BaseCommand instance, timestamp SHALL be automatically
        populated with a valid datetime.
        """
        command = TestCommand(data=data)

        assert command.timestamp is not None
        assert isinstance(command.timestamp, datetime)

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_command_ids_are_unique(self, data: str) -> None:
        """
        **Feature: python-api-base-2025-validation, Property 22: Command Metadata Presence**
        **Validates: Requirements 3.1**

        *For any* two BaseCommand instances, their command_ids SHALL be different.
        """
        command1 = TestCommand(data=data)
        command2 = TestCommand(data=data)

        assert command1.command_id != command2.command_id

    @given(st.integers(min_value=2, max_value=50))
    @settings(max_examples=50)
    def test_multiple_commands_unique_ids(self, count: int) -> None:
        """
        **Feature: python-api-base-2025-validation, Property 22: Command Metadata Presence**
        **Validates: Requirements 3.1**

        *For any* N BaseCommand instances, all N command_ids SHALL be unique.
        """
        commands = [TestCommand(data=f"data_{i}") for i in range(count)]
        command_ids = [cmd.command_id for cmd in commands]

        # All IDs should be unique
        assert len(set(command_ids)) == len(command_ids)

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_optional_fields_default_to_none(self, data: str) -> None:
        """
        **Feature: python-api-base-2025-validation, Property 22: Command Metadata Presence**
        **Validates: Requirements 3.1**

        *For any* BaseCommand instance without explicit correlation_id or user_id,
        these fields SHALL default to None.
        """
        command = TestCommand(data=data)

        # Optional fields should be None by default
        assert command.correlation_id is None
        assert command.user_id is None

    def test_correlation_id_can_be_set(self) -> None:
        """
        **Feature: python-api-base-2025-validation, Property 22: Command Metadata Presence**
        **Validates: Requirements 3.1**

        correlation_id CAN be explicitly set when creating a command.
        """
        correlation = "corr-123"
        command = TestCommand(data="test", correlation_id=correlation)

        assert command.correlation_id == correlation

    def test_user_id_can_be_set(self) -> None:
        """
        **Feature: python-api-base-2025-validation, Property 22: Command Metadata Presence**
        **Validates: Requirements 3.1**

        user_id CAN be explicitly set when creating a command.
        """
        user = "user-123"
        command = TestCommand(data="test", user_id=user)

        assert command.user_id == user
