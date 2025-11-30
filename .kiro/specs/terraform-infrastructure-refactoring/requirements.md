# Requirements Document

## Introduction

Este documento especifica os requisitos para refatoração da infraestrutura Terraform do projeto my-api. O objetivo é corrigir problemas críticos de segurança, eliminar duplicações de código, melhorar a manutenibilidade e alinhar com as melhores práticas de Infrastructure as Code (IaC).

A refatoração aborda problemas identificados no code review incluindo: credenciais hardcoded, duplicação de variáveis/outputs, falta de validações, configuração de backend inflexível e otimização de custos.

## Glossary

- **Terraform**: Ferramenta de Infrastructure as Code para provisionamento de recursos em múltiplos cloud providers
- **Backend**: Configuração de armazenamento do state file do Terraform
- **State File**: Arquivo que mantém o mapeamento entre recursos declarados e recursos reais na cloud
- **Provider**: Plugin do Terraform que permite interação com APIs de cloud providers
- **Module**: Conjunto reutilizável de recursos Terraform encapsulados
- **tfvars**: Arquivo de variáveis específicas por ambiente
- **Sensitive Variable**: Variável marcada para não ser exibida em logs ou outputs
- **NAT Gateway**: Serviço de rede que permite recursos em subnets privadas acessarem a internet
- **HCL**: HashiCorp Configuration Language, linguagem declarativa do Terraform

## Requirements

### Requirement 1: Eliminação de Duplicações de Código

**User Story:** As a DevOps engineer, I want to have a single source of truth for variable and output definitions, so that I can maintain the infrastructure code without conflicts and confusion.

#### Acceptance Criteria

1. WHEN Terraform parses the configuration files THEN the system SHALL have each variable defined exactly once across all .tf files
2. WHEN Terraform parses the configuration files THEN the system SHALL have each output defined exactly once across all .tf files
3. WHEN a developer modifies a variable definition THEN the system SHALL require changes in only one location
4. WHEN running `terraform validate` THEN the system SHALL complete without duplicate declaration errors

### Requirement 2: Externalização de Credenciais e Secrets

**User Story:** As a security engineer, I want all sensitive credentials externalized from the codebase, so that secrets are not exposed in version control.

#### Acceptance Criteria

1. WHEN reviewing the Terraform codebase THEN the system SHALL contain zero hardcoded usernames, passwords, or API keys
2. WHEN a database module requires credentials THEN the system SHALL accept them via sensitive input variables
3. WHEN Terraform outputs sensitive values THEN the system SHALL mark them with `sensitive = true`
4. WHEN running `terraform plan` THEN the system SHALL mask sensitive variable values in the output
5. WHEN the codebase is committed to version control THEN the system SHALL exclude files containing actual credential values via .gitignore

### Requirement 3: Backend Configuration Dinâmico

**User Story:** As a DevOps engineer, I want to configure the Terraform backend dynamically per environment, so that I can manage multiple environments with isolated state files.

#### Acceptance Criteria

1. WHEN initializing Terraform THEN the system SHALL accept backend configuration via partial configuration files or CLI arguments
2. WHEN the backend block is defined THEN the system SHALL contain only static settings (encrypt) without environment-specific values hardcoded
3. WHEN deploying to different environments THEN the system SHALL use separate state files per environment
4. WHEN a backend.hcl template exists THEN the system SHALL document the required parameters

### Requirement 4: Validação de Variáveis de Entrada

**User Story:** As a DevOps engineer, I want input variables validated at plan time, so that invalid configurations fail fast with clear error messages.

#### Acceptance Criteria

1. WHEN a user provides an invalid region value THEN the system SHALL reject the input with a descriptive error message
2. WHEN a user provides an invalid database username format THEN the system SHALL reject the input with validation rules
3. WHEN cloud-provider-specific variables are required THEN the system SHALL validate they are non-empty when that provider is selected
4. WHEN all validations pass THEN the system SHALL proceed with terraform plan without validation errors

### Requirement 5: Otimização de Custos - NAT Gateway

**User Story:** As a cloud architect, I want to optimize NAT Gateway costs in non-production environments, so that development costs are minimized without impacting production reliability.

#### Acceptance Criteria

1. WHEN deploying to dev or staging environment THEN the system SHALL support using a single NAT Gateway
2. WHEN deploying to production environment THEN the system SHALL deploy NAT Gateways per availability zone for high availability
3. WHEN the single_nat_gateway variable is true THEN the system SHALL route all private subnets through one NAT Gateway
4. WHEN the single_nat_gateway variable is false THEN the system SHALL maintain one NAT Gateway per AZ

### Requirement 6: Estrutura de Módulos Padronizada

**User Story:** As a DevOps engineer, I want modules to follow a consistent structure with proper documentation, so that the codebase is maintainable and self-documenting.

#### Acceptance Criteria

1. WHEN a module is created THEN the system SHALL separate variables, outputs, and resources into distinct files
2. WHEN a module is created THEN the system SHALL include a README.md with usage examples
3. WHEN a module is created THEN the system SHALL include a versions.tf specifying required provider versions
4. WHEN running terraform-docs THEN the system SHALL generate accurate documentation from the module structure

### Requirement 7: Configuração Segura de Providers

**User Story:** As a DevOps engineer, I want provider configurations that work correctly regardless of which cloud provider is selected, so that the multi-cloud setup functions without runtime errors.

#### Acceptance Criteria

1. WHEN cloud_provider is set to a value other than "aws" THEN the kubernetes and helm providers SHALL not cause errors
2. WHEN accessing module outputs conditionally THEN the system SHALL use try() or coalesce() functions to handle missing values
3. WHEN a provider requires authentication THEN the system SHALL document the required environment variables or configuration

### Requirement 8: Versionamento de Imagens de Container

**User Story:** As a release engineer, I want container image versions pinned to specific tags, so that deployments are reproducible and auditable.

#### Acceptance Criteria

1. WHEN deploying via Helm THEN the system SHALL use a specific image tag variable instead of "latest"
2. WHEN the image_tag variable is not provided THEN the system SHALL fail with a clear error message
3. WHEN reviewing deployment configuration THEN the system SHALL show the exact image version being deployed

