# Implementation Plan

## Fase 1: SQLModelRepository IdType Fix

- [x] 1. Adicionar IdType genérico ao SQLModelRepository
  - [x] 1.1 Atualizar class signature com IdType parameter
    - Modificar `SQLModelRepository[T, CreateT, UpdateT]` para `SQLModelRepository[T, CreateT, UpdateT, IdType: (str, int) = str]`
    - Atualizar herança para `IRepository[T, CreateT, UpdateT, IdType]`
    - _Requirements: 1.1_
  - [x] 1.2 Atualizar métodos para usar IdType
    - Modificar `get_by_id(self, id: str)` para `get_by_id(self, id: IdType)`
    - Modificar `update(self, id: str, ...)` para `update(self, id: IdType, ...)`
    - Modificar `delete(self, id: str, ...)` para `delete(self, id: IdType, ...)`
    - Modificar `exists(self, id: str)` para `exists(self, id: IdType)`
    - _Requirements: 1.2_
  - [x] 1.3 Atualizar bulk operations para usar Sequence[IdType]
    - Modificar `bulk_update(self, updates: Sequence[tuple[str, UpdateT]])` para `Sequence[tuple[IdType, UpdateT]]`
    - Modificar `bulk_delete(self, ids: Sequence[str], ...)` para `Sequence[IdType]`
    - _Requirements: 1.3_
  - [x] 1.4 Write property test for Repository IdType Consistency
    - **Property 1: Repository IdType Consistency**
    - **Validates: Requirements 1.2, 1.3, 1.4**

- [x] 2. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Fase 2: Complete i18n/generics.py

- [x] 3. Completar arquivo i18n/generics.py truncado
  - [x] 3.1 Completar Locale class e adicionar constantes
    - Finalizar `Locale` class com métodos restantes
    - Adicionar constantes: EN_US, EN_GB, PT_BR, ES_ES, FR_FR, DE_DE, IT_IT, JA_JP, ZH_CN
    - _Requirements: 2.1_
  - [x] 3.2 Implementar Translator[TKey] protocol
    - Criar `Translator[TKey](Protocol)` com método `translate(key: TKey, locale: Locale) -> str`
    - Adicionar `@runtime_checkable` decorator
    - _Requirements: 2.1_
  - [x] 3.3 Implementar MessageFormatter[T] protocol
    - Criar `MessageFormatter[T](Protocol)` com método `format(template: str, values: T) -> str`
    - Implementar `DictMessageFormatter` como implementação concreta
    - _Requirements: 2.2_
  - [x] 3.4 Implementar LocalizedValue[T] dataclass
    - Criar `LocalizedValue[T]` com campos `value: T` e `locale: Locale`
    - Adicionar método `with_locale(locale: Locale) -> LocalizedValue[T]`
    - _Requirements: 2.3_
  - [x] 3.5 Implementar PluralRules[T] protocol
    - Criar `PluralRules[T](Protocol)` com método `select(count: int, forms: dict[str, T]) -> T`
    - Implementar `EnglishPluralRules` e `PortuguesePluralRules`
    - _Requirements: 2.4_
  - [x] 3.6 Implementar TranslationCatalog[TKey]
    - Criar `TranslationCatalog[TKey]` class com métodos `get`, `get_or_default`, `register`
    - Adicionar suporte a fallback locale
    - _Requirements: 2.5_
  - [x] 3.7 Adicionar NumberFormatter e DateFormatter
    - Criar `NumberFormatter[T]` para formatação de números
    - Criar `DateFormatter` para formatação de datas
    - _Requirements: 2.2_
  - [x] 3.8 Write property tests for i18n generics
    - **Property 2: LocalizedValue Round-Trip**
    - **Property 3: MessageFormatter Placeholder Substitution**
    - **Property 4: PluralRules Selection**
    - **Property 5: TranslationCatalog Lookup**
    - **Validates: Requirements 2.2, 2.3, 2.4, 2.5**

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Fase 3: Fix Middleware Type Duplication

- [x] 5. Corrigir duplicação de tipo Middleware em bus.py
  - [x] 5.1 Remover type alias conflitante
    - Remover linha `Middleware = Callable[[Any, Callable[..., Any]], Any]`
    - Manter apenas `Middleware[TCommand, TResult](Protocol)`
    - _Requirements: 3.1, 3.2_
  - [x] 5.2 Criar MiddlewareFunc type alias
    - Adicionar `MiddlewareFunc = Callable[[Any, Callable[..., Awaitable[Any]]], Awaitable[Any]]`
    - Usar nome distinto para evitar conflito
    - _Requirements: 3.2_
  - [x] 5.3 Atualizar CommandBus para usar tipos corretos
    - Atualizar `_middleware: list[Middleware]` para `list[MiddlewareFunc]`
    - Atualizar `add_middleware` signature
    - _Requirements: 3.3_
  - [x] 5.4 Write property test for Middleware Type Preservation
    - **Property 6: Middleware Type Preservation**
    - **Validates: Requirements 3.4**

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Fase 4: Container Error Handling

- [x] 7. Adicionar error handling ao DI Container
  - [x] 7.1 Criar exception classes
    - Criar `DependencyResolutionError` com `service_type`, `param_name`, `expected_type`
    - Criar `CircularDependencyError` com `chain: list[type]`
    - Criar `InvalidFactoryError` com `factory`, `reason`
    - _Requirements: 4.1, 4.2, 4.5_
  - [x] 7.2 Implementar detecção de dependência circular
    - Adicionar `_resolution_stack: list[type]` ao Container
    - Verificar stack antes de resolver cada dependência
    - Raise `CircularDependencyError` se tipo já está na stack
    - _Requirements: 4.2_
  - [x] 7.3 Implementar handling de Optional[T]
    - Detectar `Optional[T]` ou `T | None` em type hints
    - Retornar `None` se dependência não está registrada
    - _Requirements: 4.3_
  - [x] 7.4 Melhorar mensagens de erro
    - Incluir `param_name` e `expected_type` em todas as mensagens
    - Adicionar contexto sobre o serviço sendo resolvido
    - _Requirements: 4.4_
  - [x] 7.5 Validar factory signature
    - Verificar se factory é callable
    - Verificar se type hints são válidos
    - Raise `InvalidFactoryError` se inválido
    - _Requirements: 4.5_
  - [x] 7.6 Write property tests for Container error handling
    - **Property 7: DependencyResolutionError Contains Info**
    - **Property 8: CircularDependencyError Contains Chain**
    - **Property 9: Optional Dependency Handling**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**

- [x] 8. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Verificar que todos os 4 issues foram corrigidos
  - Confirmar 100% de conformidade com PEP 695 Generics
