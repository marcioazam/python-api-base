# Implementation Plan

- [x] 1. Add get_async_session function to database session module
  - [x] 1.1 Implement get_async_session generator function in src/infrastructure/db/session.py
    - Add async generator that yields AsyncSession from DatabaseSession
    - Ensure proper error handling when database not initialized
    - _Requirements: 1.1, 1.3_
  - [x] 1.2 Write property test for async session validity
    - **Property 1: Async Session Yields Valid Session**
    - **Validates: Requirements 1.1**
  - [x] 1.3 Write property test for session cleanup
    - **Property 4: Session Cleanup on Exit**
    - **Validates: Requirements 1.4**

- [x] 2. Fix router dependency injection to use real repositories
  - [x] 2.1 Update router imports and remove mock classes
    - Remove MockItemRepository and MockPedidoRepository classes
    - Import get_async_session from infrastructure.db.session
    - Import real repositories from infrastructure.db.repositories.examples
    - _Requirements: 2.1_
  - [x] 2.2 Implement real dependency injection functions
    - Create get_item_repository dependency with session injection
    - Create get_pedido_repository dependency with session injection
    - Update get_item_use_case to use real repository
    - Update get_pedido_use_case to use real repositories
    - _Requirements: 2.1, 2.2, 2.3_
  - [x] 2.3 Update all route handlers to use real dependencies
    - Replace get_mock_item_use_case with get_item_use_case
    - Replace get_mock_pedido_use_case with get_pedido_use_case
    - _Requirements: 2.1_
  - [x] 2.4 Write property test for router using real repositories
    - **Property 5: Router Uses Real Repositories**
    - **Validates: Requirements 2.1, 2.2**

- [x] 3. Checkpoint - Ensure session and router changes work
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Integrate examples bootstrap into application startup
  - [x] 4.1 Update main.py to import examples bootstrap
    - Add import for bootstrap_examples function
    - Add imports for example repositories
    - _Requirements: 3.1_
  - [x] 4.2 Add examples bootstrap call in lifespan function
    - Create repository instances with database session
    - Call bootstrap_examples with command_bus, query_bus, and repositories
    - Add appropriate logging
    - _Requirements: 3.1, 3.2, 3.3_
  - [x] 4.3 Write property test for bootstrap handler registration
    - **Property 6: Bootstrap Registers All Handlers**
    - **Validates: Requirements 3.1, 3.2, 3.3**

- [x] 5. Checkpoint - Verify application starts correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Add persistence round-trip property tests
  - [x] 6.1 Write property test for Item persistence round-trip
    - **Property 7: Item Persistence Round-Trip**
    - **Validates: Requirements 4.1, 4.2**
  - [x] 6.2 Write property test for Pedido persistence round-trip
    - **Property 8: Pedido Persistence Round-Trip**
    - **Validates: Requirements 4.3, 4.4**
  - [x] 6.3 Write property test for session transaction round-trip
    - **Property 2: Session Transaction Round-Trip**
    - **Validates: Requirements 1.2, 2.3**

- [x] 7. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
