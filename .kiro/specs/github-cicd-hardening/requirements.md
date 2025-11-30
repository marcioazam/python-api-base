# Requirements Document

## Introduction

Este documento especifica os requisitos para hardening e melhorias das configurações de CI/CD do GitHub Actions, Dependabot e CodeRabbit. O objetivo é aumentar a segurança da supply chain, resiliência dos pipelines e conformidade com melhores práticas de DevSecOps.

## Glossary

- **GitHub Actions**: Plataforma de CI/CD integrada ao GitHub para automação de workflows
- **Dependabot**: Ferramenta automatizada de atualização de dependências do GitHub
- **CodeRabbit**: Ferramenta de code review automatizado com IA
- **Supply Chain Security**: Segurança da cadeia de suprimentos de software
- **SAST**: Static Application Security Testing
- **SBOM**: Software Bill of Materials
- **Cosign**: Ferramenta de assinatura de containers da Sigstore
- **Action Pinning**: Prática de fixar versões específicas de GitHub Actions usando SHA ou versão semântica

## Requirements

### Requirement 1: Action Version Pinning

**User Story:** As a security engineer, I want all GitHub Actions to use pinned versions, so that I can prevent supply chain attacks from compromised action repositories.

#### Acceptance Criteria

1. WHEN a workflow references a GitHub Action THEN the CI/CD System SHALL use a specific version tag or SHA hash instead of branch references like `@master` or `@main`
2. WHEN the Trivy action is referenced THEN the CI/CD System SHALL use version `0.28.0` or later with explicit version pinning
3. WHEN the TruffleHog action is referenced THEN the CI/CD System SHALL use version `v3.88.0` or later with explicit version pinning
4. WHEN the SBOM action is referenced THEN the CI/CD System SHALL use version `v0.17.8` or later with explicit version pinning
5. WHEN the gh-release action is referenced THEN the CI/CD System SHALL use version `v2` or later with explicit version pinning

### Requirement 2: Job Timeout Configuration

**User Story:** As a DevOps engineer, I want all CI/CD jobs to have timeout limits, so that I can prevent runaway jobs from consuming unlimited resources.

#### Acceptance Criteria

1. WHEN a lint job executes THEN the CI/CD System SHALL enforce a maximum timeout of 10 minutes
2. WHEN a test job executes THEN the CI/CD System SHALL enforce a maximum timeout of 20 minutes
3. WHEN a build job executes THEN the CI/CD System SHALL enforce a maximum timeout of 15 minutes
4. WHEN a security scan job executes THEN the CI/CD System SHALL enforce a maximum timeout of 10 minutes
5. WHEN a release job executes THEN the CI/CD System SHALL enforce a maximum timeout of 30 minutes
6. WHEN a CodeQL analysis job executes THEN the CI/CD System SHALL enforce a maximum timeout of 15 minutes

### Requirement 3: Container Image Signing

**User Story:** As a security engineer, I want container images to be cryptographically signed, so that I can verify image authenticity and integrity before deployment.

#### Acceptance Criteria

1. WHEN a container image is built for release THEN the CI/CD System SHALL sign the image using cosign with keyless signing
2. WHEN a container image is pushed to the registry THEN the CI/CD System SHALL generate and attach SBOM and provenance attestations
3. WHEN the release workflow executes THEN the CI/CD System SHALL request `id-token: write` permission for OIDC-based signing

### Requirement 4: Dependabot Configuration Enhancement

**User Story:** As a team lead, I want Dependabot to group production dependencies and assign reviewers automatically, so that I can streamline the dependency update process.

#### Acceptance Criteria

1. WHEN Dependabot creates a PR for pip dependencies THEN the Dependabot System SHALL group production dependencies (fastapi, pydantic, sqlalchemy, uvicorn, alembic) together
2. WHEN Dependabot creates any PR THEN the Dependabot System SHALL assign configured reviewers automatically
3. WHEN Dependabot creates any PR THEN the Dependabot System SHALL assign configured assignees automatically

### Requirement 5: CodeRabbit Configuration Enhancement

**User Story:** As a developer, I want CodeRabbit to provide more comprehensive reviews with security focus, so that I can catch issues earlier in the development cycle.

#### Acceptance Criteria

1. WHEN CodeRabbit reviews Python source files THEN the CodeRabbit System SHALL check for hardcoded secrets and SQL injection vulnerabilities
2. WHEN CodeRabbit reviews test files THEN the CodeRabbit System SHALL verify absence of sensitive data in fixtures
3. WHEN CodeRabbit reviews Terraform files THEN the CodeRabbit System SHALL check for hardcoded secrets and encryption configuration
4. WHEN CodeRabbit processes files THEN the CodeRabbit System SHALL exclude `.hypothesis/` and `htmlcov/` directories from review
5. WHEN CodeRabbit generates reviews THEN the CodeRabbit System SHALL enable knowledge base learnings with auto scope

### Requirement 6: Security Workflow Hardening

**User Story:** As a security engineer, I want the security workflow to be more robust, so that I can ensure consistent security scanning across all code changes.

#### Acceptance Criteria

1. WHEN the Bandit SAST job executes THEN the Security System SHALL complete within the configured timeout
2. WHEN the Trivy scan job executes THEN the Security System SHALL use a pinned version and complete within the configured timeout
3. WHEN the dependency review job executes THEN the Security System SHALL complete within the configured timeout
4. WHEN the SBOM generation job executes THEN the Security System SHALL use a pinned version and complete within the configured timeout
5. WHEN the secrets scan job executes THEN the Security System SHALL use a pinned version and complete within the configured timeout
