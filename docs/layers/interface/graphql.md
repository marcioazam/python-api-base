# GraphQL

## Overview

GraphQL é implementado com Strawberry, oferecendo uma alternativa ao REST para queries complexas.

## Schema Definition

```python
import strawberry
from strawberry.fastapi import GraphQLRouter

@strawberry.type
class User:
    id: str
    email: str
    name: str
    is_active: bool
    created_at: datetime

@strawberry.type
class Query:
    @strawberry.field
    async def user(self, id: str, info: Info) -> User | None:
        query_bus = info.context["query_bus"]
        result = await query_bus.dispatch(GetUserQuery(user_id=id))
        return User(**result.model_dump()) if result else None
    
    @strawberry.field
    async def users(
        self,
        info: Info,
        skip: int = 0,
        limit: int = 20,
    ) -> list[User]:
        query_bus = info.context["query_bus"]
        result = await query_bus.dispatch(ListUsersQuery(skip=skip, limit=limit))
        return [User(**u.model_dump()) for u in result.items]

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_user(
        self,
        info: Info,
        email: str,
        name: str,
        password: str,
    ) -> User:
        command_bus = info.context["command_bus"]
        result = await command_bus.dispatch(CreateUserCommand(
            email=email,
            name=name,
            password=password,
        ))
        if result.is_err():
            raise Exception(result.error)
        return User(**result.value.model_dump())

schema = strawberry.Schema(query=Query, mutation=Mutation)
```

## FastAPI Integration

```python
from strawberry.fastapi import GraphQLRouter

async def get_context(
    query_bus: QueryBus = Depends(get_query_bus),
    command_bus: CommandBus = Depends(get_command_bus),
):
    return {
        "query_bus": query_bus,
        "command_bus": command_bus,
    }

graphql_router = GraphQLRouter(
    schema,
    context_getter=get_context,
)

app.include_router(graphql_router, prefix="/graphql")
```

## Queries

```graphql
# Get single user
query GetUser($id: String!) {
  user(id: $id) {
    id
    email
    name
    isActive
  }
}

# List users with pagination
query ListUsers($skip: Int, $limit: Int) {
  users(skip: $skip, limit: $limit) {
    id
    email
    name
  }
}
```

## Mutations

```graphql
mutation CreateUser($email: String!, $name: String!, $password: String!) {
  createUser(email: $email, name: $name, password: $password) {
    id
    email
    name
  }
}
```

## DataLoaders

```python
from strawberry.dataloader import DataLoader

async def load_users(ids: list[str]) -> list[User | None]:
    users = await repository.get_many(ids)
    user_map = {u.id: u for u in users}
    return [user_map.get(id) for id in ids]

user_loader = DataLoader(load_fn=load_users)

@strawberry.type
class Order:
    customer_id: str
    
    @strawberry.field
    async def customer(self, info: Info) -> User | None:
        return await info.context["user_loader"].load(self.customer_id)
```

## Best Practices

1. **Use DataLoaders** - Prevent N+1 queries
2. **Limit query depth** - Prevent DoS
3. **Use context** - For dependency injection
4. **Handle errors** - Return proper GraphQL errors
