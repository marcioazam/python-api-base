# Implementation Plan

## Phase 1: Consolidação de Value Objects

- [x] 1. Consolidar Value Objects duplicados
  - [x] 1.1 Criar módulo `src/shared/value_objects/__init__.py` com exports
    - Criar estrutura de diretório para value objects compartilhados
    - Definir `__all__` com exports públicos
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 1.2 Consolidar `Money` value object
    - Mover implementação canônica para `src/shared/value_objects/money.py`
    - Usar `@dataclass(frozen=True, slots=True)`
    - Implementar `create` classmethod e `__str__`
    - Remover duplicatas em `domain/common/currency.py` e `domain/common/value_objects.py`
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 1.3 Write property test for Money value object
    - **Property 4: Value Object Pattern Consistency**
    - Testar imutabilidade, equality, serialização
    - **Validates: Requirements 4.5**

  - [x] 1.4 Consolidar `Email` value object
    - Mover para `src/shared/value_objects/email.py`
    - Unificar implementações de `domain/users/value_objects.py` e `domain/common/value_objects_common.py`
    - Garantir validação em `__post_init__` e normalização lowercase
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 1.5 Consolidar `PhoneNumber` value object
    - Mover para `src/shared/value_objects/phone.py`
    - Unificar implementações duplicadas
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 1.6 Write property tests for Email and PhoneNumber
    - **Property 4: Value Object Pattern Consistency**
    - Testar validação, normalização, equality
    - **Validates: Requirements 4.5**

- [x] 2. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 2: Atualização PEP 695 Syntax

- [x] 3. Atualizar Domain Layer para PEP 695
  - [x] 3.1 Atualizar `src/domain/common/specification.py`
    - Verificar e garantir sintaxe `class Specification[T]:`
    - Remover qualquer uso de `Generic[T]` ou `TypeVar`
    - _Requirements: 1.1, 1.3_

  - [x] 3.2 Atualizar `src/domain/common/advanced_specification/`
    - Atualizar `base.py`, `builder.py`, `combinators.py`, `field.py`
    - Garantir `class BaseSpecification[T]:` em todos os arquivos
    - _Requirements: 1.1, 1.3, 1.4_

  - [x] 3.3 Write property test for Specification composition
    - **Property 6: Specification Composition**
    - Testar `&`, `|`, `~` operators
    - **Validates: Requirements 6.2**

  - [x] 3.4 Atualizar `src/domain/common/mixins.py`
    - Verificar se mixins usam sintaxe moderna
    - Converter `Optional[X]` para `X | None`
    - _Requirements: 1.1, 12.5_

- [x] 4. Atualizar Core Layer para PEP 695
  - [x] 4.1 Verificar `src/core/base/entity.py`
    - Garantir `class BaseEntity[IdType: (str, int)]:` syntax
    - Verificar bounds em `AuditableEntity`, `VersionedEntity`
    - _Requirements: 1.1, 1.3, 2.1_

  - [x] 4.2 Verificar `src/core/base/result.py`
    - Garantir `type Result[T, E] = Ok[T] | Err[E]` syntax
    - Verificar `@dataclass(frozen=True, slots=True)` em Ok/Err
    - _Requirements: 1.1, 1.5, 2.3_

  - [x] 4.3 Write property test for Result round-trip
    - **Property 5: Result Pattern Round-Trip**
    - Testar `to_dict()` e `result_from_dict()` preservam valores
    - **Validates: Requirements 5.5, 13.1**

  - [x] 4.4 Verificar `src/core/base/repository.py` e módulos relacionados
    - Garantir `class IRepository[T: BaseEntity, IdType: (str, int)]:` syntax
    - Verificar bounds apropriados
    - _Requirements: 1.1, 1.3, 2.1, 7.1_

  - [x] 4.5 Write property test for Repository interface
    - **Property 7: Repository Interface Compliance**
    - Testar InMemoryRepository implementa interface corretamente
    - **Validates: Requirements 7.2, 7.5**

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 3: Atualização Application Layer

- [x] 6. Atualizar Handlers e DTOs
  - [x] 6.1 Verificar `src/application/_shared/cqrs/handlers.py`
    - Garantir `class CommandHandler[TCommand: BaseCommand, TResult]:` syntax
    - Garantir `class QueryHandler[TQuery: BaseQuery, TResult]:` syntax
    - _Requirements: 1.1, 1.3, 2.2, 8.1, 8.2_

  - [x] 6.2 Write property test for Handler type safety
    - **Property 8: Handler Type Safety**
    - Testar que handlers retornam Result[TResult, Exception]
    - **Validates: Requirements 8.3**

  - [x] 6.3 Verificar `src/application/_shared/dto.py`
    - Garantir `class ApiResponse[T]:` e `class PaginatedResponse[T]:` syntax
    - Verificar computed_fields funcionam corretamente
    - _Requirements: 1.1, 9.1, 9.2_

  - [x] 6.4 Write property test for DTO consistency
    - **Property 9: DTO Response Consistency**
    - Testar PaginatedResponse computed fields (pages, has_next, has_previous)
    - **Validates: Requirements 9.1, 9.2_

- [x] 7. Atualizar Shared Layer
  - [x] 7.1 Verificar `src/shared/utils/pagination.py`
    - Garantir `class OffsetPaginationResult[T]:` e `class CursorPaginationResult[T]:` syntax
    - _Requirements: 1.1, 3.5_

  - [x] 7.2 Write property test for Pagination cursor
    - **Property 14: Pagination Cursor Preservation**
    - Testar encode_cursor/decode_cursor round-trip
    - **Validates: Requirements 13.5**

  - [x] 7.3 Verificar `src/shared/localization/i18n.py`
    - Garantir TranslationService usa tipos modernos
    - Converter `Optional` para `| None`
    - _Requirements: 1.1, 10.4, 12.5_

- [x] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 4: Padronização de Mensagens e Constantes

- [x] 9. Centralizar Mensagens de Erro
  - [x] 9.1 Criar/Atualizar `src/core/errors/messages.py`
    - Definir `class ErrorMessages(str, Enum)` com todas as mensagens
    - Usar templates parametrizados `{field}`, `{id}`, etc.
    - _Requirements: 10.1, 10.2, 10.3_

  - [x] 9.2 Criar `src/core/errors/status.py`
    - Definir `class OperationStatus(str, Enum)` para status codes
    - Definir `class ValidationStatus(str, Enum)` para validação
    - _Requirements: 10.2_

  - [x] 9.3 Write property test for Enum status codes
    - **Property 10: Enum Status Codes**
    - Testar que todos os status são Enum members
    - **Validates: Requirements 10.2, 10.5**

  - [ ] 9.4 Atualizar referências de mensagens hardcoded
    - Buscar strings hardcoded em exceptions
    - Substituir por referências a ErrorMessages
    - _Requirements: 10.1_

- [x] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 5: Code Metrics e Documentação

- [x] 11. Verificar e Corrigir Code Metrics
  - [x] 11.1 Analisar funções > 50 linhas
    - Identificar funções que excedem limite
    - Refatorar em funções menores
    - _Requirements: 11.1_

  - [x] 11.2 Analisar classes > 300 linhas
    - Identificar classes que excedem limite
    - Dividir em classes focadas (já feito em alguns módulos)
    - _Requirements: 11.2_

  - [x] 11.3 Analisar nesting > 3 níveis
    - Identificar blocos com nesting excessivo
    - Aplicar early returns e extract method
    - _Requirements: 11.3_

  - [x] 11.4 Write property test for code metrics
    - **Property 11: Code Metrics Compliance**
    - Testar limites de linhas e nesting via AST analysis
    - **Validates: Requirements 11.1, 11.2, 11.3**

- [x] 12. Verificar Documentação
  - [x] 12.1 Verificar docstrings em funções públicas
    - Garantir todas as funções públicas têm docstrings
    - Incluir Args, Returns, Raises quando aplicável
    - _Requirements: 12.1_

  - [x] 12.2 Verificar docstrings em classes públicas
    - Garantir todas as classes públicas têm docstrings
    - Documentar type parameters em classes genéricas
    - _Requirements: 12.2, 12.3_

  - [x] 12.3 Write property test for documentation
    - **Property 12: Documentation Consistency**
    - Testar presença de docstrings via AST
    - **Validates: Requirements 12.1, 12.2**

- [x] 13. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 6: Entity Serialization e Testes Finais

- [x] 14. Verificar Entity Serialization
  - [x] 14.1 Verificar `BaseEntity` serialization
    - Garantir `model_dump()` preserva id, created_at, updated_at
    - Garantir `model_validate()` reconstrói corretamente
    - _Requirements: 13.2, 13.3_

  - [x] 14.2 Write property test for Entity round-trip
    - **Property 13: Entity Serialization Round-Trip**
    - Testar serialização preserva campos obrigatórios
    - **Validates: Requirements 13.2, 13.3**

  - [x] 14.3 Verificar Specification serialization
    - Garantir specs podem ser serializadas para SQL conditions
    - _Requirements: 13.4_

- [x] 15. Testes de Integração
  - [x] 15.1 Write integration tests for Repository + Specification
    - Testar que specs funcionam com InMemoryRepository
    - Testar filtering com specs compostas
    - _Requirements: 6.4, 7.4_

  - [x] 15.2 Write integration tests for Handler + Result
    - Testar fluxo completo command -> handler -> result
    - _Requirements: 5.2, 8.3_

- [x] 16. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 7: Documentação Final

- [x] 17. Criar Relatório de Code Review
  - [x] 17.1 Criar `docs/2025-generics-clean-code-review-report.md`
    - Documentar mudanças realizadas
    - Listar arquivos modificados
    - Resumir melhorias de type safety
    - _Requirements: 12.1_

  - [x] 17.2 Atualizar ADR se necessário
    - Documentar decisões arquiteturais significativas
    - Registrar trade-offs e alternativas consideradas
    - _Requirements: 12.1_

