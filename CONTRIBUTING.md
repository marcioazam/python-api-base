# Contributing to Python API Base

Obrigado por considerar contribuir para o Python API Base! Este documento fornece diretrizes para contribuições.

## Desenvolvimento

### Pré-requisitos

- Python 3.12+
- uv (gerenciador de pacotes)
- Docker e Docker Compose
- Git

### Setup do Ambiente

```bash
# Clone o repositório
git clone https://github.com/your-org/python-api-base.git
cd python-api-base

# Instale as dependências
uv sync --dev

# Configure as variáveis de ambiente
cp .env.example .env

# Inicie os serviços de infraestrutura
docker-compose up -d postgres redis

# Execute as migrations
alembic upgrade head

# Verifique se tudo está funcionando
pytest
```

### Executando o Projeto

```bash
# Desenvolvimento
uvicorn src.main:app --reload

# Com Docker
docker-compose up
```

## Coding Standards

### Nomenclatura

| Tipo | Convenção | Exemplo |
|------|-----------|---------|
| Arquivos | kebab-case | `user-repository.py` |
| Classes | PascalCase | `UserRepository` |
| Funções/Métodos | snake_case | `get_user_by_id` |
| Variáveis | snake_case | `user_count` |
| Constantes | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| Diretórios | lowercase | `infrastructure` |

### Funções

- Nomes devem começar com verbo: `get_`, `create_`, `delete_`, `validate_`
- Tamanho: 15-20 caracteres idealmente
- Máximo de linhas: 50 (exceção: 75 para casos complexos)
- Máximo de parâmetros: 4 (use objeto para mais)

### Booleans

- Prefixos: `is_`, `has_`, `can_`, `should_`, `will_`
- Exemplos: `is_active`, `has_permission`, `can_edit`

### Arquivos

| Tipo | Linhas Recomendadas | Máximo |
|------|---------------------|--------|
| Arquivo | 200-400 | 500 |
| Função | 10-50 | 75 |
| Classe | 200-300 | 400 |

### Complexidade

- Complexidade ciclomática máxima: 10
- Nesting máximo: 3 níveis (use early returns)

### Imports

Ordem:
1. Standard library
2. Third-party
3. Local

```python
# Standard library
import os
from datetime import datetime

# Third-party
from fastapi import FastAPI
from pydantic import BaseModel

# Local
from core.config import Settings
from domain.users import User
```

### Proibido

- ❌ Emojis em código
- ❌ `console.log` / `print` em produção
- ❌ Código comentado
- ❌ Magic numbers (use constantes)
- ❌ TODO sem ticket
- ❌ Copy-paste (extraia para função)
- ❌ Type assertions sem validação
- ❌ `eval` com input de usuário
- ❌ Credenciais hardcoded

## Git Workflow

### Branches

```
main           # Produção
├── develop    # Desenvolvimento
├── feature/*  # Novas features
├── fix/*      # Bug fixes
├── hotfix/*   # Fixes urgentes em produção
└── release/*  # Preparação de release
```

### Commits

Formato: `<type>(<scope>): <description>`

Tipos:
- `feat`: Nova feature
- `fix`: Bug fix
- `docs`: Documentação
- `style`: Formatação
- `refactor`: Refatoração
- `test`: Testes
- `chore`: Manutenção

Exemplos:
```
feat(users): add email verification
fix(auth): resolve token expiration issue
docs(readme): update installation instructions
```

### Pull Requests

1. Crie uma branch a partir de `develop`
2. Faça suas alterações
3. Escreva/atualize testes
4. Atualize documentação se necessário
5. Abra um PR para `develop`

#### Checklist do PR

- [ ] Código segue os coding standards
- [ ] Testes passando
- [ ] Cobertura >= 80%
- [ ] Documentação atualizada
- [ ] Sem secrets ou credenciais
- [ ] Sem breaking changes (ou documentados)

## Testes

### Requisitos

- Cobertura mínima: 80%
- Todos os testes devem passar

### Executando

```bash
# Todos os testes
pytest

# Com coverage
pytest --cov=src --cov-report=html

# Testes específicos
pytest tests/unit/
pytest tests/integration/
pytest tests/properties/
```

### Tipos de Testes

1. **Unit Tests**: Testam componentes isolados
2. **Integration Tests**: Testam integração entre componentes
3. **Property Tests**: Testam propriedades com Hypothesis
4. **E2E Tests**: Testam fluxos completos

## Code Review

### O que revisamos

- Correção funcional
- Aderência aos coding standards
- Cobertura de testes
- Performance
- Segurança
- Documentação

### Feedback

- Seja construtivo
- Explique o "porquê"
- Sugira alternativas
- Aprove quando estiver bom

## Segurança

### Reportando Vulnerabilidades

Não abra issues públicas para vulnerabilidades de segurança.

Envie um email para: security@example.com

### Práticas

- Nunca commite secrets
- Valide todos os inputs
- Use queries parametrizadas
- Siga OWASP Top 10

## Documentação

### Quando Documentar

- Novas features
- Mudanças de API
- Decisões arquiteturais (ADR)
- Configurações

### Onde

- `docs/` - Documentação geral
- `docs/adr/` - Architecture Decision Records
- `docs/api/` - Documentação de API
- Docstrings - Documentação de código

## Dúvidas

- Abra uma issue com a tag `question`
- Consulte a documentação existente
- Pergunte no canal do time

## Licença

Ao contribuir, você concorda que suas contribuições serão licenciadas sob a mesma licença do projeto (MIT).
