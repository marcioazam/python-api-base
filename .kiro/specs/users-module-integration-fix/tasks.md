# Implementation Plan

- [x] 1. Corrigir imports nos testes de propriedades
  - [x] 1.1 Atualizar imports em `test_mapper_roundtrip_properties.py`
    - Substituir `my_app.application.users.mappers` por `application.users.commands.mapper`
    - Substituir `my_app.application.users.dto` por `application.users.commands.dtos`
    - Substituir `my_app.domain.users.aggregates` por `domain.users.aggregates`
    - Remover o bloco try/except com pytest.skip
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 1.2 Escrever property test para round-trip do mapper
    - **Property 1: Mapper Round-Trip Preserves Data**
    - **Validates: Requirements 4.1, 4.2, 4.3**
    - Usar Hypothesis com min 100 exemplos
    - Anotar com `**Feature: users-module-integration-fix, Property 1**`

- [x] 2. Checkpoint - Verificar testes de mapper
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Consolidar routers de users
  - [x] 3.1 Atualizar `src/interface/v1/auth/__init__.py`
    - Remover export de `users_router`
    - Manter apenas `auth_router` no `__all__`
    - _Requirements: 1.1, 3.3_

  - [x] 3.2 Atualizar `src/main.py` para usar router CQRS
    - Alterar import de `from interface.v1.auth import auth_router, users_router`
    - Para `from interface.v1.auth import auth_router` e `from interface.v1.users_router import router as users_router`
    - Manter registro do router com prefix `/api/v1`
    - _Requirements: 1.1, 3.1, 3.2_

  - [x] 3.3 Remover ou deprecar `src/interface/v1/auth/users_router.py`
    - Renomear para `users_router_mock.py` (deprecado) ou remover
    - Adicionar comentário de deprecação se mantido
    - _Requirements: 1.4_

- [x] 4. Checkpoint - Verificar integração do router
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Adicionar testes de integração para endpoints CQRS
  - [x] 5.1 Criar teste para POST `/api/v1/users`
    - Verificar que CreateUserCommand é despachado
    - Verificar resposta com UserDTO correto
    - **Property 2: Command Dispatch Preserves User Data**
    - **Validates: Requirements 1.2**

  - [x] 5.2 Criar teste para GET `/api/v1/users`
    - Verificar que ListUsersQuery é despachado
    - Verificar resposta paginada
    - _Requirements: 1.3_

  - [x] 5.3 Criar teste para GET `/api/v1/users/{id}`
    - Verificar que GetUserByIdQuery é despachado
    - Verificar resposta com UserDTO ou 404
    - _Requirements: 1.3_

- [x] 6. Final Checkpoint - Verificar todos os testes
  - Ensure all tests pass, ask the user if questions arise.
