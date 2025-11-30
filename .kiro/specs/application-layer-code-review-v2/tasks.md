# Implementation Plan

- [x] 1. Enhance ItemMapper with input validation and structured logging
  - [x] 1.1 Add input type validation to ItemMapper
    - Add isinstance checks for entity/dto parameters in to_dto and to_entity
    - Raise TypeError with descriptive message for invalid types (include actual type name)
    - Raise ValueError for None inputs with clear parameter indication
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 1.2 Implement structured logging in ItemMapper
    - Replace f-string logging with structured context dict
    - Create log_context with entity_type, operation, timestamp (ISO format)
    - Use logger.debug with extra={"context": ...} pattern
    - Add error logging with exception context and error_count
    - Catch ValidationError specifically instead of broad Exception
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 1.3 Handle computed fields in to_entity conversion
    - Exclude price_with_tax from model_dump in to_entity method
    - Ensure reverse conversion doesn't fail on computed fields
    - _Requirements: 5.2_

  - [x] 1.4 Write property test for mapper round-trip consistency
    - **Property 1: Mapper Round-Trip Consistency**
    - Test that Item -> ItemResponse -> Item preserves essential fields
    - Use Hypothesis with min 100 examples
    - **Validates: Requirements 5.1**

  - [x] 1.5 Write property test for input type validation
    - **Property 2: Input Type Validation**
    - Test TypeError raised for invalid types with descriptive message
    - Test ValueError raised for None inputs
    - **Validates: Requirements 2.1, 2.2**

  - [x] 1.6 Write property test for structured logging context
    - **Property 3: Structured Logging Context**
    - Test that logger receives structured context with required fields
    - Verify entity_type, operation, timestamp present in log context
    - **Validates: Requirements 1.1, 1.2**

- [x] 2. Checkpoint - Ensure mapper tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Enhance ItemUseCase with custom validation hooks
  - [x] 3.1 Implement _validate_create hook in ItemUseCase
    - Add business rule constants (MIN_PRICE=0.01, MAX_PRICE=1_000_000.00, MAX_NAME_LENGTH=255)
    - Validate price range (MIN_PRICE to MAX_PRICE)
    - Validate name length (max MAX_NAME_LENGTH characters)
    - Collect errors in list and raise ValidationError with field-level details
    - _Requirements: 3.1, 3.3_

  - [x] 3.2 Implement _validate_update hook in ItemUseCase
    - Validate optional fields only when present (not None)
    - Use same business rules as create validation
    - Raise ValidationError with field-level details
    - _Requirements: 3.2, 3.3_

  - [x] 3.3 Write property test for validation hook invocation
    - **Property 4: Validation Hook Invocation**
    - Test that _validate_create is called before repository.create
    - Test that _validate_update is called before repository.update
    - Test ValidationError structure with field-level errors
    - **Validates: Requirements 3.1, 3.2, 3.3**

- [x] 4. Checkpoint - Ensure use case tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Add additional property tests for data integrity
  - [x] 5.1 Write property test for mapper statelessness
    - **Property 5: Mapper Statelessness**
    - Test same input produces same output regardless of previous operations
    - Verify mapper has no internal state affecting results
    - **Validates: Requirements 6.2**

  - [x] 5.2 Write property test for JSON serialization round-trip
    - **Property 6: JSON Serialization Round-Trip**
    - Test ItemResponse -> JSON -> ItemResponse preserves all fields
    - Use model_dump_json and model_validate_json
    - **Validates: Requirements 7.3**

  - [x] 5.3 Write property test for timestamp timezone preservation
    - **Property 7: Timestamp Timezone Preservation**
    - Test timezone-aware timestamps preserved through mapper conversion
    - Verify created_at and updated_at maintain timezone info
    - **Validates: Requirements 5.3**

  - [x] 5.4 Write property test for computed field exclusion

    - **Property 8: Computed Field Exclusion**
    - Test to_entity excludes price_with_tax without validation errors
    - Verify computed fields don't cause conversion failures
    - **Validates: Requirements 5.2**

- [x] 6. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
