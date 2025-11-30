# Requirements Document

## Introduction

Este documento especifica os requisitos para melhorias de segurança, qualidade e manutenibilidade do módulo CLI (`src/my_api/cli`). As melhorias abordam vulnerabilidades identificadas em subprocess, validação de entrada, tratamento de erros e logging estruturado.

## Glossary

- **CLI**: Command Line Interface - Interface de linha de comando
- **Subprocess**: Módulo Python para execução de processos externos
- **Path Traversal**: Vulnerabilidade que permite acesso a arquivos fora do diretório permitido
- **Command Injection**: Vulnerabilidade que permite execução de comandos arbitrários
- **Timeout**: Limite de tempo para execução de operações
- **Whitelist**: Lista de valores permitidos para validação

## Requirements

### Requirement 1

**User Story:** As a developer, I want subprocess calls to have proper security controls, so that malicious input cannot cause command injection or denial of service.

#### Acceptance Criteria

1. WHEN a subprocess command is executed THEN the CLI SHALL enforce a configurable timeout with a default of 300 seconds
2. WHEN a subprocess command exceeds the timeout THEN the CLI SHALL terminate the process and display an error message
3. WHEN an alembic command is requested THEN the CLI SHALL validate the command against a whitelist of allowed commands
4. WHEN an invalid alembic command is provided THEN the CLI SHALL reject the command and return exit code 1
5. WHEN subprocess execution fails THEN the CLI SHALL capture and log the error with appropriate context

### Requirement 2

**User Story:** As a developer, I want all user inputs to be validated, so that invalid or malicious data cannot compromise the system.

#### Acceptance Criteria

1. WHEN a database revision parameter is provided THEN the CLI SHALL validate it matches the pattern `^[a-zA-Z0-9_\-]+$|^head$|^base$`
2. WHEN an invalid revision format is detected THEN the CLI SHALL reject the input and display an error message
3. WHEN an entity name is provided THEN the CLI SHALL validate it contains only lowercase letters, numbers, and underscores
4. WHEN an entity name exceeds 50 characters THEN the CLI SHALL reject the input
5. WHEN a test path is provided THEN the CLI SHALL validate it does not contain path traversal sequences
6. WHEN field definitions are parsed THEN the CLI SHALL validate field names and types against allowed patterns

### Requirement 3

**User Story:** As a developer, I want consistent error handling across all CLI commands, so that errors are predictable and informative.

#### Acceptance Criteria

1. WHEN a CLI error occurs THEN the CLI SHALL use a standardized exception hierarchy
2. WHEN an error is raised THEN the CLI SHALL display a user-friendly message to stderr
3. WHEN a command fails THEN the CLI SHALL return an appropriate exit code following Unix conventions
4. WHEN a validation error occurs THEN the CLI SHALL return exit code 1
5. WHEN a timeout occurs THEN the CLI SHALL return exit code 124

### Requirement 4

**User Story:** As a developer, I want structured logging in CLI commands, so that I can audit and debug operations effectively.

#### Acceptance Criteria

1. WHEN a CLI command is executed THEN the CLI SHALL log the command name and parameters at DEBUG level
2. WHEN a subprocess is started THEN the CLI SHALL log the full command at DEBUG level
3. WHEN an error occurs THEN the CLI SHALL log the error with stack trace at ERROR level
4. WHEN a destructive operation is performed THEN the CLI SHALL log the action at WARNING level

### Requirement 5

**User Story:** As a developer, I want generated code to follow best practices, so that scaffolded entities are production-ready.

#### Acceptance Criteria

1. WHEN entity code is generated THEN the CLI SHALL use timezone-aware datetime with UTC
2. WHEN entity code is generated THEN the CLI SHALL include proper import ordering following PEP8
3. WHEN routes code is generated THEN the CLI SHALL use dependency injection patterns instead of global instances
4. WHEN code is generated THEN the CLI SHALL include TODO comments for required configuration

### Requirement 6

**User Story:** As a developer, I want CLI version information to be dynamic, so that it reflects the actual installed package version.

#### Acceptance Criteria

1. WHEN the version command is executed THEN the CLI SHALL retrieve version from package metadata
2. WHEN package metadata is unavailable THEN the CLI SHALL display a fallback version with "-dev" suffix
3. WHEN version is displayed THEN the CLI SHALL use a consistent format "{name} version: {version}"

