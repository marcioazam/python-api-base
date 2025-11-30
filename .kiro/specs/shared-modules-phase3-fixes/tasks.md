# Implementation Plan

- [x] 1. Security Fixes (P0)
  - [x] 1.1 Replace print with logging in memory_profiler
    - Update LogMemoryAlertHandler to use Python logging module
    - Add SEVERITY_MAP for alert severity to log level mapping
    - Add logger instance at module level
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 1.2 Write property test for memory alert logging
    - **Property 1: Memory alert logging maps severity to correct log level**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4**

  - [x] 1.3 Add query input validation in query_analyzer
    - Create constants.py with MAX_QUERY_LENGTH and ALLOWED_IDENTIFIER_PATTERN
    - Add _validate_query() method to QueryAnalyzer
    - Add validation call at start of analyze_query()
    - _Requirements: 2.1, 2.2_

  - [x] 1.4 Write property test for query length validation
    - **Property 2: Query length validation rejects oversized queries**
    - **Validates: Requirements 2.1**

  - [x] 1.5 Write property test for valid identifier extraction
    - **Property 9: Query analyzer extracts valid identifiers only**
    - **Validates: Requirements 2.4**

  - [x] 1.6 Fix SQLAlchemy boolean comparison in multitenancy
    - Replace `is_deleted == False` with `is_deleted.is_(False)`
    - Update all boolean comparisons in TenantRepository
    - _Requirements: 3.1, 3.2_

  - [x] 1.7 Write property test for SQLAlchemy boolean filter
    - **Property 3: SQLAlchemy boolean filter uses is_() method**
    - **Validates: Requirements 3.1, 3.2**

- [x] 2. Checkpoint - Security fixes complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Performance Fixes (P1)


  - [x] 3.1 Add cache size limit to BatchLoader
    - Add max_cache_size parameter with default 10000
    - Add _enforce_cache_limit() method
    - Call limit enforcement after load_all()
    - _Requirements: 4.1_

  - [x] 3.2 Write property test for BatchLoader cache limit
    - **Property 4: BatchLoader cache respects size limit**
    - **Validates: Requirements 4.1**

  - [x] 3.3 Add automatic expiration to InMemoryStateStore
    - Add periodic cleanup in save_state() when store grows large
    - Ensure clear_expired() is called automatically
    - _Requirements: 4.2_

  - [x] 3.4 Write property test for state expiration
    - **Property 7: InMemoryStateStore clears expired states**
    - **Validates: Requirements 4.2**

  - [x] 3.5 Verify InMemoryMetricsStore limit enforcement
    - Review existing implementation
    - Add test to verify limit is respected
    - _Requirements: 4.3_

  - [x] 3.6 Write property test for metrics store limit
    - **Property 8: InMemoryMetricsStore respects max_points limit**
    - **Validates: Requirements 4.3**

  - [x] 3.7 Add configurable timeout to OAuth2
    - Add request_timeout field to OAuthConfig with default 30.0
    - Update exchange_code() and refresh_token() to use config timeout
    - _Requirements: 5.2_

  - [x] 3.8 Write property test for OAuth timeout configuration
    - **Property 11: OAuth timeout is configurable and respected**
    - **Validates: Requirements 5.2**

  - [x] 3.9 Add timeout support to LazyProxy
    - Add optional timeout parameter to get() method
    - Use asyncio.wait_for() for timeout enforcement
    - Raise TimeoutError with descriptive message
    - _Requirements: 5.1, 5.3_

  - [x] 3.10 Write property test for LazyProxy timeout
    - **Property 12: LazyProxy timeout raises TimeoutError**
    - Test that slow loader with timeout raises TimeoutError
    - Test that fast loader with timeout completes successfully
    - **Validates: Requirements 5.1, 5.3**

- [x] 4. Checkpoint - Performance fixes complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Code Quality Fixes (P2)

  - [x] 5.1 Clean up imports in memory_profiler
    - Remove unused imports from enums.py (gc, sys, tracemalloc, starlette)
    - Remove unused imports from models.py
    - Keep only necessary imports in each file
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 5.2 Clean up imports in mutation_testing
    - Remove unused imports from enums.py (dataclass, field, datetime, Path, Any, json, hashlib)
    - Remove unused imports from config.py
    - _Requirements: 6.1, 6.2_

  - [x] 5.3 Clean up imports in query_analyzer
    - Remove unused imports from enums.py (re, time, dataclass, field, datetime, timezone, Any, BaseModel)
    - Remove unused imports from models.py
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 5.4 Fix timezone-aware datetime in metrics_dashboard
    - Update Dashboard.created_at to use datetime.now(timezone.utc)
    - Update DashboardData.timestamp to use datetime.now(timezone.utc)
    - _Requirements: 7.1_

  - [x] 5.5 Fix timezone-aware datetime in shared modules


    - Update smart_routing.py: datetime.now() → datetime.now(timezone.utc) (line 72)
    - Update slo.py: datetime.now() → datetime.now(timezone.utc) (lines 217, 236, 248, 263, 264, 268)
    - Update mock_server.py: datetime.now() → datetime.now(timezone.utc) (line 119)
    - Update metrics_dashboard/dashboard.py: datetime.now() → datetime.now(timezone.utc) (line 91)
    - Update hot_reload/middleware.py: datetime.now() → datetime.now(timezone.utc) (line 81)
    - Update correlation.py: datetime.now() → datetime.now(timezone.utc) (line 171)
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 5.6 Write property test for timezone-aware datetimes
    - **Property 5: Datetime fields are timezone-aware**
    - **Validates: Requirements 7.1, 7.2, 7.3**


  - [x] 5.7 Extract constants in http2_config

    - Create http2_config/constants.py with RFC 7540 protocol limits
    - Add MAX_CONCURRENT_STREAMS_LIMIT = 2147483647 (RFC 7540 Section 6.5.2)
    - Add MAX_WINDOW_SIZE = 2147483647 (RFC 7540 Section 6.9.1)
    - Add MIN_FRAME_SIZE = 16384, MAX_FRAME_SIZE = 16777215 (RFC 7540 Section 4.2)
    - Add DEFAULT_MAX_HEADER_LIST_SIZE = 8192 (RFC 7540 Section 6.5.2)
    - Update config.py validate() to use named constants instead of magic numbers (lines 27-37)
    - _Requirements: 8.1, 8.2, 8.3_


  - [x] 5.8 Add UTF-8 encoding to file operations

    - Update MutationScoreTracker._load_history() with encoding='utf-8' (line 56)
    - Update MutationScoreTracker._save_history() with encoding='utf-8' (line 63)
    - Update parse_mutmut_results() with encoding='utf-8' (line 186)
    - _Requirements: 9.1, 9.2, 9.3_

  - [x] 5.9 Write property test for UTF-8 encoding


    - **Property 6: File operations use UTF-8 encoding**
    - **Validates: Requirements 9.1, 9.2, 9.3**


  - [x] 5.10 Fix regex escaping in query_builder

    - Update InMemoryQueryBuilder._match_pattern() in in_memory.py (line 79-81)
    - Use re.escape() for user-provided patterns before converting % and _
    - Escape special regex chars: . ^ $ * + ? { } [ ] \ | ( )
    - _Requirements: 2.2_


  - [x] 5.11 Write property test for regex escaping
    - **Property 10: Regex pattern matching escapes special characters**
    - **Validates: Requirements 2.2**


  - [x] 5.12 Update docstrings in protocols module

    - Update base.py docstring from "Protocols base definitions" to "Base protocol definitions for entity traits"
    - Update entities.py docstring from "Protocols base definitions" to "Entity protocol compositions for domain modeling"
    - Update repository.py docstring from "Protocols base definitions" to "Repository and infrastructure protocol definitions"
    - _Requirements: 10.1_

- [x] 6. Final Checkpoint - All fixes complete


  - Ensure all tests pass, ask the user if questions arise.
