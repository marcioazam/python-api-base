# Design Document: Alembic Migrations Refactoring

## Overview

Este design documenta as melhorias na configuração do Alembic para suportar auto-discovery de models, validação robusta de configuração, tipos de dados apropriados para valores monetários e integridade referencial nas migrations.

## Architecture

```mermaid
graph TB
    subgraph "Alembic Environment"
        ENV[env.py]
        ENV --> AD[Auto-Discovery Module]
        ENV --> UV[URL Validator]
        AD --> |pkgutil.iter_modules| ENTITIES[my_api.domain.entities.*]
        UV --> |validate| CONFIG[alembic.ini]
        UV --> |priority| ENVVAR[Environment Variables]
    end
    
    subgraph "Migrations"
        M001[001_initial_item_table]
        M001B[001b_add_users_table]
        M002[002_add_roles_tables]
        M003[003_add_audit_logs_table]
        M004[004_migrate_float_to_numeric]
        
        M001 --> M001B
        M001B --> M002
        M002 --> M003
        M003 --> M004
    end
```

## Components and Interfaces

### 1. Model Auto-Discovery (`env.py`)

```python
def import_models() -> None:
    """Auto-import all entity models for metadata registration.
    
    Raises:
        ImportError: If entities package is not found.
    """
```

### 2. URL Validator (`env.py`)

```python
PLACEHOLDER_PATTERNS = [
    "driver://user:pass@localhost/dbname",
    "postgresql://user:password@localhost/db",
]

def get_database_url() -> str:
    """Get and validate database URL from environment or config.
    
    Returns:
        Validated database URL string.
        
    Raises:
        ValueError: If no valid database URL is configured.
    """
```

### 3. New Migration: Users Table (`001b_add_users_table.py`)

```python
def upgrade() -> None:
    """Create users table before roles migration."""
    op.create_table(
        "users",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
```

### 4. Data Migration: Float to Numeric (`004_migrate_float_to_numeric.py`)

```python
def upgrade() -> None:
    """Migrate price and tax columns from Float to Numeric."""
    op.alter_column(
        "items",
        "price",
        type_=sa.Numeric(precision=10, scale=2),
        existing_type=sa.Float(),
    )
```

## Data Models

### Items Table (Updated Schema)

| Column | Old Type | New Type | Notes |
|--------|----------|----------|-------|
| price | Float | Numeric(10,2) | Precisão monetária |
| tax | Float | Numeric(10,2) | Precisão monetária |

### Users Table (New)

| Column | Type | Constraints |
|--------|------|-------------|
| id | String(26) | PK, ULID |
| email | String(255) | NOT NULL, UNIQUE |
| hashed_password | String(255) | NOT NULL |
| is_active | Boolean | NOT NULL, DEFAULT true |
| created_at | DateTime | NOT NULL |
| updated_at | DateTime | NOT NULL |

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Model Auto-Discovery Completeness

*For any* set of Python modules in `my_api/domain/entities/`, calling `import_models()` should result in all modules being imported and their SQLModel classes registered in metadata.

**Validates: Requirements 1.1, 1.2**

### Property 2: URL Resolution Precedence

*For any* configuration state, `get_database_url()` should return:
- `DATABASE__URL` if set, else
- `DATABASE_URL` if set, else
- `alembic.ini` value if valid, else
- raise `ValueError`

**Validates: Requirements 2.2, 2.3**

### Property 3: Invalid URL Rejection

*For any* URL that matches placeholder patterns or is empty, `get_database_url()` should raise `ValueError` with guidance message.

**Validates: Requirements 2.1, 2.4**

### Property 4: Float to Numeric Round-Trip Preservation

*For any* float value within Numeric(10,2) range, converting to Numeric and back should preserve the value within 2 decimal places precision.

**Validates: Requirements 3.3**

### Property 5: Foreign Key Integrity in Migration Chain

*For any* foreign key constraint in migrations, the referenced table must be created in an earlier or same revision.

**Validates: Requirements 4.1, 4.2, 4.3**

## Error Handling

| Scenario | Error Type | Message Pattern |
|----------|------------|-----------------|
| Missing entities package | ImportError | "Cannot find entities package at {path}" |
| No DATABASE_URL configured | ValueError | "DATABASE_URL not configured. Set DATABASE__URL or..." |
| Placeholder URL detected | ValueError | "Invalid placeholder URL detected. Configure..." |
| Migration FK violation | IntegrityError | Handled by database |

## Testing Strategy

### Property-Based Testing

Biblioteca: **Hypothesis** (já presente no projeto conforme `.hypothesis/` folder)

Configuração: Mínimo 100 iterações por property test.

```python
from hypothesis import given, settings, strategies as st

@settings(max_examples=100)
@given(st.lists(st.text(min_size=1, alphabet="abcdefghijklmnopqrstuvwxyz_")))
def test_auto_discovery_completeness(module_names: list[str]) -> None:
    """
    **Feature: alembic-migrations-refactoring, Property 1: Model Auto-Discovery Completeness**
    """
    # Test implementation
```

### Unit Tests

- Validação de URL com diferentes combinações de env vars
- Verificação de tipos de coluna nas migrations
- Teste de ordenação de migrations

### Integration Tests

- Execução de migration chain completa em banco de teste
- Verificação de schema resultante
