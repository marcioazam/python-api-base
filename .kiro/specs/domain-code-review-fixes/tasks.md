# Implementation Plan

- [x] 1. Fix Timezone-Aware Datetime in Domain Entities
  - [x] 1.1 Update audit_log.py with timezone-aware datetime
    - Import `timezone` from datetime module
    - Replace `datetime.now()` with `datetime.now(timezone.utc)`
    - Update SQLAlchemy columns to use `DateTime(timezone=True)`
    - _Requirements: 1.1, 1.2_
  - [x] 1.2 Update item.py with timezone-aware datetime
    - Import `timezone` from datetime module
    - Replace `datetime.now()` with `datetime.now(timezone.utc)`
    - Update SQLAlchemy columns to use `DateTime(timezone=True)`
    - _Requirements: 1.1, 1.2_
  - [x] 1.3 Update role.py with timezone-aware datetime
    - Import `timezone` from datetime module
    - Replace `datetime.now()` with `datetime.now(timezone.utc)`
    - Update SQLAlchemy columns to use `DateTime(timezone=True)`
    - _Requirements: 1.1, 1.2_
  - [x] 1.4 Write property test for timezone-aware timestamps
    - **Property 1: Entity Timestamps Are Timezone-Aware**
    - **Validates: Requirements 1.1, 1.3**

- [x] 2. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Improve Domain Layer Module Exports
  - [x] 3.1 Update entities/__init__.py with __all__ exports
    - Add `__all__` list with all entity classes
    - Import and re-export entity classes
    - _Requirements: 2.1, 2.2_
  - [x] 3.2 Update domain/__init__.py with convenient exports
    - Add `__all__` list with commonly used components
    - Provide convenient access to entities
    - _Requirements: 2.3_

- [x] 4. Add Repository Interface Foundations
  - [x] 4.1 Create repositories/base.py with generic protocol
    - Define `RepositoryProtocol` using Python Protocol
    - Include CRUD method signatures with type hints
    - Add comprehensive docstrings
    - _Requirements: 3.1, 3.2, 3.3_
  - [x] 4.2 Update repositories/__init__.py with exports
    - Add `__all__` list with repository interfaces
    - Export `RepositoryProtocol`
    - _Requirements: 2.1_

- [x] 5. Add Value Object Foundations
  - [x] 5.1 Create value_objects/money.py
    - Implement `Money` dataclass with Decimal precision
    - Add arithmetic operations (__add__, __sub__)
    - Ensure immutability with frozen=True
    - _Requirements: 4.1_
  - [x] 5.2 Create value_objects/entity_id.py
    - Implement typed ID value objects (EntityId, ItemId, RoleId, UserId)
    - Add validation for ULID format (26 characters, Crockford Base32)
    - Ensure immutability with frozen=True dataclass
    - _Requirements: 4.2_
  - [x] 5.3 Update value_objects/__init__.py with exports
    - Add `__all__` list with value object classes
    - Export Money and EntityId classes
    - _Requirements: 2.1_
  - [x] 5.4 Write property test for value object equality
    - **Property 2: Value Object Equality**
    - **Validates: Requirements 4.3**

- [x] 6. Final Checkpoint - Ensure all tests pass

  - Ensure all tests pass, ask the user if questions arise.
