# Requirements Document

## Introduction

Esta especificação documenta a auditoria dos módulos de infraestrutura solicitados: `elasticsearch`, `errors`, `feature_flags`, `generics` e `httpclient`. O objetivo é verificar se o código está vinculado ao workflow do projeto, se há bugs, conexões com o código principal, e se é possível testar via ItemExample/PedidoExample e manualmente via API/Docker.

## Glossary

- **Módulo de Infraestrutura**: Componente da camada de infraestrutura que fornece serviços técnicos
- **Workflow do Projeto**: Fluxo de execução desde a inicialização da API até o processamento de requisições
- **ItemExample/PedidoExample**: Entidades de exemplo do sistema para demonstração de funcionalidades
- **Property-Based Testing (PBT)**: Testes que verificam propriedades universais usando geração de dados aleatórios
- **Dead Code**: Código que existe mas nunca é executado no fluxo normal da aplicação

## Requirements

### Requirement 1

**User Story:** As a developer, I want to verify that infrastructure modules are properly integrated into the application workflow, so that I can ensure code is not orphaned.

#### Acceptance Criteria

1. WHEN analyzing `infrastructure.errors` THEN the System SHALL identify all modules that import from it
2. WHEN analyzing `infrastructure.httpclient` THEN the System SHALL identify all modules that import from it
3. WHEN analyzing `infrastructure.feature_flags` THEN the System SHALL identify all modules that import from it
4. WHEN analyzing `infrastructure.generics` THEN the System SHALL identify all modules that import from it
5. WHEN analyzing `infrastructure.elasticsearch` THEN the System SHALL identify all modules that import from it

### Requirement 2

**User Story:** As a developer, I want to identify dead code in infrastructure modules, so that I can remove unused components.

#### Acceptance Criteria

1. WHEN a module has no imports from application code THEN the System SHALL flag it as potentially dead code
2. WHEN a module is only imported by tests THEN the System SHALL flag it as test-only code
3. WHEN a module is imported by main.py or middleware THEN the System SHALL mark it as active in workflow

### Requirement 3

**User Story:** As a developer, I want to verify that infrastructure modules can be tested via ItemExample/PedidoExample, so that I can validate integration.

#### Acceptance Criteria

1. WHEN ItemExample uses an infrastructure module THEN the System SHALL document the connection
2. WHEN PedidoExample uses an infrastructure module THEN the System SHALL document the connection
3. WHEN an infrastructure module has no connection to examples THEN the System SHALL identify alternative test paths

### Requirement 4

**User Story:** As a developer, I want to verify that infrastructure modules can be tested manually via Docker, so that I can perform integration testing.

#### Acceptance Criteria

1. WHEN docker-compose.dev.yml is used THEN the System SHALL start all required services
2. WHEN the API starts THEN the System SHALL load all infrastructure modules without errors
3. WHEN testing manually THEN the System SHALL provide endpoints that exercise infrastructure modules

### Requirement 5

**User Story:** As a developer, I want to identify bugs or issues in infrastructure modules, so that I can fix them.

#### Acceptance Criteria

1. WHEN analyzing module code THEN the System SHALL identify any syntax or import errors
2. WHEN analyzing module tests THEN the System SHALL identify any skipped or failing tests
3. WHEN analyzing module dependencies THEN the System SHALL identify any missing dependencies

## Analysis Results

### Module: `infrastructure.errors`

**Status: ✅ ATIVO NO WORKFLOW**

**Importado por:**
- `infrastructure.db.session` - Usa `DatabaseError`
- `infrastructure.scylladb.client` - Usa `DatabaseError`
- `infrastructure.messaging.inbox` - Usa `MessagingError`
- `tests/unit/infrastructure/test_exceptions.py` - Testes unitários
- `tests/properties/test_infrastructure_examples_integration_properties.py` - Testes de propriedade

**Conexão com ItemExample/PedidoExample:**
- ✅ Indiretamente via `infrastructure.db.session` que é usado pelo router de examples

**Testável via Docker:**
- ✅ Sim, erros são lançados quando operações de banco falham

**Issues Identificados:**
- ✅ Nenhum bug identificado
- ✅ Testes passando

---

### Module: `infrastructure.httpclient`

**Status: ⚠️ PARCIALMENTE ATIVO**

**Importado por:**
- `tests/unit/infrastructure/httpclient/test_client.py` - **SKIPPED** (RetryPolicy não implementado)
- `docs/refactoring-report-2025-01-02.md` - Documentação

**Conexão com ItemExample/PedidoExample:**
- ❌ Nenhuma conexão direta

**Testável via Docker:**
- ⚠️ Não há endpoints que usem este módulo atualmente

**Issues Identificados:**
- 🐛 **BUG ENCONTRADO**: Teste unitário está **SKIPPED** com mensagem "RetryPolicy not implemented in httpclient.client"
  - **Causa**: O teste importa `RetryPolicy` de `infrastructure.httpclient.client`, mas está definido em `infrastructure.httpclient.resilience`
  - **Correção**: Alterar import para `from infrastructure.httpclient import RetryPolicy` ou `from infrastructure.httpclient.resilience import RetryPolicy`
- ⚠️ Módulo não está integrado ao workflow principal
- ⚠️ Código potencialmente órfão - não é usado por nenhum componente ativo

---

### Module: `infrastructure.feature_flags`

**Status: ✅ ATIVO NO WORKFLOW**

**Importado por:**
- `infrastructure/__init__.py` - Exportado no módulo principal
- `interface/middleware/production.py` - Usado no middleware de produção

**Conexão com ItemExample/PedidoExample:**
- ⚠️ Indiretamente via middleware (todas as requisições passam pelo middleware)

**Testável via Docker:**
- ✅ Sim, via middleware de produção que é configurado em `main.py`

**Issues Identificados:**
- ✅ Nenhum bug identificado
- ✅ Testes de propriedade existem em `tests/properties/test_feature_flags_properties.py`
- ⚠️ Usa `application.services.feature_flags` nos testes, não `infrastructure.feature_flags`

---

### Module: `infrastructure.generics`

**Status: ⚠️ PARCIALMENTE ATIVO**

**Importado por:**
- `tests/properties/test_infrastructure_generics_properties.py` - Testes de propriedade

**Conexão com ItemExample/PedidoExample:**
- ❌ Nenhuma conexão direta

**Testável via Docker:**
- ⚠️ Não há endpoints que usem este módulo diretamente

**Issues Identificados:**
- ⚠️ Módulo é principalmente usado por testes
- ⚠️ Protocols definidos (`Repository`, `Service`, `Factory`, `Store`) não são implementados pelos repositórios de examples
- ⚠️ Código potencialmente subutilizado

---

### Module: `infrastructure.elasticsearch`

**Status: ⚠️ PARCIALMENTE ATIVO**

**Importado por:**
- `tests/unit/infrastructure/elasticsearch/test_document.py` - Testes unitários
- `tests/unit/infrastructure/elasticsearch/test_repository.py` - Testes unitários
- Módulos internos do próprio elasticsearch

**Conexão com ItemExample/PedidoExample:**
- ❌ Nenhuma conexão direta

**Testável via Docker:**
- ⚠️ Elasticsearch não está configurado no docker-compose.base.yml ou docker-compose.dev.yml
- ⚠️ Não há endpoints que usem este módulo

**Issues Identificados:**
- ⚠️ Módulo não está integrado ao workflow principal
- ⚠️ Elasticsearch não está no docker-compose
- ⚠️ Código potencialmente órfão

---

## Summary

| Módulo | Status | Workflow | Examples | Docker | Bugs |
|--------|--------|----------|----------|--------|------|
| errors | ✅ Ativo | ✅ | ✅ Indireto | ✅ | ✅ Nenhum |
| httpclient | ⚠️ Parcial | ❌ | ❌ | ⚠️ | ⚠️ Teste skipped |
| feature_flags | ✅ Ativo | ✅ | ⚠️ Indireto | ✅ | ✅ Nenhum |
| generics | ⚠️ Parcial | ⚠️ | ❌ | ⚠️ | ⚠️ Subutilizado |
| elasticsearch | ⚠️ Parcial | ❌ | ❌ | ❌ | ⚠️ Não configurado |

## Recommendations

1. **httpclient**: Corrigir o teste skipped ou remover se não for usado
2. **elasticsearch**: Adicionar ao docker-compose ou documentar como código futuro
3. **generics**: Considerar usar os protocols nos repositórios de examples
4. **Todos**: Adicionar testes de integração que exercitem estes módulos via API
