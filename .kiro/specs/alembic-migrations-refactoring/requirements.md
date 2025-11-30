# Requirements Document

## Introduction

Este documento especifica os requisitos para refatoração da configuração e migrations do Alembic, visando melhorar robustez, segurança, manutenibilidade e precisão de dados. O escopo inclui auto-discovery de models, validação de configuração, correção de integridade referencial e uso de tipos apropriados para valores monetários.

## Glossary

- **Alembic**: Ferramenta de migração de banco de dados para SQLAlchemy
- **SQLModel**: Biblioteca que combina SQLAlchemy e Pydantic para definição de models
- **Migration**: Script que altera o schema do banco de dados de forma versionada
- **Auto-discovery**: Mecanismo para importar automaticamente todos os models sem listagem manual
- **DATABASE_URL**: Variável de ambiente contendo a string de conexão do banco de dados
- **Numeric/Decimal**: Tipo de dado com precisão fixa para valores monetários
- **Foreign Key (FK)**: Constraint que garante integridade referencial entre tabelas

## Requirements

### Requirement 1

**User Story:** As a developer, I want models to be auto-discovered, so that I don't need to manually import each new entity in env.py.

#### Acceptance Criteria

1. WHEN a new model is added to `my_api/domain/entities/` THEN the Alembic environment SHALL automatically detect it for autogenerate
2. WHEN running migrations THEN the system SHALL import all entity modules without manual intervention
3. IF the entities package is not found THEN the system SHALL raise a clear error message indicating the missing package

### Requirement 2

**User Story:** As a DevOps engineer, I want database URL validation, so that migrations fail fast with clear errors instead of obscure connection failures.

#### Acceptance Criteria

1. WHEN DATABASE_URL environment variable is not set AND alembic.ini has placeholder value THEN the system SHALL raise ValueError with configuration instructions
2. WHEN DATABASE__URL or DATABASE_URL is set THEN the system SHALL use the environment variable value
3. WHEN a valid URL is configured in alembic.ini THEN the system SHALL use it as fallback
4. IF the URL matches the placeholder pattern THEN the system SHALL reject it and provide guidance

### Requirement 3

**User Story:** As a database administrator, I want proper numeric types for monetary values, so that financial calculations maintain precision.

#### Acceptance Criteria

1. WHEN storing price values THEN the system SHALL use Numeric type with precision 10 and scale 2
2. WHEN storing tax values THEN the system SHALL use Numeric type with precision 10 and scale 2
3. WHEN migrating existing Float data THEN the system SHALL preserve values with appropriate rounding

### Requirement 4

**User Story:** As a developer, I want referential integrity in migrations, so that foreign key constraints reference existing tables.

#### Acceptance Criteria

1. WHEN user_roles table references users.id THEN the users table SHALL exist in a prior migration
2. WHEN creating foreign key constraints THEN the referenced table SHALL be created first
3. IF a migration references a non-existent table THEN the migration chain SHALL include the missing table creation

### Requirement 5

**User Story:** As a security engineer, I want safe placeholder values in configuration, so that sensitive patterns are not exposed in logs or error messages.

#### Acceptance Criteria

1. WHEN alembic.ini contains database URL THEN the placeholder SHALL NOT contain realistic credentials
2. WHEN logging connection errors THEN the system SHALL NOT expose the full connection string
3. WHEN configuration is invalid THEN error messages SHALL guide without exposing sensitive patterns
