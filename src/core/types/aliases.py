"""PEP 695 Type Aliases for common patterns.

**Feature: python-api-base-2025-validation**
**Validates: Requirements 24.1, 24.2, 24.3, 24.4, 24.5**

Provides reusable type aliases using PEP 695 `type` statement (Python 3.12+):
- AsyncResult[T, E]: Async operation returning Result
- Handler[TInput, TOutput]: Async handler function
- Validator[T]: Validation function returning Result
- Filter[T]: Predicate function
"""

from collections.abc import Awaitable, Callable, Coroutine
from typing import Any

from core.base.patterns.result import Result


# =============================================================================
# AsyncResult Type Alias
# **Feature: python-api-base-2025-validation**
# **Validates: Requirements 24.1, 24.5**
# =============================================================================

type AsyncResult[T, E] = Coroutine[Any, Any, Result[T, E]]
"""Async operation that returns a Result.

Example:
    >>> async def fetch_user(id: str) -> Result[User, UserError]:
    ...     ...
    >>> result: AsyncResult[User, UserError] = fetch_user("123")
"""


# =============================================================================
# Handler Type Aliases
# **Feature: python-api-base-2025-validation**
# **Validates: Requirements 24.2, 24.5**
# =============================================================================

type Handler[TInput, TOutput] = Callable[[TInput], Awaitable[Result[TOutput, Exception]]]
"""Async handler function that processes input and returns Result.

Example:
    >>> async def handle_command(cmd: CreateUserCommand) -> Result[User, Exception]:
    ...     ...
    >>> handler: Handler[CreateUserCommand, User] = handle_command
"""

type SyncHandler[TInput, TOutput] = Callable[[TInput], Result[TOutput, Exception]]
"""Sync handler function that processes input and returns Result.

Example:
    >>> def validate_input(data: InputDTO) -> Result[InputDTO, Exception]:
    ...     ...
    >>> handler: SyncHandler[InputDTO, InputDTO] = validate_input
"""

type AsyncHandler[TInput, TOutput, TError] = Callable[[TInput], Awaitable[Result[TOutput, TError]]]
"""Async handler with custom error type.

Example:
    >>> async def process(req: Request) -> Result[Response, AppError]:
    ...     ...
    >>> handler: AsyncHandler[Request, Response, AppError] = process
"""


# =============================================================================
# Validator Type Aliases
# **Feature: python-api-base-2025-validation**
# **Validates: Requirements 24.3, 24.5**
# =============================================================================

type Validator[T] = Callable[[T], Result[T, Exception]]
"""Sync validation function that returns the validated value or error.

Example:
    >>> def validate_email(email: str) -> Result[str, Exception]:
    ...     if "@" not in email:
    ...         return Err(ValueError("Invalid email"))
    ...     return Ok(email)
    >>> validator: Validator[str] = validate_email
"""

type AsyncValidator[T] = Callable[[T], Awaitable[Result[T, Exception]]]
"""Async validation function that returns the validated value or error.

Example:
    >>> async def validate_unique_email(email: str) -> Result[str, Exception]:
    ...     exists = await check_email_exists(email)
    ...     if exists:
    ...         return Err(ValueError("Email already exists"))
    ...     return Ok(email)
    >>> validator: AsyncValidator[str] = validate_unique_email
"""

type ValidatorWithError[T, E] = Callable[[T], Result[T, E]]
"""Validator with custom error type.

Example:
    >>> def validate_age(age: int) -> Result[int, ValidationError]:
    ...     if age < 0:
    ...         return Err(ValidationError("Age must be positive"))
    ...     return Ok(age)
    >>> validator: ValidatorWithError[int, ValidationError] = validate_age
"""


# =============================================================================
# Filter/Predicate Type Aliases
# **Feature: python-api-base-2025-validation**
# **Validates: Requirements 24.4, 24.5**
# =============================================================================

type Filter[T] = Callable[[T], bool]
"""Sync predicate function that returns True/False.

Example:
    >>> def is_active(user: User) -> bool:
    ...     return user.status == "active"
    >>> filter_fn: Filter[User] = is_active
"""

type AsyncFilter[T] = Callable[[T], Awaitable[bool]]
"""Async predicate function that returns True/False.

Example:
    >>> async def has_permission(user: User) -> bool:
    ...     return await check_permissions(user.id)
    >>> filter_fn: AsyncFilter[User] = has_permission
"""

type Predicate[T] = Filter[T]
"""Alias for Filter - predicate function.

Example:
    >>> predicate: Predicate[int] = lambda x: x > 0
"""


# =============================================================================
# Additional Utility Type Aliases
# =============================================================================

type Mapper[TSource, TTarget] = Callable[[TSource], TTarget]
"""Sync mapping function from source to target type.

Example:
    >>> def user_to_dto(user: User) -> UserDTO:
    ...     return UserDTO(id=user.id, name=user.name)
    >>> mapper: Mapper[User, UserDTO] = user_to_dto
"""

type AsyncMapper[TSource, TTarget] = Callable[[TSource], Awaitable[TTarget]]
"""Async mapping function from source to target type."""

type Factory[T] = Callable[[], T]
"""Factory function that creates instances of T.

Example:
    >>> def create_connection() -> Connection:
    ...     return Connection(host="localhost")
    >>> factory: Factory[Connection] = create_connection
"""

type AsyncFactory[T] = Callable[[], Awaitable[T]]
"""Async factory function that creates instances of T."""

type Callback[T] = Callable[[T], None]
"""Callback function that receives a value and returns nothing.

Example:
    >>> def on_user_created(user: User) -> None:
    ...     print(f"User {user.name} created")
    >>> callback: Callback[User] = on_user_created
"""

type AsyncCallback[T] = Callable[[T], Awaitable[None]]
"""Async callback function."""


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # AsyncResult
    "AsyncResult",
    # Handlers
    "Handler",
    "SyncHandler",
    "AsyncHandler",
    # Validators
    "Validator",
    "AsyncValidator",
    "ValidatorWithError",
    # Filters
    "Filter",
    "AsyncFilter",
    "Predicate",
    # Utilities
    "Mapper",
    "AsyncMapper",
    "Factory",
    "AsyncFactory",
    "Callback",
    "AsyncCallback",
]
