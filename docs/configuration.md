# Configuração do Sistema

## Visão Geral

O Python API Base utiliza Pydantic Settings para gerenciamento de configurações, suportando variáveis de ambiente e arquivos `.env`.

## Estrutura de Configuração

```python
Settings
├── app_name: str           # Nome da aplicação
├── debug: bool             # Modo debug
├── version: str            # Versão da API
├── api_prefix: str         # Prefixo das rotas
├── database: DatabaseSettings
├── security: SecuritySettings
├── redis: RedisSettings
└── observability: ObservabilitySettings
```

---

## Variáveis de Ambiente

### Aplicação

| Variável | Tipo | Default | Descrição |
|----------|------|---------|-----------|
| `APP_NAME` | string | "My API" | Nome da aplicação |
| `DEBUG` | bool | false | Modo debug |
| `VERSION` | string | "0.1.0" | Versão da API |
| `API_PREFIX` | string | "/api/v1" | Prefixo das rotas |

### Database

| Variável | Tipo | Default | Descrição |
|----------|------|---------|-----------|
| `DATABASE__URL` | string | - | Connection string PostgreSQL |
| `DATABASE__POOL_SIZE` | int | 10 | Tamanho do pool |
| `DATABASE__MAX_OVERFLOW` | int | 20 | Conexões extras |
| `DATABASE__POOL_TIMEOUT` | int | 30 | Timeout do pool (s) |
| `DATABASE__ECHO` | bool | false | Log de queries SQL |

**Exemplo:**
```bash
DATABASE__URL=postgresql+asyncpg://user:pass@localhost:5432/mydb
DATABASE__POOL_SIZE=20
DATABASE__MAX_OVERFLOW=30
```

### Security

| Variável | Tipo | Default | Descrição |
|----------|------|---------|-----------|
| `SECURITY__SECRET_KEY` | string | - | Chave JWT (min 32 chars) |
| `SECURITY__CORS_ORIGINS` | list | ["*"] | Origens CORS |
| `SECURITY__RATE_LIMIT` | string | "100/minute" | Rate limit |
| `SECURITY__ALGORITHM` | string | "HS256" | Algoritmo JWT |
| `SECURITY__ACCESS_TOKEN_EXPIRE_MINUTES` | int | 30 | Expiração access token |
| `SECURITY__CSP` | string | "default-src 'self'" | Content-Security-Policy |
| `SECURITY__PERMISSIONS_POLICY` | string | "geolocation=()..." | Permissions-Policy |

**Exemplo:**
```bash
SECURITY__SECRET_KEY=your-super-secret-key-at-least-32-characters
SECURITY__CORS_ORIGINS=["https://app.example.com","https://admin.example.com"]
SECURITY__RATE_LIMIT=100/minute
SECURITY__ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Redis

| Variável | Tipo | Default | Descrição |
|----------|------|---------|-----------|
| `REDIS__URL` | string | "redis://localhost:6379/0" | URL Redis |
| `REDIS__ENABLED` | bool | false | Habilitar Redis |
| `REDIS__TOKEN_TTL` | int | 604800 | TTL de tokens (s) |

**Exemplo:**
```bash
REDIS__URL=redis://localhost:6379/0
REDIS__ENABLED=true
REDIS__TOKEN_TTL=604800
```

### Observability

#### Logging

| Variável | Tipo | Default | Descrição |
|----------|------|---------|-----------|
| `OBSERVABILITY__LOG_LEVEL` | string | "INFO" | Nível de log |
| `OBSERVABILITY__LOG_FORMAT` | string | "json" | Formato (json/console) |
| `OBSERVABILITY__LOG_ECS_FORMAT` | bool | true | Formato ECS |
| `OBSERVABILITY__LOG_PII_REDACTION` | bool | true | Redação de PII |

#### OpenTelemetry

| Variável | Tipo | Default | Descrição |
|----------|------|---------|-----------|
| `OBSERVABILITY__OTLP_ENDPOINT` | string | null | Endpoint OTLP |
| `OBSERVABILITY__SERVICE_NAME` | string | "python-api-base" | Nome do serviço |
| `OBSERVABILITY__SERVICE_VERSION` | string | "1.0.0" | Versão do serviço |
| `OBSERVABILITY__ENVIRONMENT` | string | "development" | Ambiente |
| `OBSERVABILITY__ENABLE_TRACING` | bool | true | Habilitar tracing |
| `OBSERVABILITY__ENABLE_METRICS` | bool | true | Habilitar métricas |

#### Elasticsearch

| Variável | Tipo | Default | Descrição |
|----------|------|---------|-----------|
| `OBSERVABILITY__ELASTICSEARCH_ENABLED` | bool | false | Habilitar ES |
| `OBSERVABILITY__ELASTICSEARCH_HOSTS` | list | ["http://localhost:9200"] | Hosts ES |
| `OBSERVABILITY__ELASTICSEARCH_INDEX_PREFIX` | string | "logs-python-api-base" | Prefixo de índice |
| `OBSERVABILITY__ELASTICSEARCH_USERNAME` | string | null | Usuário |
| `OBSERVABILITY__ELASTICSEARCH_PASSWORD` | string | null | Senha |
| `OBSERVABILITY__ELASTICSEARCH_API_KEY` | string | null | API Key |
| `OBSERVABILITY__ELASTICSEARCH_USE_SSL` | bool | false | Usar SSL |
| `OBSERVABILITY__ELASTICSEARCH_VERIFY_CERTS` | bool | true | Verificar certs |
| `OBSERVABILITY__ELASTICSEARCH_BATCH_SIZE` | int | 100 | Tamanho do batch |
| `OBSERVABILITY__ELASTICSEARCH_FLUSH_INTERVAL` | float | 5.0 | Intervalo de flush |

#### Kafka

| Variável | Tipo | Default | Descrição |
|----------|------|---------|-----------|
| `OBSERVABILITY__KAFKA_ENABLED` | bool | false | Habilitar Kafka |
| `OBSERVABILITY__KAFKA_BOOTSTRAP_SERVERS` | list | ["localhost:9092"] | Servidores |
| `OBSERVABILITY__KAFKA_CLIENT_ID` | string | "python-api-base" | Client ID |
| `OBSERVABILITY__KAFKA_GROUP_ID` | string | "python-api-base-group" | Group ID |
| `OBSERVABILITY__KAFKA_AUTO_OFFSET_RESET` | string | "earliest" | Offset reset |
| `OBSERVABILITY__KAFKA_ENABLE_AUTO_COMMIT` | bool | true | Auto commit |
| `OBSERVABILITY__KAFKA_SECURITY_PROTOCOL` | string | "PLAINTEXT" | Protocolo |
| `OBSERVABILITY__KAFKA_SASL_MECHANISM` | string | null | SASL mechanism |
| `OBSERVABILITY__KAFKA_SASL_USERNAME` | string | null | SASL username |
| `OBSERVABILITY__KAFKA_SASL_PASSWORD` | string | null | SASL password |

#### ScyllaDB

| Variável | Tipo | Default | Descrição |
|----------|------|---------|-----------|
| `OBSERVABILITY__SCYLLADB_ENABLED` | bool | false | Habilitar ScyllaDB |
| `OBSERVABILITY__SCYLLADB_HOSTS` | list | ["localhost"] | Hosts |
| `OBSERVABILITY__SCYLLADB_PORT` | int | 9042 | Porta |
| `OBSERVABILITY__SCYLLADB_KEYSPACE` | string | "python_api_base" | Keyspace |
| `OBSERVABILITY__SCYLLADB_USERNAME` | string | null | Usuário |
| `OBSERVABILITY__SCYLLADB_PASSWORD` | string | null | Senha |
| `OBSERVABILITY__SCYLLADB_PROTOCOL_VERSION` | int | 4 | Versão do protocolo |
| `OBSERVABILITY__SCYLLADB_CONNECT_TIMEOUT` | int | 10 | Timeout de conexão |
| `OBSERVABILITY__SCYLLADB_REQUEST_TIMEOUT` | int | 30 | Timeout de request |

#### Prometheus

| Variável | Tipo | Default | Descrição |
|----------|------|---------|-----------|
| `OBSERVABILITY__PROMETHEUS_ENABLED` | bool | true | Habilitar Prometheus |
| `OBSERVABILITY__PROMETHEUS_ENDPOINT` | string | "/metrics" | Endpoint |
| `OBSERVABILITY__PROMETHEUS_INCLUDE_IN_SCHEMA` | bool | false | Incluir no schema |
| `OBSERVABILITY__PROMETHEUS_NAMESPACE` | string | "python_api" | Namespace |
| `OBSERVABILITY__PROMETHEUS_SUBSYSTEM` | string | "" | Subsystem |

#### Redis (Observability)

| Variável | Tipo | Default | Descrição |
|----------|------|---------|-----------|
| `OBSERVABILITY__REDIS_ENABLED` | bool | false | Habilitar Redis |
| `OBSERVABILITY__REDIS_URL` | string | "redis://localhost:6379/0" | URL |
| `OBSERVABILITY__REDIS_POOL_SIZE` | int | 10 | Pool size |
| `OBSERVABILITY__REDIS_KEY_PREFIX` | string | "api" | Prefixo de chaves |

#### MinIO

| Variável | Tipo | Default | Descrição |
|----------|------|---------|-----------|
| `OBSERVABILITY__MINIO_ENABLED` | bool | false | Habilitar MinIO |
| `OBSERVABILITY__MINIO_ENDPOINT` | string | "localhost:9000" | Endpoint |
| `OBSERVABILITY__MINIO_ACCESS_KEY` | string | null | Access key |
| `OBSERVABILITY__MINIO_SECRET_KEY` | string | null | Secret key |
| `OBSERVABILITY__MINIO_BUCKET` | string | "uploads" | Bucket |
| `OBSERVABILITY__MINIO_SECURE` | bool | false | Usar HTTPS |

#### RabbitMQ

| Variável | Tipo | Default | Descrição |
|----------|------|---------|-----------|
| `OBSERVABILITY__RABBITMQ_ENABLED` | bool | false | Habilitar RabbitMQ |
| `OBSERVABILITY__RABBITMQ_HOST` | string | "localhost" | Host |
| `OBSERVABILITY__RABBITMQ_PORT` | int | 5672 | Porta |
| `OBSERVABILITY__RABBITMQ_USERNAME` | string | null | Usuário |
| `OBSERVABILITY__RABBITMQ_PASSWORD` | string | null | Senha |
| `OBSERVABILITY__RABBITMQ_VIRTUAL_HOST` | string | "/" | Virtual host |

#### Keycloak

| Variável | Tipo | Default | Descrição |
|----------|------|---------|-----------|
| `OBSERVABILITY__KEYCLOAK_ENABLED` | bool | false | Habilitar Keycloak |
| `OBSERVABILITY__KEYCLOAK_SERVER_URL` | string | "http://localhost:8080" | URL |
| `OBSERVABILITY__KEYCLOAK_REALM` | string | "master" | Realm |
| `OBSERVABILITY__KEYCLOAK_CLIENT_ID` | string | "python-api" | Client ID |
| `OBSERVABILITY__KEYCLOAK_CLIENT_SECRET` | string | null | Client secret |

---

## Arquivo .env

### Exemplo Completo

```bash
# Application
APP_NAME=My API
DEBUG=false
VERSION=1.0.0
API_PREFIX=/api/v1

# Database
DATABASE__URL=postgresql+asyncpg://user:password@localhost:5432/mydb
DATABASE__POOL_SIZE=20
DATABASE__MAX_OVERFLOW=30
DATABASE__POOL_TIMEOUT=30
DATABASE__ECHO=false

# Security
SECURITY__SECRET_KEY=your-super-secret-key-at-least-32-characters-long
SECURITY__CORS_ORIGINS=["https://app.example.com"]
SECURITY__RATE_LIMIT=100/minute
SECURITY__ALGORITHM=HS256
SECURITY__ACCESS_TOKEN_EXPIRE_MINUTES=30

# Redis
REDIS__URL=redis://localhost:6379/0
REDIS__ENABLED=true
REDIS__TOKEN_TTL=604800

# Observability - Logging
OBSERVABILITY__LOG_LEVEL=INFO
OBSERVABILITY__LOG_FORMAT=json
OBSERVABILITY__LOG_ECS_FORMAT=true
OBSERVABILITY__LOG_PII_REDACTION=true

# Observability - OpenTelemetry
OBSERVABILITY__OTLP_ENDPOINT=http://localhost:4317
OBSERVABILITY__SERVICE_NAME=my-api
OBSERVABILITY__SERVICE_VERSION=1.0.0
OBSERVABILITY__ENVIRONMENT=production
OBSERVABILITY__ENABLE_TRACING=true
OBSERVABILITY__ENABLE_METRICS=true

# Observability - Elasticsearch
OBSERVABILITY__ELASTICSEARCH_ENABLED=true
OBSERVABILITY__ELASTICSEARCH_HOSTS=["http://localhost:9200"]
OBSERVABILITY__ELASTICSEARCH_INDEX_PREFIX=logs-my-api
OBSERVABILITY__ELASTICSEARCH_USERNAME=elastic
OBSERVABILITY__ELASTICSEARCH_PASSWORD=changeme

# Observability - Kafka
OBSERVABILITY__KAFKA_ENABLED=true
OBSERVABILITY__KAFKA_BOOTSTRAP_SERVERS=["localhost:9092"]
OBSERVABILITY__KAFKA_CLIENT_ID=my-api
OBSERVABILITY__KAFKA_GROUP_ID=my-api-group

# Observability - Prometheus
OBSERVABILITY__PROMETHEUS_ENABLED=true
OBSERVABILITY__PROMETHEUS_ENDPOINT=/metrics
OBSERVABILITY__PROMETHEUS_NAMESPACE=my_api

# Observability - Redis
OBSERVABILITY__REDIS_ENABLED=true
OBSERVABILITY__REDIS_URL=redis://localhost:6379/1
OBSERVABILITY__REDIS_POOL_SIZE=10
OBSERVABILITY__REDIS_KEY_PREFIX=myapi

# Observability - MinIO
OBSERVABILITY__MINIO_ENABLED=true
OBSERVABILITY__MINIO_ENDPOINT=localhost:9000
OBSERVABILITY__MINIO_ACCESS_KEY=minioadmin
OBSERVABILITY__MINIO_SECRET_KEY=minioadmin
OBSERVABILITY__MINIO_BUCKET=uploads
OBSERVABILITY__MINIO_SECURE=false

# Observability - RabbitMQ
OBSERVABILITY__RABBITMQ_ENABLED=true
OBSERVABILITY__RABBITMQ_HOST=localhost
OBSERVABILITY__RABBITMQ_PORT=5672
OBSERVABILITY__RABBITMQ_USERNAME=guest
OBSERVABILITY__RABBITMQ_PASSWORD=guest
OBSERVABILITY__RABBITMQ_VIRTUAL_HOST=/
```

---

## Validações

### Secret Key

A chave secreta deve ter no mínimo 32 caracteres (256 bits):

```python
@field_validator("secret_key")
@classmethod
def validate_secret_entropy(cls, v: SecretStr) -> SecretStr:
    secret = v.get_secret_value()
    if len(secret) < 32:
        raise ValueError(
            "Secret key must be at least 32 characters (256 bits)"
        )
    return v
```

### Rate Limit

O formato deve ser `number/unit`:

```python
# Válidos
"100/minute"
"10/second"
"1000/hour"
"10000/day"

# Inválidos
"100"
"100/min"
"hundred/minute"
```

### CORS Origins

Wildcard `*` gera warning em produção:

```python
@field_validator("cors_origins")
@classmethod
def warn_wildcard_cors(cls, v: list[str]) -> list[str]:
    if "*" in v:
        env = os.getenv("ENVIRONMENT", "").lower()
        if env == "production":
            logger.warning(
                "SECURITY WARNING: Wildcard CORS origin '*' in production"
            )
    return v
```

### Credenciais Obrigatórias

Quando serviços são habilitados, credenciais são obrigatórias:

```python
@model_validator(mode="after")
def validate_credentials(self) -> Self:
    if self.minio_enabled:
        if not self.minio_access_key or not self.minio_secret_key:
            raise ValueError("MinIO credentials required when enabled")
    
    if self.rabbitmq_enabled:
        if not self.rabbitmq_username or not self.rabbitmq_password:
            raise ValueError("RabbitMQ credentials required when enabled")
    
    return self
```

---

## Ambientes

### Development

```bash
# .env.development
DEBUG=true
OBSERVABILITY__LOG_LEVEL=DEBUG
OBSERVABILITY__LOG_FORMAT=console
DATABASE__ECHO=true
```

### Staging

```bash
# .env.staging
DEBUG=false
OBSERVABILITY__LOG_LEVEL=INFO
OBSERVABILITY__LOG_FORMAT=json
OBSERVABILITY__ENVIRONMENT=staging
```

### Production

```bash
# .env.production
DEBUG=false
OBSERVABILITY__LOG_LEVEL=WARNING
OBSERVABILITY__LOG_FORMAT=json
OBSERVABILITY__ENVIRONMENT=production
OBSERVABILITY__LOG_PII_REDACTION=true
```

---

## Carregamento

### Ordem de Precedência

1. Variáveis de ambiente do sistema
2. Arquivo `.env`
3. Valores default

### Uso no Código

```python
from core.config import get_settings

settings = get_settings()

# Acessar configurações
print(settings.app_name)
print(settings.database.url)
print(settings.security.secret_key.get_secret_value())
```

### Cache de Settings

Settings são cacheados via `@lru_cache`:

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```

Para recarregar em testes:

```python
get_settings.cache_clear()
```
