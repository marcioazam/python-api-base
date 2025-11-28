# ADR-006: CI/CD Security and Automation Improvements

## Status

Accepted

## Context

O pipeline de CI/CD existente cobria linting, testes e build, mas faltavam:
- Atualizações automáticas de dependências
- Análise de segurança abrangente (SAST, secrets, SBOM)
- Code review automatizado com IA
- Cache para acelerar builds

## Decision

Implementar as seguintes melhorias:

### 1. Dependabot (GitHub nativo - gratuito)
- Atualizações semanais de dependências Python
- Atualizações semanais de GitHub Actions
- Atualizações mensais de Docker
- Agrupamento de dependências dev

### 2. Security Workflow
- **Bandit**: SAST para Python
- **Trivy**: Scanner de vulnerabilidades (filesystem e Docker image)
- **TruffleHog**: Detecção de secrets
- **Dependency Review**: Análise de licenças e vulnerabilidades em PRs
- **SBOM**: Software Bill of Materials com Anchore

### 3. CodeQL (GitHub nativo - gratuito)
- Análise de segurança estática
- Queries security-extended e security-and-quality
- Execução semanal e em PRs

### 4. CodeRabbit (gratuito para OSS)
- Code review automatizado com IA
- Instruções específicas por path
- Suporte a português

### 5. Melhorias no CI
- Cache de uv para acelerar builds (~50% mais rápido)
- Concurrency para cancelar runs duplicados
- Upload de artefatos de coverage
- Scan de imagem Docker após build

## Consequences

### Positivas
- Detecção precoce de vulnerabilidades
- Dependências sempre atualizadas
- Code review mais consistente
- Builds mais rápidos com cache
- Compliance com SBOM

### Negativas
- Mais workflows para manter
- Possível ruído de PRs do Dependabot
- CodeRabbit requer aprovação de app no repo

### Neutras
- Necessário configurar CODECOV_TOKEN como secret

## Alternatives Considered

| Alternativa | Motivo da rejeição |
|-------------|-------------------|
| Snyk | Free tier mais limitado que Trivy |
| SonarCloud | Mais complexo de configurar |
| Renovate | Dependabot é nativo e suficiente |

## References

- [Dependabot docs](https://docs.github.com/en/code-security/dependabot)
- [CodeQL docs](https://docs.github.com/en/code-security/code-scanning)
- [CodeRabbit docs](https://docs.coderabbit.ai)
- [Trivy docs](https://aquasecurity.github.io/trivy)
