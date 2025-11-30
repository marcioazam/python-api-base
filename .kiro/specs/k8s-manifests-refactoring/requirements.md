# Requirements Document

## Introduction

Este documento especifica os requisitos para refatoração dos manifests Kubernetes na pasta `k8s/`. O objetivo é aplicar as melhores práticas de segurança, observabilidade, resiliência e manutenibilidade, corrigindo vulnerabilidades críticas identificadas no code review.

## Glossary

- **ConfigMap**: Recurso Kubernetes para armazenar configurações não-sensíveis
- **Secret**: Recurso Kubernetes para armazenar dados sensíveis (credenciais, tokens)
- **External Secrets Operator (ESO)**: Operador que sincroniza secrets de provedores externos (AWS Secrets Manager, Vault)
- **PodDisruptionBudget (PDB)**: Recurso que limita interrupções voluntárias de pods
- **NetworkPolicy**: Recurso que controla tráfego de rede entre pods
- **SecurityContext**: Configurações de segurança a nível de pod/container
- **HPA**: HorizontalPodAutoscaler - escala pods baseado em métricas
- **Ingress**: Recurso que gerencia acesso externo HTTP/HTTPS aos serviços
- **ServiceAccount**: Identidade para processos que rodam em pods

## Requirements

### Requirement 1: Gestão Segura de Secrets

**User Story:** As a DevOps engineer, I want secrets to be managed securely without plaintext credentials in the repository, so that sensitive data is protected from unauthorized access.

#### Acceptance Criteria

1. WHEN secrets are defined THEN the system SHALL store them using External Secrets Operator referencing an external secret store
2. WHEN a Secret resource exists in the repository THEN the system SHALL NOT contain plaintext credentials in stringData or data fields
3. WHEN the application requires database credentials THEN the system SHALL inject them via secretKeyRef from externally-managed secrets
4. WHEN secrets are rotated in the external store THEN the system SHALL automatically sync within the configured refresh interval

### Requirement 2: Container Image Security

**User Story:** As a platform engineer, I want container images to use specific versioned tags with digests, so that deployments are reproducible and auditable.

#### Acceptance Criteria

1. WHEN a container image is specified THEN the system SHALL use a semantic version tag (not `latest`)
2. WHEN a container image is specified THEN the system SHALL include the SHA256 digest for immutability
3. WHEN imagePullPolicy is configured THEN the system SHALL use `Always` for production environments

### Requirement 3: Pod Security Hardening

**User Story:** As a security engineer, I want pods to run with minimal privileges and restricted capabilities, so that the attack surface is minimized.

#### Acceptance Criteria

1. WHEN a pod is deployed THEN the system SHALL run as non-root user with explicit runAsUser
2. WHEN a pod is deployed THEN the system SHALL use readOnlyRootFilesystem
3. WHEN a pod is deployed THEN the system SHALL drop ALL capabilities
4. WHEN a pod is deployed THEN the system SHALL set allowPrivilegeEscalation to false
5. WHEN a pod is deployed THEN the system SHALL use seccompProfile type RuntimeDefault
6. WHEN a namespace is created THEN the system SHALL enforce Pod Security Standards (restricted)

### Requirement 4: High Availability and Resilience

**User Story:** As a SRE, I want the application to maintain availability during cluster maintenance and failures, so that users experience minimal disruption.

#### Acceptance Criteria

1. WHEN cluster maintenance occurs THEN the system SHALL maintain minimum available pods via PodDisruptionBudget
2. WHEN pods are scheduled THEN the system SHALL distribute them across availability zones via topologySpreadConstraints
3. WHEN pods are scheduled THEN the system SHALL prefer different nodes via podAntiAffinity
4. WHEN a pod starts THEN the system SHALL use startupProbe to handle slow-starting containers
5. WHEN a pod terminates THEN the system SHALL allow graceful shutdown via terminationGracePeriodSeconds

### Requirement 5: Network Security

**User Story:** As a security engineer, I want network traffic to be restricted to only necessary communications, so that lateral movement is prevented.

#### Acceptance Criteria

1. WHEN a pod is deployed THEN the system SHALL apply NetworkPolicy restricting ingress to allowed sources
2. WHEN a pod is deployed THEN the system SHALL apply NetworkPolicy restricting egress to required destinations
3. WHEN DNS resolution is needed THEN the system SHALL allow egress to kube-dns on port 53

### Requirement 6: Ingress Security

**User Story:** As a security engineer, I want external traffic to be protected with security headers and rate limiting, so that the application is protected from common attacks.

#### Acceptance Criteria

1. WHEN Ingress is configured THEN the system SHALL use ingressClassName instead of deprecated annotation
2. WHEN Ingress is configured THEN the system SHALL add security headers (X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy, CSP)
3. WHEN Ingress is configured THEN the system SHALL enforce rate limiting via annotations
4. WHEN Ingress is configured THEN the system SHALL enforce TLS with valid certificates

### Requirement 7: Observability

**User Story:** As a SRE, I want the application to expose metrics and be discoverable by monitoring systems, so that I can monitor health and performance.

#### Acceptance Criteria

1. WHEN a pod is deployed THEN the system SHALL include Prometheus scrape annotations
2. WHEN a Service is created THEN the system SHALL include monitoring annotations
3. WHEN metrics are exposed THEN the system SHALL use standard port and path conventions

### Requirement 8: Resource Isolation

**User Story:** As a platform engineer, I want resources to be isolated in dedicated namespaces with proper labeling, so that multi-tenancy is supported.

#### Acceptance Criteria

1. WHEN resources are created THEN the system SHALL specify explicit namespace
2. WHEN resources are created THEN the system SHALL use consistent labeling following Kubernetes recommended labels
3. WHEN a ServiceAccount is needed THEN the system SHALL create a dedicated ServiceAccount with automountServiceAccountToken disabled

### Requirement 9: Deployment Strategy

**User Story:** As a DevOps engineer, I want deployments to use safe rollout strategies, so that failed deployments can be quickly rolled back.

#### Acceptance Criteria

1. WHEN a Deployment is configured THEN the system SHALL use RollingUpdate strategy with maxSurge and maxUnavailable
2. WHEN a Deployment is configured THEN the system SHALL maintain revision history for rollbacks
3. WHEN probes are configured THEN the system SHALL use appropriate thresholds for failure detection
