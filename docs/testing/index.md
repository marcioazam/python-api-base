# Testing Guide

## Overview

O Python API Base utiliza uma estratégia de testes em múltiplas camadas: unit, integration, property-based e e2e.

## Testing Pyramid

```
        /\
       /  \     E2E Tests (few)
      /----\    
     /      \   Integration Tests
    /--------\  
   /          \ Unit Tests (many)
  /------------\
```

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── factories/               # Test factories
├── unit/                    # Unit tests
│   ├── domain/
│   ├── application/
│   └── infrastructure/
├── integration/             # Integration tests
│   ├── api/
│   └── repositories/
├── properties/              # Property-based tests
└── e2e/                     # End-to-end tests
```

## Test Types

| Type | Purpose | Documentation |
|------|---------|---------------|
| Unit | Test isolated components | [unit-testing.md](unit-testing.md) |
| Integration | Test component interactions | [integration-testing.md](integration-testing.md) |
| Property | Test invariants with random data | [property-testing.md](property-testing.md) |
| E2E | Test complete flows | [e2e-testing.md](e2e-testing.md) |

## Quick Start

```bash
# Run all tests
pytest

# Run by type
pytest tests/unit/
pytest tests/integration/
pytest tests/properties/

# With coverage
pytest --cov=src --cov-report=html

# Parallel execution
pytest -n auto
```

## Coverage Requirements

- Minimum coverage: **80%**
- Branch coverage: **75%**

## Markers

```python
@pytest.mark.unit
@pytest.mark.integration
@pytest.mark.property
@pytest.mark.e2e
@pytest.mark.slow
```

## Related Documentation

- [Test Fixtures](test-fixtures.md)
- [Manual API Testing](manual-api-testing.md)
