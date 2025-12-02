# Getting Started

## Pré-requisitos

### Software Necessário

| Software | Versão | Obrigatório |
|----------|--------|-------------|
| Python | 3.12+ | ✅ |
| uv | latest | Recomendado |
| Docker | 24+ | ✅ |
| Docker Compose | 2.0+ | ✅ |
| PostgreSQL | 15+ | ✅ |
| Redis | 7+ | Opcional |

### Verificar Instalação

```bash
python --version    # Python 3.12+
uv --version        # uv 0.4+
docker --version    # Docker 24+
docker compose version  # Docker Compose 2.0+
```

---

## Instalação

### 1. Clonar Repositório

```bash
git clone https://github.com/example/python-api-base.git
cd python-api-base
```

### 2. Instalar Dependências

**Com uv (recomendado):**
```bash
uv sync --dev
```

**Com pip:**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate     # Windows

pip install -e ".[dev]"
```

### 3. Configurar Ambiente

```bash
cp .env.example .env
```

Edite o arquivo `.env`:

```bash
# Obrigatório: Gere uma chave segura
SECURITY__SECRET_KEY=your-super-secret-key-at-least-32-characters

# Database
DATABASE__URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mydb

# Opcional: Redis
REDIS__ENABLED=true
REDIS__URL=redis://localhost:6379/0
```

### 4. Iniciar Infraestrutura

```bash
# Iniciar PostgreSQL e Redis
docker compose -f deployments/docker/docker-compose.dev.yml up -d
```

### 5. Executar Migrations

```bash
# Criar banco de dados
alembic upgrade head
```

### 6. Iniciar API

```bash
# Com uv
uv run uvicorn src.main:app --reload

# Com Python
python -m uvicorn src.main:app --reload
```

---

## Verificar Instalação

### Health Check

```bash
curl http://localhost:8000/health/live
```

**Resposta esperada:**
```json
{"status": "healthy"}
```

### Documentação

Acesse no navegador:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Estrutura do Projeto

```
python-api-base/
├── src/                    # Código fonte
│   ├── core/              # Kernel (config, DI, protocols)
│   ├── domain/            # Entidades e regras de negócio
│   ├── application/       # Use cases e DTOs
│   ├── infrastructure/    # Implementações (DB, cache, etc)
│   ├── interface/         # API (routers, middleware)
│   └── main.py            # Entry point
├── tests/                  # Testes
├── docs/                   # Documentação
├── deployments/            # Docker, K8s, Terraform
├── scripts/                # Scripts utilitários
├── alembic/                # Migrations
├── .env.example            # Template de configuração
├── pyproject.toml          # Dependências
└── README.md
```

---

## Primeiro Endpoint

### 1. Criar Entidade

`src/domain/products/entities.py`:
```python
from sqlmodel import SQLModel, Field
from ulid import ULID

class Product(SQLModel, table=True):
    __tablename__ = "products"
    
    id: str = Field(default_factory=lambda: str(ULID()), primary_key=True)
    name: str = Field(max_length=100)
    price: float = Field(ge=0)
    description: str | None = Field(default=None, max_length=500)
```

### 2. Criar DTOs

`src/application/products/dtos.py`:
```python
from pydantic import BaseModel, Field

class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(ge=0)
    description: str | None = None

class ProductResponse(BaseModel):
    id: str
    name: str
    price: float
    description: str | None
    
    model_config = {"from_attributes": True}
```

### 3. Criar Router

`src/interface/v1/products.py`:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from domain.products.entities import Product
from application.products.dtos import ProductCreate, ProductResponse
from infrastructure.db.session import get_session

router = APIRouter(prefix="/products", tags=["Products"])

@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(
    data: ProductCreate,
    session: AsyncSession = Depends(get_session),
) -> ProductResponse:
    product = Product(**data.model_dump())
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return ProductResponse.model_validate(product)

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    session: AsyncSession = Depends(get_session),
) -> ProductResponse:
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    return ProductResponse.model_validate(product)
```

### 4. Registrar Router

`src/main.py`:
```python
from interface.v1.products import router as products_router

# Adicionar no create_app()
app.include_router(products_router, prefix="/api/v1")
```

### 5. Criar Migration

```bash
alembic revision --autogenerate -m "Add products table"
alembic upgrade head
```

### 6. Testar

```bash
# Criar produto
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Product", "price": 99.99}'

# Buscar produto
curl http://localhost:8000/api/v1/products/{id}
```

---

## Testes

### Executar Todos os Testes

```bash
# Com uv
uv run pytest

# Com pytest diretamente
pytest
```

### Testes por Tipo

```bash
# Unitários
pytest tests/unit/

# Integração
pytest tests/integration/

# Property-based
pytest tests/properties/

# Com cobertura
pytest --cov=src --cov-report=html
```

### Testes Específicos

```bash
# Arquivo específico
pytest tests/unit/test_auth.py

# Teste específico
pytest tests/unit/test_auth.py::test_jwt_creation

# Por marcador
pytest -m "unit"
pytest -m "integration"
pytest -m "property"
```

---

## Comandos Úteis

### Desenvolvimento

```bash
# Iniciar com reload
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy src/

# Todas as verificações
uv run pre-commit run --all-files
```

### Database

```bash
# Criar migration
alembic revision --autogenerate -m "Description"

# Aplicar migrations
alembic upgrade head

# Reverter última migration
alembic downgrade -1

# Ver histórico
alembic history
```

### Docker

```bash
# Iniciar infraestrutura
docker compose -f deployments/docker/docker-compose.dev.yml up -d

# Parar
docker compose -f deployments/docker/docker-compose.dev.yml down

# Ver logs
docker compose -f deployments/docker/docker-compose.dev.yml logs -f

# Rebuild
docker compose -f deployments/docker/docker-compose.dev.yml up -d --build
```

---

## Próximos Passos

1. **Leia a documentação:**
   - [Arquitetura](architecture.md)
   - [Componentes](components.md)
   - [Configuração](configuration.md)

2. **Explore os exemplos:**
   - `src/interface/v1/examples.py`
   - `src/domain/examples/`

3. **Configure autenticação:**
   - [API Security](api/security.md)

4. **Deploy:**
   - [Deployment Guide](deployment.md)

---

## Troubleshooting

### Erro de Conexão com Database

```
sqlalchemy.exc.OperationalError: connection refused
```

**Solução:**
```bash
# Verificar se PostgreSQL está rodando
docker ps | grep postgres

# Iniciar se necessário
docker compose -f deployments/docker/docker-compose.dev.yml up -d postgres
```

### Erro de Secret Key

```
pydantic_core._pydantic_core.ValidationError: secret_key
```

**Solução:**
```bash
# Gerar chave segura
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Adicionar ao .env
SECURITY__SECRET_KEY=<chave_gerada>
```

### Erro de Importação

```
ModuleNotFoundError: No module named 'core'
```

**Solução:**
```bash
# Verificar PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"

# Ou instalar em modo editável
pip install -e .
```

### Porta em Uso

```
OSError: [Errno 98] Address already in use
```

**Solução:**
```bash
# Encontrar processo
lsof -i :8000

# Matar processo
kill -9 <PID>

# Ou usar outra porta
uvicorn src.main:app --port 8001
```
