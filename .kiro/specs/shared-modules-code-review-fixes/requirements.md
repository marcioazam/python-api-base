# Requirements Document

## Introduction

Este documento especifica os requisitos para correção de issues identificados durante o code review dos módulos compartilhados: `request_signing`, `response_transformation`, `saga`, `secrets_manager`, `streaming`, `tiered_rate_limiter`, `utils` e `waf`. As correções focam em segurança, performance, manutenibilidade e conformidade com boas práticas Python.

## Glossary

- **ReDoS**: Regular Expression Denial of Service - ataque que explora backtracking excessivo em regex
- **WAF**: Web Application Firewall - sistema de proteção contra ataques web
- **HMAC**: Hash-based Message Authentication Code - mecanismo de autenticação de mensagens
- **Provider**: Implementação concreta de um serviço abstrato (ex: AWS Secrets Manager)
- **Timezone-aware**: Datetime que possui informação de fuso horário
- **Secret Key**: Chave criptográfica usada para assinatura de requests

## Requirements

### Requirement 1: Implementação de Secrets Providers

**User Story:** As a developer, I want to have working secrets provider implementations, so that I can securely manage secrets in different environments.

#### Acceptance Criteria

1. WHEN the secrets_manager module is imported THEN the system SHALL provide a BaseSecretsProvider abstract class with methods for get, create, update, delete and rotate secrets
2. WHEN a LocalSecretsProvider is instantiated THEN the system SHALL provide an in-memory implementation for development and testing
3. WHEN get_secret is called for a non-existent secret THEN the system SHALL raise SecretNotFoundError with the secret name
4. WHEN create_secret is called THEN the system SHALL store the secret and return SecretMetadata with creation timestamp
5. WHEN update_secret is called for an existing secret THEN the system SHALL update the value and return SecretMetadata with updated timestamp

### Requirement 2: Logging de Exceções em Rotation Tasks

**User Story:** As a system operator, I want rotation failures to be logged, so that I can monitor and troubleshoot secret rotation issues.

#### Acceptance Criteria

1. WHEN a secret rotation succeeds THEN the system SHALL log an info message with the secret name
2. WHEN a secret rotation fails THEN the system SHALL log an exception with full stack trace and secret name
3. WHEN scheduling rotation THEN the system SHALL use a module-level logger with appropriate log levels

### Requirement 3: Cleanup de Imports Não Utilizados

**User Story:** As a developer, I want clean imports in all modules, so that the codebase is maintainable and follows PEP8 standards.

#### Acceptance Criteria

1. WHEN request_signing/enums.py is analyzed THEN the system SHALL contain only the Enum import and HashAlgorithm class
2. WHEN request_signing/config.py is analyzed THEN the system SHALL contain only necessary imports for SignatureConfig
3. WHEN response_transformation/enums.py is analyzed THEN the system SHALL contain only the Enum import and TransformationType class
4. WHEN streaming/enums.py is analyzed THEN the system SHALL contain only the Enum import and StreamFormat class

### Requirement 4: Timezone Awareness em Datetime

**User Story:** As a developer, I want all datetime instances to be timezone-aware, so that the system handles time correctly across different timezones.

#### Acceptance Criteria

1. WHEN ThreatDetection is created in waf/models.py THEN the timestamp field SHALL default to UTC timezone
2. WHEN any datetime.now() is called THEN the system SHALL pass timezone.utc as parameter
3. WHEN datetime fields are serialized THEN the system SHALL preserve timezone information

### Requirement 5: Proteção contra ReDoS em WAF Patterns

**User Story:** As a security engineer, I want WAF regex patterns to be protected against ReDoS attacks, so that malicious inputs cannot cause denial of service.

#### Acceptance Criteria

1. WHEN SQL injection patterns are defined THEN the system SHALL limit wildcard matches to maximum 100 characters
2. WHEN regex patterns use .* THEN the system SHALL replace with .{0,100} or similar bounded quantifier
3. WHEN a pattern is compiled THEN the system SHALL handle regex compilation errors gracefully

### Requirement 6: Validação de Secret Key Length

**User Story:** As a security engineer, I want secret keys to have minimum length requirements, so that cryptographic operations are secure.

#### Acceptance Criteria

1. WHEN RequestSigner is instantiated with a secret key shorter than 32 bytes THEN the system SHALL raise ValueError
2. WHEN RequestVerifier is instantiated with a secret key shorter than 32 bytes THEN the system SHALL raise ValueError
3. WHEN the error is raised THEN the system SHALL include the minimum required length in the error message

### Requirement 7: Import de secrets no Topo do Arquivo

**User Story:** As a developer, I want imports at the top of files, so that the code follows Python best practices and has better performance.

#### Acceptance Criteria

1. WHEN request_signing/service.py is analyzed THEN the secrets module SHALL be imported at the top of the file
2. WHEN the sign method is called THEN the system SHALL use the pre-imported secrets module

### Requirement 8: Expansão de Exports em utils/__init__.py

**User Story:** As a developer, I want all utility functions exported from the utils module, so that I can easily import them.

#### Acceptance Criteria

1. WHEN utils module is imported THEN the system SHALL export functions from datetime, ids, pagination, password and sanitization modules
2. WHEN __all__ is defined THEN the system SHALL include all public functions from submodules
