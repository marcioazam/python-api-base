# Configuration System

## Overview

O sistema de configuração utiliza Pydantic Settings para validação e carregamento de configurações a partir de variáveis de ambiente e arquivos `.env`.

## Settings Structure

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        case_sensitive=False,
    )
    
    # Application
    app_name: str = "Python API Base"
    debug: bool = False
    version: str = "1.0.0"
    
    # Nested settings
    database: DatabaseSettings
    security: SecuritySettings
    observability: ObservabilitySettings
```

## Configuration Classes

### DatabaseSettings

```python
class DatabaseSettings(BaseSettings):
    url: str = "postgresql+asyncpg://localhost/mydb"
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    echo: bool = False
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | `str` | - | PostgreSQL connection string |
| `pool_size` | `int` | 10 | Connection pool size |
| `max_overflow` | `int` | 20 | Extra connections allowed |
| `pool_timeout` | `int` | 30 | Timeout to get connection |
| `echo` | `bool` | False | Log SQL queries |

### SecuritySettings

```python
class SecuritySettings(BaseSettings):
    secret_key: SecretStr
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    cors_origins: list[str] = ["*"]
    rate_limit: str = "100/minute"
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `secret_key` | `SecretStr` | - | JWT signing key (min 32 chars) |
| `algorithm` | `str` | HS256 | JWT algorithm |
| `access_token_expire_minutes` | `int` | 30 | Access token TTL |
| `refresh_token_expire_days` | `int` | 7 | Refresh token TTL |
| `cors_origins` | `list[str]` | ["*"] | Allowed CORS origins |
| `rate_limit` | `str` | 100/minute | Rate limit config |

### ObservabilitySettings

```python
class ObservabilitySettings(BaseSettings):
    log_level: str = "INFO"
    log_format: str = "json"
    otlp_endpoint: str | None = None
    service_name: str = "python-api-base"
```

## Environment Variables

```bash
# .env file
APP_NAME=My API
DEBUG=false

# Nested with double underscore
DATABASE__URL=postgresql+asyncpg://user:pass@localhost/db
DATABASE__POOL_SIZE=20

SECURITY__SECRET_KEY=your-secret-key-at-least-32-characters
SECURITY__CORS_ORIGINS=["http://localhost:3000"]

OBSERVABILITY__LOG_LEVEL=DEBUG
OBSERVABILITY__OTLP_ENDPOINT=http://jaeger:4317
```

## Usage

```python
from functools import lru_cache
from core.config import Settings

@lru_cache
def get_settings() -> Settings:
    return Settings()

# In application code
settings = get_settings()
db_url = settings.database.url
secret = settings.security.secret_key.get_secret_value()
```

## Validation

Pydantic validates all settings on startup:

```python
# Invalid configuration raises ValidationError
SECURITY__SECRET_KEY=short  # Error: min 32 chars
DATABASE__POOL_SIZE=abc     # Error: not an integer
```

## Testing

```python
def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE__URL", "postgresql://test")
    settings = Settings()
    assert "test" in settings.database.url
```
