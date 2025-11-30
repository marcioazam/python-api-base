# Requirements Document

## Introduction

Este documento especifica os requisitos para correção de issues identificados no code review dos módulos shared phase 2. O objetivo é resolver 23 issues de segurança, performance, tipagem e boas práticas em 10 módulos: http2_config, lazy, memory_profiler, metrics_dashboard, multitenancy, mutation_testing, oauth2, protocols, query_analyzer e query_builder.

## Glossary

- **ReDoS**: Regular Expression Denial of Service - ataque que explora regex mal construídas
- **Memory Leak**: Vazamento de memória por objetos não liberados
- **Timezone-aware**: Datetime com informação de fuso horário
- **SQLAlchemy**: ORM Python para acesso a banco de dados
- **Sanitização**: Processo de limpeza e validação de input

## Requirements

### Requirement 1: Security - Logging em Produção

**User Story:** As a system administrator, I want proper logging instead of print statements, so that I can monitor memory alerts in production environments.

#### Acceptance Criteria

1. WHEN the LogMemoryAlertHandler receives a memory alert THEN the system SHALL log the alert using Python's logging module with appropriate severity level
2. WHEN a memory alert has severity CRITICAL THEN the system SHALL log at ERROR level
3. WHEN a memory alert has severity WARNING THEN the system SHALL log at WARNING level
4. WHEN a memory alert has severity INFO THEN the system SHALL log at INFO level

### Requirement 2: Security - Query Input Validation

**User Story:** As a security engineer, I want SQL query inputs to be validated and sanitized, so that the system is protected against ReDoS and injection attacks.

#### Acceptance Criteria

1. WHEN a query exceeds 10000 characters THEN the QueryAnalyzer SHALL reject it with a ValueError
2. WHEN a query contains potentially malicious patterns THEN the QueryAnalyzer SHALL sanitize the input before processing
3. WHEN regex operations are performed on user input THEN the system SHALL use timeout-protected regex matching
4. WHEN extracting table/column names THEN the system SHALL validate against allowed character patterns

### Requirement 3: Security - SQLAlchemy Boolean Comparison

**User Story:** As a developer, I want proper SQLAlchemy boolean comparisons, so that queries are generated correctly and securely.

#### Acceptance Criteria

1. WHEN filtering by is_deleted field THEN the TenantRepository SHALL use SQLAlchemy's is_() method instead of == operator
2. WHEN applying boolean filters THEN the system SHALL generate parameterized queries

### Requirement 4: Performance - Cache Size Limits

**User Story:** As a system operator, I want cache sizes to be bounded, so that the application does not run out of memory.

#### Acceptance Criteria

1. WHEN BatchLoader cache exceeds max_cache_size THEN the system SHALL evict oldest entries
2. WHEN InMemoryStateStore grows beyond threshold THEN the system SHALL automatically clear expired states
3. WHEN InMemoryMetricsStore exceeds max_points THEN the system SHALL trim oldest points

### Requirement 5: Performance - Async Timeouts

**User Story:** As a developer, I want async operations to have configurable timeouts, so that the system does not hang indefinitely.

#### Acceptance Criteria

1. WHEN LazyProxy.get() is called THEN the system SHALL support an optional timeout parameter
2. WHEN OAuth2 HTTP requests are made THEN the timeout SHALL be configurable via OAuthConfig
3. WHEN timeout is exceeded THEN the system SHALL raise TimeoutError with descriptive message

### Requirement 6: Code Quality - Import Cleanup

**User Story:** As a maintainer, I want clean imports in all modules, so that the codebase is easier to understand and faster to load.

#### Acceptance Criteria

1. WHEN a module is loaded THEN it SHALL only import dependencies that are actually used
2. WHEN enums.py files are loaded THEN they SHALL not import dataclass, field, datetime, or other unused modules
3. WHEN models.py files are loaded THEN they SHALL only import types needed for model definitions

### Requirement 7: Code Quality - Timezone Consistency

**User Story:** As a developer, I want all datetime fields to be timezone-aware, so that timestamps are consistent across the application.

#### Acceptance Criteria

1. WHEN a datetime default is created THEN the system SHALL use datetime.now(timezone.utc)
2. WHEN comparing datetimes THEN the system SHALL ensure both are timezone-aware
3. WHEN serializing datetimes THEN the system SHALL include timezone information

### Requirement 8: Code Quality - Constants Extraction

**User Story:** As a maintainer, I want magic numbers replaced with named constants, so that the code is self-documenting.

#### Acceptance Criteria

1. WHEN HTTP/2 protocol limits are referenced THEN the system SHALL use named constants from a constants module
2. WHEN validation thresholds are checked THEN the system SHALL reference named constants
3. WHEN constants are defined THEN they SHALL include documentation comments explaining their source (e.g., RFC number)

### Requirement 9: Code Quality - File I/O Encoding

**User Story:** As a developer, I want file operations to specify encoding explicitly, so that the code works correctly on all platforms.

#### Acceptance Criteria

1. WHEN opening files for reading THEN the system SHALL specify encoding='utf-8'
2. WHEN opening files for writing THEN the system SHALL specify encoding='utf-8'
3. WHEN JSON files are read/written THEN the system SHALL handle encoding errors gracefully

### Requirement 10: Code Quality - Docstring Consistency

**User Story:** As a developer, I want consistent and specific docstrings, so that I can understand each module's purpose.

#### Acceptance Criteria

1. WHEN a module __init__.py is created THEN it SHALL have a specific docstring describing the module's purpose
2. WHEN a class is defined THEN it SHALL have a docstring describing its responsibility
3. WHEN a public method is defined THEN it SHALL have a docstring with Args and Returns sections
