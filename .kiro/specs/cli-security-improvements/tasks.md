# Implementation Plan

- [x] 1. Create CLI infrastructure modules
  - [x] 1.1 Create constants module with validation patterns and limits
    - Create `src/my_api/cli/constants.py`
    - Define SUBPROCESS_TIMEOUT, validation patterns (REVISION_PATTERN, ENTITY_NAME_PATTERN, etc.)
    - Define whitelists (ALLOWED_ALEMBIC_COMMANDS, ALLOWED_FIELD_TYPES)
    - Define exit codes (EXIT_SUCCESS, EXIT_ERROR, EXIT_TIMEOUT)
    - _Requirements: 1.1, 1.3, 2.1, 2.3, 3.3_

  - [x] 1.2 Create exceptions module with CLI error hierarchy
    - Create `src/my_api/cli/exceptions.py`
    - Implement CLIError base class with exit_code attribute
    - Implement ValidationError, CommandError, CLITimeoutError subclasses
    - _Requirements: 3.1, 3.4, 3.5_

  - [x] 1.3 Write property test for exit code consistency
    - **Property 6: Exit Code Consistency**
    - **Validates: Requirements 3.3, 3.4, 3.5**

- [x] 2. Implement input validators
  - [x] 2.1 Create validators module with validation functions
    - Create `src/my_api/cli/validators.py`
    - Implement validate_revision() with regex pattern
    - Implement validate_entity_name() with pattern and length check
    - Implement validate_path() with traversal detection
    - Implement validate_alembic_command() with whitelist
    - Implement validate_field_definition() with parsing and validation
    - _Requirements: 1.3, 2.1, 2.3, 2.5, 2.6_

  - [x] 2.2 Write property test for alembic command whitelist
    - **Property 1: Alembic Command Whitelist Validation**
    - **Validates: Requirements 1.3, 1.4**

  - [x] 2.3 Write property test for revision format validation
    - **Property 2: Revision Format Validation**
    - **Validates: Requirements 2.1, 2.2**

  - [x] 2.4 Write property test for entity name validation
    - **Property 3: Entity Name Validation**
    - **Validates: Requirements 2.3, 2.4**

  - [x] 2.5 Write property test for path traversal detection
    - **Property 4: Path Traversal Detection**
    - **Validates: Requirements 2.5**

  - [x] 2.6 Write property test for field definition parsing
    - **Property 5: Field Definition Parsing Round-Trip**
    - **Validates: Requirements 2.6**

- [x] 3. Implement secure subprocess runner
  - [x] 3.1 Create runner module with subprocess wrapper
    - Create `src/my_api/cli/runner.py`
    - Implement run_subprocess() with timeout enforcement
    - Add logging for subprocess execution
    - Handle TimeoutExpired and other exceptions
    - _Requirements: 1.1, 1.2, 1.5, 4.2_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Refactor db.py with security controls
  - [x] 5.1 Update db.py to use validators and runner
    - Import validators and runner modules
    - Replace _run_alembic with secure runner
    - Add validation for revision parameter in migrate command
    - Add validation for steps parameter in rollback command
    - Add logging for all commands
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 4.1, 4.4_

- [x] 6. Refactor generate.py with security controls
  - [x] 6.1 Update generate.py to use validators
    - Import validators module
    - Add validation for entity name parameter
    - Add validation for field definitions
    - Update parse_fields to use validate_field_definition
    - _Requirements: 2.3, 2.4, 2.6_

  - [x] 6.2 Update code generation templates for best practices
    - Update _generate_entity_content to use datetime.now(UTC)
    - Update imports to follow PEP8 ordering
    - Update _generate_routes_content to use DI pattern
    - Add TODO comments for required configuration
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 6.3 Write property test for generated code UTC datetime
    - **Property 7: Generated Code UTC Datetime**
    - **Validates: Requirements 5.1**

  - [x] 6.4 Write property test for generated code import ordering
    - **Property 8: Generated Code Import Ordering**
    - **Validates: Requirements 5.2**

- [x] 7. Refactor test.py with security controls
  - [x] 7.1 Update test.py to use validators and runner
    - Import validators and runner modules
    - Replace _run_pytest with secure runner
    - Add validation for path parameter
    - Add validation for markers parameter
    - Add logging for all commands
    - _Requirements: 1.1, 2.5, 4.1_

- [x] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Update main.py with version and logging
  - [x] 9.1 Implement dynamic version retrieval
    - Add get_version() function using importlib.metadata
    - Add fallback version with "-dev" suffix
    - Update version command to use get_version()
    - _Requirements: 6.1, 6.2_

  - [x] 9.2 Add structured logging configuration
    - Configure logging for CLI module
    - Add debug logging for command execution
    - _Requirements: 4.1, 4.3_

  - [x] 9.3 Write property test for version format
    - **Property 9: Version Format Consistency**
    - **Validates: Requirements 6.3**

- [x] 10. Update CLI __init__.py exports
  - [x] 10.1 Update module exports
    - Export new modules (constants, exceptions, validators, runner)
    - Update __all__ list
    - _Requirements: All_

- [x] 11. Final Checkpoint - Ensure all tests pass



  - Ensure all tests pass, ask the user if questions arise.
