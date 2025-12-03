# CQRS Pattern

## Overview

CQRS (Command Query Responsibility Segregation) separa operações de leitura (Queries) e escrita (Commands), permitindo otimização independente de cada lado.

## Command (Write Operations)

```python
from dataclasses import dataclass
from result import Result, Ok, Err

@dataclass
class Command[TResult]:
    """Base class for commands."""
    
    async def execute(self, *args, **kwargs) -> TResult:
        raise NotImplementedError
```

### CreateUserCommand

```python
@dataclass
class CreateUserCommand(Command[Result[User, str]]):
    """Command to create a new user."""
    
    email: str
    name: str
    password: str
    
    async def execute(
        self,
        repository: IUserRepository,
        password_hasher: PasswordHasher,
    ) -> Result[User, str]:
        # Validation
        if await repository.exists_by_email(self.email):
            return Err("Email already exists")
        
        if len(self.password) < 8:
            return Err("Password must be at least 8 characters")
        
        # Create entity
        user = User(
            id=str(ULID()),
            email=self.email,
            name=self.name,
            password_hash=password_hasher.hash(self.password),
            created_at=datetime.utcnow(),
        )
        
        # Persist
        created = await repository.create(user)
        return Ok(created)
```

### UpdateUserCommand

```python
@dataclass
class UpdateUserCommand(Command[Result[User, str]]):
    """Command to update an existing user."""
    
    user_id: str
    name: str | None = None
    email: str | None = None
    
    async def execute(
        self,
        repository: IUserRepository,
    ) -> Result[User, str]:
        user = await repository.get(self.user_id)
        if user is None:
            return Err("User not found")
        
        if self.name:
            user.name = self.name
        if self.email:
            if await repository.exists_by_email(self.email):
                return Err("Email already exists")
            user.email = self.email
        
        user.updated_at = datetime.utcnow()
        updated = await repository.update(user)
        return Ok(updated)
```

## Query (Read Operations)

```python
@dataclass
class Query[TResult]:
    """Base class for queries."""
    
    cacheable: bool = False
    cache_ttl: int = 300
    
    async def execute(self, *args, **kwargs) -> TResult:
        raise NotImplementedError
```

### GetUserQuery

```python
@dataclass
class GetUserQuery(Query[UserDTO | None]):
    """Query to get a user by ID."""
    
    user_id: str
    cacheable: bool = True
    cache_ttl: int = 300
    
    async def execute(
        self,
        repository: IUserRepository,
    ) -> UserDTO | None:
        user = await repository.get(self.user_id)
        if user is None:
            return None
        return UserMapper.to_dto(user)
```

### ListUsersQuery

```python
@dataclass
class ListUsersQuery(Query[list[UserDTO]]):
    """Query to list users with pagination."""
    
    skip: int = 0
    limit: int = 20
    filter_active: bool = True
    search: str | None = None
    
    async def execute(
        self,
        repository: IUserRepository,
    ) -> list[UserDTO]:
        spec = equals("is_active", True) if self.filter_active else None
        
        if self.search:
            search_spec = contains("name", self.search).or_spec(
                contains("email", self.search)
            )
            spec = spec.and_spec(search_spec) if spec else search_spec
        
        users = await repository.find_by_spec(
            spec=spec,
            skip=self.skip,
            limit=self.limit,
        )
        return [UserMapper.to_dto(u) for u in users]
```

## Command/Query Bus

```python
class CommandBus:
    """Dispatches commands to handlers."""
    
    def __init__(self):
        self._handlers: dict[type, CommandHandler] = {}
    
    def register(self, command_type: type, handler: CommandHandler) -> None:
        self._handlers[command_type] = handler
    
    async def dispatch[T](self, command: Command[T]) -> T:
        handler = self._handlers.get(type(command))
        if handler is None:
            raise ValueError(f"No handler for {type(command)}")
        return await handler.handle(command)

class QueryBus:
    """Dispatches queries to handlers with caching."""
    
    def __init__(self, cache: CacheProvider | None = None):
        self._handlers: dict[type, QueryHandler] = {}
        self._cache = cache
    
    async def dispatch[T](self, query: Query[T]) -> T:
        # Check cache
        if query.cacheable and self._cache:
            cache_key = self._build_cache_key(query)
            cached = await self._cache.get(cache_key)
            if cached is not None:
                return cached
        
        # Execute query
        handler = self._handlers.get(type(query))
        if handler is None:
            raise ValueError(f"No handler for {type(query)}")
        
        result = await handler.handle(query)
        
        # Store in cache
        if query.cacheable and self._cache:
            await self._cache.set(cache_key, result, ttl=query.cache_ttl)
        
        return result
```

## Handler Pattern

```python
class CommandHandler[TCommand, TResult]:
    """Base command handler."""
    
    async def handle(self, command: TCommand) -> TResult:
        raise NotImplementedError

class CreateUserHandler(CommandHandler[CreateUserCommand, Result[User, str]]):
    def __init__(
        self,
        repository: IUserRepository,
        password_hasher: PasswordHasher,
    ):
        self._repository = repository
        self._hasher = password_hasher
    
    async def handle(self, command: CreateUserCommand) -> Result[User, str]:
        return await command.execute(self._repository, self._hasher)
```

## Middleware Pipeline

```python
class CommandMiddleware:
    """Middleware for command processing."""
    
    async def __call__(
        self,
        command: Command,
        next_handler: Callable,
    ) -> Any:
        raise NotImplementedError

class LoggingMiddleware(CommandMiddleware):
    async def __call__(self, command: Command, next_handler: Callable) -> Any:
        logger.info("executing_command", command_type=type(command).__name__)
        try:
            result = await next_handler(command)
            logger.info("command_succeeded")
            return result
        except Exception as e:
            logger.error("command_failed", error=str(e))
            raise

class ValidationMiddleware(CommandMiddleware):
    async def __call__(self, command: Command, next_handler: Callable) -> Any:
        if hasattr(command, "validate"):
            command.validate()
        return await next_handler(command)
```

## Usage in Router

```python
@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    data: CreateUserRequest,
    command_bus: CommandBus = Depends(get_command_bus),
) -> UserResponse:
    command = CreateUserCommand(
        email=data.email,
        name=data.name,
        password=data.password,
    )
    result = await command_bus.dispatch(command)
    
    if result.is_err():
        raise HTTPException(400, detail=result.error)
    
    return UserResponse.from_entity(result.value)
```
