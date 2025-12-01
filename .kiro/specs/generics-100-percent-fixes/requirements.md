# Requirements Document

## Introduction

Este documento define os requisitos para corrigir os 4 issues identificados na análise de conformidade de Generics PEP 695, visando atingir 100% de conformidade com o estado da arte 2025.

## Glossary

- **PEP 695**: Nova sintaxe de type parameters do Python 3.12+ (`class Foo[T]:`)
- **IdType**: Tipo genérico para identificadores de entidade (str | int)
- **Protocol**: Interface estrutural do Python (duck typing com type hints)
- **Auto-wiring**: Resolução automática de dependências baseada em type hints
- **Type Alias**: Alias de tipo que pode conflitar com Protocol de mesmo nome

## Requirements

### Requirement 1: SQLModelRepository IdType Generic Parameter

**User Story:** As a developer, I want SQLModelRepository to support generic IdType parameter, so that I can use different ID types (str, int, ULID) with full type safety.

#### Acceptance Criteria

1. WHEN SQLModelRepository is defined THEN the system SHALL include IdType as fourth type parameter matching IRepository signature
2. WHEN get_by_id is called THEN the system SHALL accept IdType parameter instead of hardcoded str
3. WHEN bulk operations use IDs THEN the system SHALL use Sequence[IdType] for type safety
4. WHEN repository is instantiated THEN the system SHALL preserve type information for all ID operations

### Requirement 2: Complete i18n/generics.py Implementation

**User Story:** As a developer, I want complete i18n generic infrastructure, so that I can handle translations with full type safety.

#### Acceptance Criteria

1. WHEN Translator[T] protocol is defined THEN the system SHALL provide translate method with typed message keys
2. WHEN MessageFormatter[T] is used THEN the system SHALL support typed placeholder substitution
3. WHEN LocalizedValue[T] is created THEN the system SHALL store value with locale information
4. WHEN PluralRules[T] is defined THEN the system SHALL support typed plural form selection
5. WHEN TranslationCatalog[TKey] is used THEN the system SHALL provide type-safe message lookup

### Requirement 3: Fix Middleware Type Duplication in bus.py

**User Story:** As a developer, I want clean type definitions without conflicts, so that I can use middleware with proper type inference.

#### Acceptance Criteria

1. WHEN Middleware protocol is defined THEN the system SHALL use only the Protocol definition with generics
2. WHEN type alias is needed THEN the system SHALL use a different name to avoid conflict
3. WHEN CommandBus uses middleware THEN the system SHALL reference the correct typed Protocol
4. WHEN middleware is added THEN the system SHALL preserve type information through the chain

### Requirement 4: Container Auto-wiring Error Handling

**User Story:** As a developer, I want proper error handling in DI container auto-wiring, so that I can debug dependency resolution issues.

#### Acceptance Criteria

1. WHEN type hints cannot be resolved THEN the system SHALL raise descriptive DependencyResolutionError
2. WHEN circular dependency is detected THEN the system SHALL raise CircularDependencyError with dependency chain
3. WHEN optional dependency is missing THEN the system SHALL skip it without error
4. WHEN auto-wiring fails THEN the system SHALL include parameter name and expected type in error message
5. WHEN factory signature is invalid THEN the system SHALL provide clear error about the issue
