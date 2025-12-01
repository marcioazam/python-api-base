# ADR-007: CQRS DTO Separation (Write Model vs Read Model)

## Status

**Accepted** - 2025-12-01

## Context

The application layer has two sets of DTOs for the Users bounded context:

1. **Write Model DTOs** (`application/users/dto.py`)
   - `UserDTO`, `CreateUserDTO`, `UpdateUserDTO`, `ChangePasswordDTO`, `ChangeEmailDTO`, `UserListDTO`
   - Used for command operations (create, update, delete)

2. **Read Model DTOs** (`application/read_model/users_read/dto.py`)
   - `UserReadDTO`, `UserListReadDTO`, `UserSearchResultDTO`, `UserActivityReadDTO`
   - Used for query operations, optimized for reads

There was a question about whether to consolidate these DTOs or keep them separate.

## Decision

**Keep DTOs strictly separated following CQRS (Command Query Responsibility Segregation) pattern.**

### Rationale

1. **Different Optimization Goals**
   - Write DTOs: Validation-focused, contain only fields needed for mutations
   - Read DTOs: Query-optimized, may contain denormalized/computed fields

2. **Independent Evolution**
   - Write and Read models can evolve independently
   - Adding a field to Read model doesn't require changing Write model

3. **Performance Optimization**
   - Read DTOs can include aggregated data (e.g., `permission_count`, `role_names`)
   - Write DTOs remain lean for fast validation

4. **Event Sourcing Compatibility**
   - Read models are populated by event projections
   - Clear separation enables eventual consistency patterns

## Consequences

### Positive

- **Clear Boundaries**: Each DTO has a single responsibility
- **Flexibility**: Models can be optimized independently
- **Scalability**: Read and Write can scale differently
- **Maintainability**: Changes in one don't cascade to the other

### Negative

- **More Code**: Two sets of DTOs to maintain
- **Mapping Overhead**: Need mappers between domain and each DTO type
- **Learning Curve**: Developers must understand which DTO to use

### Neutral

- Consistent with DDD/CQRS patterns
- Follows industry best practices for complex domains

## File Locations

```
src/application/
├── users/
│   └── dto.py              # Write Model DTOs (commands)
└── read_model/
    └── users_read/
        └── dto.py          # Read Model DTOs (queries)
```

## References

- [CQRS Pattern - Martin Fowler](https://martinfowler.com/bliki/CQRS.html)
- [Microsoft CQRS Documentation](https://docs.microsoft.com/en-us/azure/architecture/patterns/cqrs)
