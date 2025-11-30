# Implementation Plan

## GitHub CI/CD Hardening

- [x] 1. Create validation infrastructure
  - [x] 1.1 Create GitHub config validation script
    - Create `scripts/validate_github_config.py` with functions to parse and validate workflow files
    - Implement action reference parser to detect branch references
    - Implement timeout checker for all jobs
    - _Requirements: 1.1, 2.1_
  - [x] 1.2 Write property test for action pinning validation
    - **Property 1: No Branch References in Actions**
    - **Validates: Requirements 1.1**
  - [x] 1.3 Write property test for timeout validation
    - **Property 2: All Jobs Have Timeouts**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**
  - [x] 1.4 Write property test for YAML validity
    - **Property 3: YAML Syntax Validity**
    - **Validates: Requirements 1.1, 2.1, 3.1, 4.1, 5.1, 6.1**

- [x] 2. Harden CI workflow
  - [x] 2.1 Add timeouts to ci.yml jobs
    - Add `timeout-minutes: 10` to lint job
    - Add `timeout-minutes: 20` to test job
    - Add `timeout-minutes: 15` to build job
    - _Requirements: 2.1, 2.2, 2.3_
  - [x] 2.2 Pin Trivy action version in ci.yml
    - Change `aquasecurity/trivy-action@master` to `aquasecurity/trivy-action@0.28.0`
    - _Requirements: 1.1, 1.2_

- [x] 3. Harden security workflow
  - [x] 3.1 Add timeouts to security.yml jobs
    - Add `timeout-minutes: 10` to bandit job
    - Add `timeout-minutes: 10` to trivy job
    - Add `timeout-minutes: 5` to dependency-review job
    - Add `timeout-minutes: 10` to sbom job
    - Add `timeout-minutes: 10` to secrets-scan job
    - _Requirements: 2.4, 6.1, 6.2, 6.3, 6.4, 6.5_
  - [x] 3.2 Pin action versions in security.yml
    - Change `aquasecurity/trivy-action@master` to `aquasecurity/trivy-action@0.28.0`
    - Change `anchore/sbom-action@v0` to `anchore/sbom-action@v0.17.8`
    - Change `trufflesecurity/trufflehog@main` to `trufflesecurity/trufflehog@v3.88.0`
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 4. Harden release workflow
  - [x] 4.1 Add timeout and permissions to release.yml
    - Add `timeout-minutes: 30` to release job
    - Add `id-token: write` permission for cosign OIDC
    - _Requirements: 2.5, 3.3_
  - [x] 4.2 Add cosign image signing to release.yml
    - Add cosign-installer step using `sigstore/cosign-installer@v3.7.0`
    - Add image signing step after build-push
    - Enable provenance and sbom in build-push action
    - _Requirements: 3.1, 3.2_
  - [x] 4.3 Update gh-release action version
    - Change `softprops/action-gh-release@v1` to `softprops/action-gh-release@v2`
    - _Requirements: 1.1, 1.5_

- [x] 5. Harden CodeQL workflow
  - [x] 5.1 Add timeout to codeql.yml
    - Add `timeout-minutes: 15` to analyze job
    - _Requirements: 2.6_

- [x] 6. Enhance Dependabot configuration
  - [x] 6.1 Add production dependency group to dependabot.yml
    - Add group for fastapi, pydantic, sqlalchemy, uvicorn, alembic patterns
    - _Requirements: 4.1_
  - [x] 6.2 Add reviewers and assignees to dependabot.yml
    - Add reviewers configuration
    - Add assignees configuration
    - _Requirements: 4.2, 4.3_

- [x] 7. Enhance CodeRabbit configuration
  - [x] 7.1 Add security checks to path instructions
    - Add secrets and SQL injection checks for src/**/*.py
    - Add sensitive data check for tests/**/*.py
    - Add terraform path instructions for secrets and encryption
    - _Requirements: 5.1, 5.2, 5.3_
  - [x] 7.2 Add path filters and knowledge base
    - Add `.hypothesis/` and `htmlcov/` to path_filters exclusions
    - Add knowledge_base configuration with auto scope
    - _Requirements: 5.4, 5.5_

- [x] 8. Checkpoint - Validate all configurations
  - Ensure all tests pass, ask the user if questions arise.
  - Run validation script against all workflow files
  - Verify no branch references remain in actions
  - Verify all jobs have timeouts configured

- [x] 9. Final Checkpoint - Run full validation
  - Ensure all tests pass, ask the user if questions arise.
