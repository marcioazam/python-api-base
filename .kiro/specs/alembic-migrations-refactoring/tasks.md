# Implementation Plan

- [x] 1. Implement URL validation in env.py


  - [x] 1.1 Add PLACEHOLDER_PATTERNS constant and get_database_url validation logic


    - Define list of known placeholder patterns to reject
    - Add ValueError with clear guidance message when invalid
    - Preserve existing env var precedence (DATABASE__URL > DATABASE_URL > config)


    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 1.2 Write property test for URL resolution precedence

    - **Property 2: URL Resolution Precedence**


    - **Validates: Requirements 2.2, 2.3**
  - [x] 1.3 Write property test for invalid URL rejection
    - **Property 3: Invalid URL Rejection**
    - **Validates: Requirements 2.1, 2.4**





- [x] 2. Implement model auto-discovery in env.py

  - [x] 2.1 Create import_models() function with pkgutil.iter_modules


    - Use pkgutil to iterate over my_api.domain.entities package
    - Import each module dynamically with importlib
    - Add error handling for missing package


    - Replace hardcoded Item import with auto-discovery call

    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 2.2 Write property test for auto-discovery completeness
    - **Property 1: Model Auto-Discovery Completeness**
    - **Validates: Requirements 1.1, 1.2**





- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [x] 4. Create users table migration
  - [x] 4.1 Create migration 001b_add_users_table.py
    - Add users table with id, email, hashed_password, is_active, timestamps
    - Set down_revision to "001" and update 002 to depend on "001b"
    - Create indexes for email lookup
    - _Requirements: 4.1, 4.2_
  - [x] 4.2 Write property test for FK integrity in migration chain
    - **Property 5: Foreign Key Integrity in Migration Chain**
    - **Validates: Requirements 4.1, 4.2, 4.3**



- [x] 5. Update roles migration dependency
  - [x] 5.1 Update 002_add_roles_tables.py down_revision
    - Change down_revision from "001" to "001b"
    - Verify FK to users.id now references existing table
    - _Requirements: 4.1, 4.3_

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Create Float to Numeric migration
  - [x] 7.1 Create migration 004_migrate_float_to_numeric.py
    - Use op.alter_column to change price from Float to Numeric(10,2)
    - Use op.alter_column to change tax from Float to Numeric(10,2)
    - Add downgrade to revert to Float if needed
    - _Requirements: 3.1, 3.2, 3.3_
  - [x] 7.2 Write property test for Float to Numeric round-trip
    - **Property 4: Float to Numeric Round-Trip Preservation**
    - **Validates: Requirements 3.3**

- [x] 8. Update alembic.ini placeholder
  - [x] 8.1 Replace placeholder URL with safe pattern
    - Change from "driver://user:pass@localhost/dbname" to safe placeholder
    - Add comment explaining env var override
    - _Requirements: 5.1_

- [x] 9. Update script.py.mako template
  - [x] 9.1 Remove unused sqlmodel import from template
    - Remove "import sqlmodel" line that is rarely used
    - Keep template minimal and clean
    - _Requirements: Code quality_

- [x] 10. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
