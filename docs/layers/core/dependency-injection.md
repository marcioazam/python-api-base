# Dependency Injection

## Overview

O sistema utiliza `dependency-injector` para Inversion of Control (IoC), permitindo injeção de dependências configurável e testável.

## Container Definition

```python
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    """Application DI container."""
    
    # Configuration
    config = providers.Configuration()
    
    # Database
    db_engine = providers.Singleton(
        create_async_engine,
        url=config.database.url,
        pool_size=config.database.pool_size,
    )
    
    db_session_factory = providers.Factory(
        async_sessionmaker,
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Repositories
    user_repository = providers.Factory(
        UserRepository,
        session_factory=db_session_factory,
    )
    
    item_repository = providers.Factory(
        ItemRepository,
        session_factory=db_session_factory,
    )
    
    # Services
    user_service = providers.Factory(
        UserService,
        repository=user_repository,
    )
    
    # Cache
    cache_provider = providers.Singleton(
        RedisCacheProvider,
        url=config.redis.url,
    )
```

## Provider Types

### Singleton
Single instance shared across application:

```python
db_engine = providers.Singleton(
    create_async_engine,
    url=config.database.url,
)
```

### Factory
New instance on each call:

```python
user_repository = providers.Factory(
    UserRepository,
    session_factory=db_session_factory,
)
```

### Resource
Managed lifecycle with cleanup:

```python
redis_client = providers.Resource(
    init_redis_client,
    url=config.redis.url,
)
```

## FastAPI Integration

```python
from fastapi import Depends
from dependency_injector.wiring import inject, Provide

@router.get("/users/{user_id}")
@inject
async def get_user(
    user_id: str,
    service: UserService = Depends(Provide[Container.user_service]),
) -> UserResponse:
    user = await service.get(user_id)
    return UserResponse.from_entity(user)
```

## Wiring

```python
# main.py
container = Container()
container.config.from_pydantic(get_settings())
container.wire(modules=[
    "interface.v1.users",
    "interface.v1.items",
    "interface.v1.auth",
])
```

## Testing with Overrides

```python
@pytest.fixture
def container():
    container = Container()
    container.config.from_dict({
        "database": {"url": "sqlite+aiosqlite:///:memory:"},
    })
    return container

@pytest.fixture
def mock_user_repository():
    return AsyncMock(spec=IUserRepository)

async def test_get_user(container, mock_user_repository):
    # Override repository with mock
    with container.user_repository.override(mock_user_repository):
        mock_user_repository.get.return_value = User(id="123", name="Test")
        
        service = container.user_service()
        user = await service.get("123")
        
        assert user.name == "Test"
```

## Best Practices

1. **Define interfaces (protocols) in domain layer**
2. **Implement in infrastructure layer**
3. **Wire in interface layer**
4. **Override in tests**

```
Domain: IUserRepository (Protocol)
    ↓
Infrastructure: UserRepository (Implementation)
    ↓
Core: Container (Wiring)
    ↓
Interface: Depends(Provide[...]) (Injection)
```
