"""User mapper implementation for Domain-DTO conversion.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 3.5**
"""

from application.common.base.mapper import IMapper
from application.users.commands.dtos import UserDTO, UserListDTO
from domain.users.aggregates import UserAggregate


class UserMapper(IMapper[UserAggregate, UserDTO]):
    """Mapper for UserAggregate to UserDTO conversion.

    Provides bidirectional mapping between domain aggregates
    and application DTOs.
    """

    def to_dto(self, aggregate: UserAggregate) -> UserDTO:
        """Convert UserAggregate to UserDTO.

        Args:
            aggregate: User aggregate to convert.

        Returns:
            UserDTO with all aggregate fields mapped.

        Raises:
            ValueError: If aggregate is None.
            TypeError: If aggregate is not a UserAggregate.
        """
        if aggregate is None:
            raise ValueError("aggregate parameter cannot be None")
        if not isinstance(aggregate, UserAggregate):
            raise TypeError(
                f"Expected UserAggregate instance, got {type(aggregate).__name__}"
            )

        return UserDTO(
            id=str(aggregate.id),
            email=aggregate.email,
            username=aggregate.username,
            display_name=aggregate.display_name,
            is_active=aggregate.is_active,
            is_verified=aggregate.is_verified,
            created_at=aggregate.created_at,
            updated_at=aggregate.updated_at,
            last_login_at=aggregate.last_login_at,
        )

    def to_entity(self, dto: UserDTO) -> UserAggregate:
        """Convert UserDTO to UserAggregate.

        Note: This creates a new aggregate without domain events.
        Use for reconstitution from persistence, not for new users.

        Args:
            dto: UserDTO to convert.

        Returns:
            UserAggregate with all DTO fields mapped.

        Raises:
            ValueError: If dto is None.
            TypeError: If dto is not a UserDTO.
        """
        if dto is None:
            raise ValueError("dto parameter cannot be None")
        if not isinstance(dto, UserDTO):
            raise TypeError(f"Expected UserDTO instance, got {type(dto).__name__}")

        return UserAggregate(
            id=dto.id,
            email=dto.email,
            password_hash="",  # Not stored in DTO for security
            username=dto.username,
            display_name=dto.display_name,
            is_active=dto.is_active,
            is_verified=dto.is_verified,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            last_login_at=dto.last_login_at,
        )

    def to_list_dto(self, aggregate: UserAggregate) -> UserListDTO:
        """Convert UserAggregate to UserListDTO (summary view).

        Args:
            aggregate: User aggregate to convert.

        Returns:
            UserListDTO with summary fields.
        """
        if aggregate is None:
            raise ValueError("aggregate parameter cannot be None")

        return UserListDTO(
            id=str(aggregate.id),
            email=aggregate.email,
            username=aggregate.username,
            display_name=aggregate.display_name,
            is_active=aggregate.is_active,
            created_at=aggregate.created_at,
        )
