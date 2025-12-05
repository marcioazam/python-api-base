"""User mapper implementation for Domain-DTO conversion.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 3.5**
**Fix: F-04 - Password hash validation awareness**
"""

import logging

from application.common.mappers import IMapper
from application.users.dtos import UserDTO, UserListDTO
from domain.users.aggregates import UserAggregate

logger = logging.getLogger(__name__)


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

    def to_entity(
        self,
        dto: UserDTO,
        *,
        password_hash: str | None = None,
    ) -> UserAggregate:
        """Convert UserDTO to UserAggregate.

        WARNING: This method is for reconstitution from persistence only.
        For new user creation, use UserAggregate.create() directly.

        **Feature: application-layer-code-review-fixes**
        **Validates: Requirements F-04**

        Args:
            dto: UserDTO to convert.
            password_hash: Optional password hash for migration scenarios.
                If None, creates aggregate without password (reconstitution mode).

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

        if password_hash is None:
            logger.debug(
                "Creating UserAggregate without password_hash (reconstitution mode)",
                extra={"user_id": dto.id, "operation": "USER_RECONSTITUTION"},
            )

        return UserAggregate(
            id=dto.id,
            email=dto.email,
            password_hash=password_hash or "",
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
