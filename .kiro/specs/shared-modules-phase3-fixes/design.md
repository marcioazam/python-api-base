# Design Document

## Overview

Este documento descreve o design para correção de 23 issues identificados no code review dos módulos shared phase 2. As correções são organizadas em três categorias: Segurança (P0), Performance (P1) e Qualidade de Código (P2).

## Architecture

A arquitetura existente será mantida. As correções são incrementais e não alteram a estrutura dos módulos:

```
src/my_api/shared/
├── http2_config/      # Extrair constantes
├── lazy/              # Adicionar limites de cache
├── memory_profiler/   # Substituir print por logging
├── metrics_dashboard/ # Corrigir timezone
├── multitenancy/      # Corrigir SQLAlchemy boolean
├── mutation_testing/  # Adicionar encoding
├── oauth2/            # Timeout configurável
├── protocols/         # Melhorar docstrings
├── query_analyzer/    # Validação de input
└── query_builder/     # Escape de regex
```

## Components and Interfaces

### 1. Memory Profiler - Logging Handler

```python
# memory_profiler/service.py
import logging

logger = logging.getLogger(__name__)

class LogMemoryAlertHandler:
    """Handler that logs memory alerts using Python logging."""
    
    SEVERITY_MAP = {
        MemoryAlertSeverity.CRITICAL: logging.ERROR,
        MemoryAlertSeverity.WARNING: logging.WARNING,
        MemoryAlertSeverity.INFO: logging.INFO,
    }
    
    async def handle(self, alert: MemoryAlert) -> None:
        level = self.SEVERITY_MAP.get(alert.severity, logging.WARNING)
        logger.log(
            level,
            "Memory alert: %s - %s (current: %.2f, threshold: %.2f)",
            alert.alert_type.value,
            alert.message,
            alert.current_value,
            alert.threshold,
        )
```

### 2. Query Analyzer - Input Validation

```python
# query_analyzer/constants.py
MAX_QUERY_LENGTH = 10000
ALLOWED_IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
REGEX_TIMEOUT_SECONDS = 1.0

# query_analyzer/service.py
class QueryAnalyzer:
    def analyze_query(self, query: str) -> QueryAnalysis:
        self._validate_query(query)
        # ... existing logic
    
    def _validate_query(self, query: str) -> None:
        if len(query) > MAX_QUERY_LENGTH:
            raise ValueError(f"Query exceeds maximum length of {MAX_QUERY_LENGTH}")
        if not query.strip():
            raise ValueError("Query cannot be empty")
```

### 3. Multitenancy - SQLAlchemy Fix

```python
# multitenancy/service.py
if hasattr(self._model_class, "is_deleted"):
    query = query.where(
        self._model_class.is_deleted.is_(False)
    )
```

### 4. Lazy Loader - Cache Limits

```python
# lazy/loader.py
@dataclass
class BatchLoader(Generic[T]):
    batch_resolver: Callable[[list[str]], Awaitable[dict[str, T]]]
    max_cache_size: int = 10000
    
    async def load_all(self) -> dict[str, T]:
        # ... existing logic
        self._enforce_cache_limit()
        return self._cache
    
    def _enforce_cache_limit(self) -> None:
        if len(self._cache) > self.max_cache_size:
            excess = len(self._cache) - self.max_cache_size
            for key in list(self._cache.keys())[:excess]:
                del self._cache[key]
```

### 5. HTTP/2 Config - Constants

```python
# http2_config/constants.py
"""HTTP/2 Protocol Constants per RFC 7540."""

# Section 6.5.2 - SETTINGS_MAX_CONCURRENT_STREAMS
MAX_CONCURRENT_STREAMS_LIMIT = 2147483647

# Section 6.9.1 - Initial Window Size
MAX_WINDOW_SIZE = 2147483647

# Section 4.2 - Frame Size
MIN_FRAME_SIZE = 16384
MAX_FRAME_SIZE = 16777215

# Section 6.5.2 - SETTINGS_MAX_HEADER_LIST_SIZE
DEFAULT_MAX_HEADER_LIST_SIZE = 8192
```

### 6. OAuth2 - Configurable Timeout

```python
# oauth2/models.py
@dataclass(frozen=True)
class OAuthConfig:
    # ... existing fields
    request_timeout: float = 30.0

# oauth2/base.py
async def exchange_code(self, code: str) -> OAuthTokenResponse:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            self._config.token_url,
            data=data,
            headers=headers,
            timeout=self._config.request_timeout,
        )
```

## Data Models

Não há alterações nos modelos de dados. As correções são comportamentais.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Prework Analysis

1.1 WHEN the LogMemoryAlertHandler receives a memory alert THEN the system SHALL log the alert using Python's logging module
Thoughts: Podemos testar que para qualquer alerta, o logger é chamado com o nível correto
Testable: yes - property

1.2 WHEN a memory alert has severity CRITICAL THEN the system SHALL log at ERROR level
Thoughts: Mapeamento direto de severidade para nível de log, testável com diferentes severidades
Testable: yes - property

2.1 WHEN a query exceeds 10000 characters THEN the QueryAnalyzer SHALL reject it
Thoughts: Para qualquer string maior que 10000 chars, deve lançar ValueError
Testable: yes - property

2.2 WHEN regex operations are performed on user input THEN the system SHALL use timeout-protected matching
Thoughts: Difícil testar timeout sem criar input malicioso específico
Testable: yes - example

3.1 WHEN filtering by is_deleted field THEN the TenantRepository SHALL use is_() method
Thoughts: Verificar que a query gerada usa is_() ao invés de ==
Testable: yes - property

4.1 WHEN BatchLoader cache exceeds max_cache_size THEN the system SHALL evict oldest entries
Thoughts: Para qualquer sequência de adds que exceda o limite, o cache deve ter no máximo max_cache_size
Testable: yes - property

5.1 WHEN LazyProxy.get() is called with timeout THEN the system SHALL respect the timeout
Thoughts: Testar com loader lento e verificar que TimeoutError é lançado
Testable: yes - example

6.1 WHEN a module is loaded THEN it SHALL only import dependencies that are actually used
Thoughts: Verificação estática, não é testável em runtime
Testable: no

7.1 WHEN a datetime default is created THEN the system SHALL use timezone-aware datetime
Thoughts: Para qualquer instância criada, o campo datetime deve ter tzinfo não-None
Testable: yes - property

8.1 WHEN HTTP/2 protocol limits are referenced THEN the system SHALL use named constants
Thoughts: Verificação estática de código, não testável em runtime
Testable: no

9.1 WHEN opening files for reading THEN the system SHALL specify encoding='utf-8'
Thoughts: Verificação estática, mas podemos testar que arquivos são lidos corretamente com UTF-8
Testable: yes - property

10.1 WHEN a module __init__.py is created THEN it SHALL have a specific docstring
Thoughts: Verificação estática de código
Testable: no

### Property Reflection

Após análise, as propriedades 1.1 e 1.2 podem ser combinadas em uma única propriedade que testa o mapeamento de severidade para nível de log.

### Correctness Properties

Property 1: Memory alert logging maps severity to correct log level
*For any* memory alert with any severity level, when handled by LogMemoryAlertHandler, the logger should be called with the corresponding log level (CRITICAL→ERROR, WARNING→WARNING, INFO→INFO)
**Validates: Requirements 1.1, 1.2, 1.3, 1.4**

Property 2: Query length validation rejects oversized queries
*For any* string with length greater than MAX_QUERY_LENGTH, the QueryAnalyzer.analyze_query() should raise ValueError
**Validates: Requirements 2.1**

Property 3: SQLAlchemy boolean filter uses is_() method
*For any* TenantRepository query with is_deleted filter, the generated SQL should use IS FALSE instead of = FALSE
**Validates: Requirements 3.1, 3.2**

Property 4: BatchLoader cache respects size limit
*For any* sequence of entity loads that would exceed max_cache_size, the cache size should never exceed max_cache_size after load_all()
**Validates: Requirements 4.1**

Property 5: Datetime fields are timezone-aware
*For any* newly created Dashboard, MetricPoint, or OAuthState instance, the datetime fields should have tzinfo set to UTC
**Validates: Requirements 7.1, 7.2, 7.3**

Property 6: File operations use UTF-8 encoding
*For any* file read/write operation in MutationScoreTracker, the content should be correctly encoded/decoded as UTF-8
**Validates: Requirements 9.1, 9.2, 9.3**

Property 7: InMemoryStateStore clears expired states
*For any* collection of OAuth states with varying creation times, calling clear_expired() should remove all states older than max_age_seconds and retain all newer states
**Validates: Requirements 4.2**

Property 8: InMemoryMetricsStore respects max_points limit
*For any* sequence of metric recordings that exceeds max_points_per_series, the stored points should never exceed max_points_per_series
**Validates: Requirements 4.3**

Property 9: Query analyzer extracts valid identifiers only
*For any* SQL query, all extracted table and column names should match the pattern ^[a-zA-Z_][a-zA-Z0-9_]*$
**Validates: Requirements 2.4**

Property 10: Regex pattern matching escapes special characters
*For any* LIKE pattern in InMemoryQueryBuilder, special regex characters in the pattern should be properly escaped before matching
**Validates: Requirements 2.2**

Property 11: OAuth timeout is configurable and respected
*For any* OAuthConfig with custom request_timeout, HTTP requests should use that timeout value
**Validates: Requirements 5.2**

Property 12: LazyProxy timeout raises TimeoutError
*For any* LazyProxy with a slow loader and timeout configured, calling get() should raise TimeoutError if loader exceeds timeout
**Validates: Requirements 5.1, 5.3**

## Error Handling

| Error Type | Condition | Response |
|------------|-----------|----------|
| ValueError | Query > MAX_QUERY_LENGTH | Reject with descriptive message |
| ValueError | Empty query | Reject with descriptive message |
| TimeoutError | Async operation exceeds timeout | Raise with operation context |
| UnicodeDecodeError | Invalid UTF-8 in file | Log warning, return empty/default |

## Testing Strategy

### Property-Based Testing

Utilizaremos **Hypothesis** como biblioteca de property-based testing.

Cada property test deve:
1. Gerar inputs aleatórios válidos usando strategies
2. Executar a operação sendo testada
3. Verificar que a propriedade se mantém
4. Rodar mínimo de 100 iterações

### Test Structure

```python
# tests/properties/test_phase3_fixes_properties.py
from hypothesis import given, strategies as st, settings

@settings(max_examples=100)
@given(st.text(min_size=10001, max_size=20000))
def test_query_length_validation(query: str):
    """
    **Feature: shared-modules-phase3-fixes, Property 2: Query length validation**
    **Validates: Requirements 2.1**
    """
    analyzer = QueryAnalyzer()
    with pytest.raises(ValueError):
        analyzer.analyze_query(query)
```

### Unit Tests

Unit tests complementam property tests para:
- Edge cases específicos (query vazia, query exatamente no limite)
- Integração entre componentes
- Comportamento de erro específico
