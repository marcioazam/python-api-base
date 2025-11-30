# Implementation Plan

- [x] 1. Criar infraestrutura de testes para k8s manifests

  - [x] 1.1 Criar arquivo de testes `tests/properties/test_k8s_properties.py`
    - Implementar helpers para parsing YAML
    - Criar funções para extrair recursos por tipo
    - _Requirements: 1.2, 2.1, 3.1_

  - [x] 1.2 Write property test for no plaintext secrets
    - **Property 1: No Plaintext Secrets**
    - **Validates: Requirements 1.2**

  - [x] 1.3 Write property test for no latest image tags
    - **Property 2: No Latest Image Tags**
    - **Validates: Requirements 2.1**

- [x] 2. Remover secrets plaintext e criar External Secret

  - [x] 2.1 Remover Secret do configmap.yaml
    - Separar ConfigMap e Secret em arquivos distintos
    - Remover credenciais plaintext
    - _Requirements: 1.2_

  - [x] 2.2 Criar external-secret.yaml
    - Criar ExternalSecret referenciando AWS Secrets Manager
    - Configurar refreshInterval
    - _Requirements: 1.1, 1.3_

- [x] 3. Hardening de segurança do Deployment

  - [x] 3.1 Atualizar image tag para versão específica
    - Substituir `my-api:latest` por `my-api:1.0.0`
    - Adicionar imagePullPolicy: Always
    - _Requirements: 2.1, 2.3_

  - [x] 3.2 Adicionar capabilities drop ALL
    - Adicionar securityContext.capabilities.drop: [ALL]
    - _Requirements: 3.3_

  - [x] 3.3 Adicionar seccompProfile
    - Adicionar securityContext.seccompProfile.type: RuntimeDefault
    - _Requirements: 3.5_

  - [x] 3.4 Write property test for pod security context
    - **Property 3: Pod Security Context Hardening**
    - **Validates: Requirements 3.1, 3.2, 3.4**

  - [x] 3.5 Write property test for capabilities dropped
    - **Property 4: Capabilities Dropped**
    - **Validates: Requirements 3.3**

- [x] 4. Checkpoint - Validar segurança básica
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Adicionar recursos de resiliência

  - [x] 5.1 Criar pdb.yaml
    - Criar PodDisruptionBudget com minAvailable
    - _Requirements: 4.1_

  - [x] 5.2 Adicionar topologySpreadConstraints ao Deployment
    - Distribuir pods entre zonas de disponibilidade
    - _Requirements: 4.2_

  - [x] 5.3 Adicionar startupProbe ao Deployment
    - Configurar startupProbe para containers slow-starting
    - _Requirements: 4.4_

  - [x] 5.4 Adicionar terminationGracePeriodSeconds
    - Configurar graceful shutdown
    - _Requirements: 4.5_

  - [x] 5.5 Write property test for PDB exists
    - **Property 5: PodDisruptionBudget Exists**
    - **Validates: Requirements 4.1**

  - [x] 5.6 Write property test for startup probe
    - **Property 12: Startup Probe Configuration**
    - **Validates: Requirements 4.4**

- [x] 6. Adicionar NetworkPolicy

  - [x] 6.1 Criar networkpolicy.yaml
    - Criar NetworkPolicy com ingress rules
    - Criar NetworkPolicy com egress rules (incluindo DNS)
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 6.2 Write property test for NetworkPolicy exists
    - **Property 6: NetworkPolicy Exists**
    - **Validates: Requirements 5.1, 5.2**

- [x] 7. Checkpoint - Validar resiliência e rede
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Melhorar Ingress

  - [x] 8.1 Adicionar ingressClassName
    - Substituir annotation deprecated por ingressClassName
    - _Requirements: 6.1_

  - [x] 8.2 Adicionar security headers
    - Adicionar X-Frame-Options, X-Content-Type-Options, CSP
    - _Requirements: 6.2_

  - [x] 8.3 Adicionar rate limiting
    - Configurar rate limiting annotations
    - _Requirements: 6.3_

  - [x] 8.4 Write property test for ingress security headers
    - **Property 7: Ingress Security Headers**
    - **Validates: Requirements 6.2**

  - [x] 8.5 Write property test for ingress class
    - **Property 8: Ingress Class Specification**
    - **Validates: Requirements 6.1**

- [x] 9. Adicionar observabilidade

  - [x] 9.1 Adicionar Prometheus annotations ao Deployment
    - Adicionar prometheus.io/scrape, prometheus.io/port, prometheus.io/path
    - _Requirements: 7.1, 7.3_

  - [x] 9.2 Adicionar monitoring annotations ao Service
    - _Requirements: 7.2_

  - [x] 9.3 Write property test for Prometheus annotations
    - **Property 9: Prometheus Annotations**
    - **Validates: Requirements 7.1**

- [x] 10. Padronizar labels e namespace

  - [x] 10.1 Criar namespace.yaml
    - Criar namespace com Pod Security Standards labels
    - _Requirements: 3.6, 8.1_

  - [x] 10.2 Criar serviceaccount.yaml
    - Criar ServiceAccount com automountServiceAccountToken: false
    - _Requirements: 8.3_

  - [x] 10.3 Atualizar todos os recursos com labels padrão
    - Adicionar app.kubernetes.io/* labels
    - Adicionar namespace explícito
    - _Requirements: 8.1, 8.2_

  - [x] 10.4 Write property test for Kubernetes recommended labels
    - **Property 10: Kubernetes Recommended Labels**
    - **Validates: Requirements 8.2**

- [x] 11. Melhorar estratégia de deployment

  - [x] 11.1 Configurar RollingUpdate strategy
    - Adicionar maxSurge e maxUnavailable
    - _Requirements: 9.1_

  - [x] 11.2 Configurar revisionHistoryLimit
    - _Requirements: 9.2_

  - [x] 11.3 Write property test for deployment strategy
    - **Property 11: Deployment Strategy Configuration**
    - **Validates: Requirements 9.1**

- [x] 12. Final Checkpoint - Validação completa

  - All 12 property tests pass
  - All k8s manifests refactored with security best practices
  - External Secrets, NetworkPolicy, PDB implemented
  - Kubernetes recommended labels applied to all resources
