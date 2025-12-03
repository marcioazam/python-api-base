# ADR-002: DTO vs Mapper Strategy

**Status:** Accepted

**Date:** 2025-01-02

**Deciders:** Architecture Team

**Technical Story:** Query responses return `dict[str, Any]` which are manually converted to DTOs in the interface layer, rather than using automatic GenericMapper.

---

## Context

In the application layer, we have two approaches for converting between domain entities/aggregates and DTOs:

1. **Generic Mapper** (`application.common.base.mapper.GenericMapper`):
   - Automatic field mapping based on matching names
   - Supports nested objects and collections
   - Configured field mapping and exclusions
   - Less boilerplate code

2. **Manual DTO Conversion**:
   - Explicit conversion code in each layer
   - Type-safe at every step
   - Clear data shaping and transformation
   - More boilerplate but more control

Currently, the project uses **Manual DTO Conversion** for query responses:

```python
# Query handler returns dict[str, Any]
user_data = user_aggregate.model_dump()
return Ok(user_data)

# Router converts dict to DTO
return UserDTO(
    id=user_data["id"],
    email=user_data["email"],
    username=user_data.get("username"),
    # ...
)
```

The GenericMapper exists but is not actively used in the main flow.

## Decision

**We will use Manual DTO Conversion as the primary strategy** for query responses and command results, with the following rationale:

### Query Layer
- Handlers return `dict[str, Any]` from `aggregate.model_dump()`
- Dicts are lightweight and avoid ORM/entity overhead
- Interface layer (routers) performs explicit dict → DTO conversion
- Type safety enforced at API boundary via Pydantic DTOs

### Command Layer
- Handlers return domain aggregates wrapped in Result
- Routers convert aggregates to DTOs explicitly
- Same explicit conversion pattern as queries

### GenericMapper
- Remains available for complex scenarios:
  - Bulk operations with many fields
  - Nested object trees
  - Migration from legacy systems
- Not used in primary CQRS flow

## Rationale

### Advantages of Manual Conversion

1. **Type Safety**: Explicit conversion ensures type errors caught at development time
2. **Performance**: Dict intermediate is lighter than full ORM models in read path
3. **Flexibility**: Easy to shape data differently per endpoint (partial responses)
4. **Debugging**: Clear where and how data transforms
5. **Code Review**: Explicit code easier to review than "magic" mapping

### Trade-offs Accepted

1. **Boilerplate**: More code to write for each DTO conversion
2. **Maintenance**: Changes to Aggregate require updating conversion code
3. **DRY Violation**: Similar conversion logic in multiple routers

These trade-offs are acceptable because:
- Type safety and debuggability outweigh DRY in critical paths
- FastAPI/Pydantic already enforce schema at API boundary
- Conversion code is simple and testable
- GenericMapper available for complex cases

## Alternatives Considered

### Alternative 1: Use GenericMapper Everywhere

**Pros:**
- Less boilerplate code
- DRY - single mapping configuration
- Automatic handling of nested objects

**Cons:**
- Loss of type safety (Any → Any mapping)
- Hidden errors in field name mismatches
- Performance overhead for complex mappings
- Less explicit, harder to debug

**Rejected because:** Type safety and explicitness are critical in a base framework.

### Alternative 2: Auto-generate DTOs from Aggregates

**Pros:**
- Zero boilerplate
- Guaranteed sync between Aggregate and DTO

**Cons:**
- Tight coupling between domain and API
- Exposes internal domain structure
- Complex build-time code generation

**Rejected because:** Violates separation of concerns between domain and API layers.

### Alternative 3: Use ORM Models Directly in API

**Pros:**
- No conversion needed
- Direct database → API path

**Cons:**
- Couples API to database schema
- Exposes internal fields (password_hash, etc.)
- Performance issues (lazy loading, sessions)
- Security risk (mass assignment)

**Rejected because:** Violates clean architecture principles and security best practices.

## Consequences

### Positive

- **Type-safe API responses**: Pydantic validates all outgoing data
- **Performance optimized**: Dict intermediate avoids ORM overhead in read path
- **Clear data flow**: Easy to trace data transformation
- **Flexible data shaping**: Different DTOs for different endpoints
- **Security**: Never accidentally expose internal fields

### Negative

- **Boilerplate code**: ~10-15 lines per DTO conversion
- **Maintenance burden**: Aggregate changes require DTO update
- **Code duplication**: Similar conversion patterns across routers

### Neutral

- **GenericMapper available**: Can be used when complexity justifies it
- **Hybrid approach**: Mix manual and automatic as needed per use case

## Implementation Guidelines

### For Queries

```python
# Query Handler (application layer)
class GetUserHandler(QueryHandler[GetUserByIdQuery, dict[str, Any] | None]):
    async def handle(self, query: GetUserByIdQuery) -> Result[dict[str, Any] | None, Exception]:
        user = await self._repository.get_by_id(query.user_id)
        if user is None:
            return Ok(None)
        return Ok(user.model_dump())  # ✅ Return dict

# Router (interface layer)
@router.get("/{user_id}", response_model=UserDTO)
async def get_user(user_id: str, query_bus: QueryBusDep) -> UserDTO:
    result = await query_bus.dispatch(GetUserByIdQuery(user_id=user_id))
    match result:
        case Ok(user_data):
            if user_data is None:
                raise HTTPException(status_code=404)
            # ✅ Explicit conversion
            return UserDTO(
                id=user_data["id"],
                email=user_data["email"],
                username=user_data.get("username"),
                # ...
            )
```

### For Commands

```python
# Command Handler (application layer)
class CreateUserHandler(CommandHandler[CreateUserCommand, UserAggregate]):
    async def handle(self, command: CreateUserCommand) -> Result[UserAggregate, Exception]:
        # ... validation and creation
        return Ok(user_aggregate)  # ✅ Return aggregate

# Router (interface layer)
@router.post("", response_model=UserDTO)
async def create_user(data: CreateUserDTO, command_bus: CommandBusDep) -> UserDTO:
    command = CreateUserCommand(email=data.email, password=data.password)
    result = await command_bus.dispatch(command)
    match result:
        case Ok(user_aggregate):
            # ✅ Explicit conversion from aggregate
            return UserDTO(
                id=user_aggregate.id,
                email=user_aggregate.email,
                username=user_aggregate.username,
                # ...
            )
```

### When to Use GenericMapper

Use GenericMapper for:
- Bulk export/import operations (100+ fields)
- Complex nested object hierarchies (>3 levels)
- Migration scripts with many entity types
- Backwards compatibility layers

```python
# Example: Complex bulk export
from application.common.base.mapper import GenericMapper

mapper = GenericMapper(
    source_type=UserAggregate,
    target_type=UserExportDTO,
    field_mapping={"email_address": "email"},
    exclude_fields={"password_hash", "internal_id"}
)
dtos = mapper.to_dto_list(user_aggregates)
```

## Validation

Success criteria:
- ✅ All API responses use Pydantic DTOs
- ✅ No `Any` types in router signatures
- ✅ Query handlers return dicts for performance
- ✅ Command handlers return domain aggregates
- ✅ Conversion code in routers, not handlers
- ✅ GenericMapper available for complex cases

## Related Decisions

- ADR-001: CQRS Pattern (queries separate from commands)
- ADR-003: Resilience Layers (error handling strategy)
- ADR-004: Unit of Work Strategy (transaction boundaries)

## References

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [FastAPI Response Models](https://fastapi.tiangolo.com/tutorial/response-model/)
- Martin Fowler - DTO Pattern
- Clean Architecture by Robert C. Martin

## Review Notes

- Review date: 2025-Q2
- Review trigger: If conversion boilerplate exceeds 30% of router code
- Consider: Code generation for DTOs if maintenance burden increases
