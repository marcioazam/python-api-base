# Contributing Guide

## Overview

Thank you for contributing to Python API Base! This guide covers the contribution process and standards.

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker & Docker Compose
- Git

### Setup

```bash
# Clone repository
git clone https://github.com/example/python-api-base.git
cd python-api-base

# Install dependencies
uv sync --dev

# Setup pre-commit hooks
uv run pre-commit install

# Copy environment file
cp .env.example .env
```

## Code Style

### Python Style Guide

We follow PEP 8 with these additions:

| Rule | Value |
|------|-------|
| Line length | 120 characters |
| Indentation | 4 spaces |
| Quotes | Double quotes for strings |
| Imports | Sorted with isort |
| Type hints | Required for public APIs |

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Files | kebab-case | `user-service.py` |
| Classes | PascalCase | `UserService` |
| Functions | snake_case | `get_user_by_id` |
| Constants | UPPER_SNAKE | `MAX_RETRIES` |
| Variables | snake_case | `user_count` |

### Code Organization

```python
# Standard library imports
import asyncio
from datetime import datetime

# Third-party imports
from fastapi import Depends
from pydantic import BaseModel

# Local imports
from src.core.config import Settings
from src.domain.users import User
```

## Commit Conventions

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation |
| `style` | Formatting |
| `refactor` | Code restructuring |
| `test` | Adding tests |
| `chore` | Maintenance |

### Examples

```bash
# Feature
feat(users): add email verification endpoint

# Bug fix
fix(auth): handle expired refresh tokens correctly

# Documentation
docs(api): update authentication examples

# Refactor
refactor(cache): extract cache key builder
```

## Pull Request Process

### 1. Create Branch

```bash
# Feature
git checkout -b feature/user-verification

# Bug fix
git checkout -b fix/auth-token-expiry

# Documentation
git checkout -b docs/api-examples
```

### 2. Make Changes

- Write code following style guide
- Add/update tests
- Update documentation
- Run checks locally

### 3. Run Checks

```bash
# Format code
uv run ruff format .

# Lint
uv run ruff check .

# Type check
uv run mypy src/

# Run tests
uv run pytest

# All checks
uv run pre-commit run --all-files
```

### 4. Create PR

- Use descriptive title
- Fill out PR template
- Link related issues
- Request reviewers

### PR Template

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] All tests passing

## Checklist
- [ ] Code follows style guide
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
```

### 5. Review Process

1. Automated checks must pass
2. At least 1 approval required
3. Address review comments
4. Squash and merge

## Testing Requirements

### Unit Tests

- Required for all new code
- Minimum 80% coverage
- Use pytest fixtures

### Property-Based Tests

- Required for domain logic
- Use Hypothesis library
- Tag with feature/property

### Integration Tests

- Required for API endpoints
- Required for database operations
- Use test fixtures

## Documentation Requirements

### When to Update Docs

- New features
- API changes
- Configuration changes
- Breaking changes

### Documentation Types

| Type | Location | When |
|------|----------|------|
| API docs | `docs/api/` | New endpoints |
| Layer docs | `docs/layers/` | New components |
| Guides | `docs/guides/` | New patterns |
| ADRs | `docs/adr/` | Architecture decisions |

### ADR Template

```markdown
# ADR-XXX: Title

## Status
Proposed

## Context
Why is this decision needed?

## Decision
What was decided?

## Consequences
What are the implications?
```

## Release Process

### Versioning

We use [Semantic Versioning](https://semver.org/):

- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

### Release Steps

1. Update CHANGELOG.md
2. Update version in pyproject.toml
3. Create release PR
4. Merge to main
5. Tag release
6. Publish to PyPI

## Getting Help

- GitHub Issues: Bug reports, feature requests
- Discussions: Questions, ideas
- Slack: #python-api-base

## Code of Conduct

Be respectful, inclusive, and constructive. See CODE_OF_CONDUCT.md for details.
