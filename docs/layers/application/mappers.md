# Mappers

## Overview

Mappers transform data between domain entities and DTOs, maintaining separation of concerns.

## Mapper Pattern

```python
class UserMapper:
    """Maps between User entity and DTOs."""
    
    @staticmethod
    def to_response(user: User) -> UserResponseDTO:
        """Map entity to response DTO."""
        return UserResponseDTO(
            id=str(user.id),
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            created_at=user.created_at,
        )
    
    @staticmethod
    def to_entity(dto: UserCreateDTO) -> User:
        """Map create DTO to entity."""
        return User(
            email=dto.email,
            name=dto.name,
            password_hash=hash_password(dto.password),
        )
    
    @staticmethod
    def to_response_list(users: list[User]) -> list[UserResponseDTO]:
        """Map list of entities to response DTOs."""
        return [UserMapper.to_response(u) for u in users]
```

## Usage

```python
class GetUserUseCase:
    async def execute(self, user_id: str) -> UserResponseDTO | None:
        user = await self.repository.get(user_id)
        if not user:
            return None
        return UserMapper.to_response(user)
```

## Best Practices

1. **Keep mappers stateless**
2. **Use static methods**
3. **Handle None values**
4. **Map collections efficiently**

## Related

- [DTOs](dtos.md)
- [CQRS](cqrs.md)
