# Implementation Plan

## 1. Fix High Priority Issues

- [x] 1.1 Migrate SQLModelRepository to PEP 695 syntax
  - Update `src/my_api/adapters/repositories/sqlmodel_repository.py`
  - Change `T = TypeVar("T", bound=SQLModel)` to class-level type parameters
  - Use `class SQLModelRepository[T: SQLModel, CreateT: BaseModel, UpdateT: BaseModel]`
  - Remove `Generic[T, CreateT, UpdateT]` from class inheritance
  - _Requirements: 1.1, 14.2_

- [x] 1.2 Write property test for SQLModelRepository generic types
  - **Property 1: PEP 695 Syntax Compliance**
  - **Validates: Requirements 1.1**

- [x] 1.3 Add slots=True to ErrorContext dataclass
  - Update `src/my_api/core/exceptions.py`
  - Change `@dataclass(frozen=True)` to `@dataclass(frozen=True, slots=True)`
  - _Requirements: 8.1, 12.1, 14.6_

- [x] 1.4 Write property test for ErrorContext memory optimization
  - **Property 2: Dataclass Memory Optimization**
  - **Validates: Requirements 8.1, 12.1**

- [x] 1.5 Fix InMemoryRepository callable type hint
  - Update `src/my_api/shared/repository.py`
  - Change `id_generator: callable = None` to `id_generator: Callable[[], str] | None = None`
  - Add import for `Callable` from `collections.abc`
  - _Requirements: 14.3_

- [x] 1.6 Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## 2. Migrate Circuit Breaker to PEP 695

- [x] 2.1 Update CircuitBreaker to use PEP 695 syntax
  - Update `src/my_api/shared/circuit_breaker.py`
  - Remove `P = ParamSpec("P")` and `T = TypeVar("T")`
  - Use inline type parameters in function signatures: `def call[T, **P](...)`
  - Update `circuit_breaker` decorator to use PEP 695 syntax
  - _Requirements: 1.1_

- [x] 2.2 Write property test for CircuitBreaker PEP 695 compliance
  - **Property 1: PEP 695 Syntax Compliance**
  - **Validates: Requirements 1.1**
  - Note: Existing tests in `test_circuit_breaker_properties.py` cover state transitions

## 3. Migrate Event Sourcing to PEP 695

- [x] 3.1 Update Aggregate to use PEP 695 syntax
  - Update `src/my_api/shared/event_sourcing/aggregate.py`
  - Change `class Aggregate(ABC, Generic[AggregateId])` to `class Aggregate[AggregateId: (str, int)](ABC)`
  - Remove `AggregateId = TypeVar("AggregateId", str, int)`
  - _Requirements: 1.1_

- [x] 3.2 Write property test for Aggregate PEP 695 compliance
  - **Property 1: PEP 695 Syntax Compliance**
  - **Validates: Requirements 1.1**
  - Note: Existing tests in `test_event_sourcing_properties.py` cover event replay

- [x] 3.3 Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## 4. Create Code Quality Analysis Scripts

- [x] 4.1 Create AST-based analysis script for PEP 695 compliance
  - Create `scripts/analyze_pep695_compliance.py`
  - Scan all Python files in src/my_api
  - Detect old TypeVar/ParamSpec syntax usage
  - Report files needing migration
  - _Requirements: 15.2_

- [x] 4.2 Create analysis script for __slots__ usage
  - Add to `scripts/analyze_pep695_compliance.py` or create separate script
  - Scan all dataclasses with `frozen=True`
  - Report classes missing `slots=True`
  - _Requirements: 15.3_

- [x] 4.3 Create analysis script for type annotation coverage
  - Scan all public functions in src/my_api
  - Report functions missing return type hints
  - _Requirements: 15.1_

- [x] 4.4 Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

---

## Verified as Already Implemented ✅

The following items from the original task list have been verified as already correctly implemented in the codebase:

### Result Pattern (Requirements 4.2, 4.3, 4.4)
- ✅ `src/my_api/shared/result.py` uses PEP 695 syntax with `@dataclass(frozen=True, slots=True)`
- ✅ Implements `map`, `map_err`, `unwrap`, `unwrap_or` methods
- ✅ Tests exist in `tests/properties/test_repository_properties.py`

### Specification Pattern (Requirements 5.2, 5.4)
- ✅ `src/my_api/shared/specification.py` uses PEP 695 syntax
- ✅ Implements `__and__`, `__or__`, `__invert__` operators
- ✅ Comprehensive tests in `tests/properties/test_specification_properties.py`

### Use Case @overload (Requirements 3.2)
- ✅ `src/my_api/shared/use_case.py` uses `@overload` for type narrowing
- ✅ `get(id, raise_on_missing=True)` returns `ResponseDTO`
- ✅ `get(id, raise_on_missing=False)` returns `ResponseDTO | None`

### Protocol Classes (Requirements 13.6)
- ✅ `src/my_api/shared/protocols/repository.py` has `@runtime_checkable` on all protocols
- ✅ Tests exist in `tests/properties/test_protocol_properties.py`

### Pydantic Settings (Requirements 9.1, 9.2, 9.4, 9.5)
- ✅ `src/my_api/core/config.py` uses `SecretStr` for sensitive values
- ✅ Uses `@field_validator` for pattern validation
- ✅ Uses `@lru_cache` for singleton pattern
- ✅ Tests exist in `tests/properties/test_core_config_properties.py`

### Entity ID Validation (Requirements 6.2, 6.5)
- ✅ `src/my_api/domain/value_objects/entity_id.py` uses `@dataclass(frozen=True, slots=True)`
- ✅ ULID validation in `__post_init__`
- ✅ Raises `ValueError` for invalid IDs

### Mapper Interface (Requirements 2.1, 2.3)
- ✅ `src/my_api/shared/mapper.py` uses PEP 695 syntax
- ✅ Tests in `tests/properties/test_mapper_properties.py` cover round-trip

### Repository Interface (Requirements 1.1, 1.3)
- ✅ `src/my_api/shared/repository.py` IRepository uses PEP 695 syntax
- ✅ Tests in `tests/properties/test_repository_properties.py`

### Circuit Breaker State Transitions (Requirements 5.2 from design)
- ✅ Comprehensive tests in `tests/properties/test_circuit_breaker_properties.py`

### Event Sourcing (Requirements 2.3 from design)
- ✅ Tests in `tests/properties/test_event_sourcing_properties.py`
