# Implementation Plan

- [x] 1. Consolidar variáveis e eliminar duplicações

  - [x] 1.1 Remover variáveis duplicadas de main.tf
    - Remover declarações de variáveis das linhas 38-79 de main.tf
    - Manter apenas terraform block e locals em main.tf
    - _Requirements: 1.1, 1.3_

  - [x] 1.2 Remover variáveis duplicadas de azure.tf e gcp.tf
    - Remover `variable "azure_subscription_id"` e `variable "azure_tenant_id"` de azure.tf
    - Remover `variable "gcp_project_id"` de gcp.tf
    - Variáveis já existem em variables.tf
    - _Requirements: 1.1, 1.3_

  - [x] 1.3 Write property test for variable uniqueness
    - **Property 1: Variable Declaration Uniqueness**
    - **Validates: Requirements 1.1**

- [x] 2. Consolidar outputs e eliminar duplicações

  - [x] 2.1 Remover outputs duplicados de main.tf
    - Remover declarações de outputs das linhas 91-113 de main.tf
    - Outputs já existem em outputs.tf
    - _Requirements: 1.2_

  - [x] 2.2 Refatorar outputs para usar try() ou coalesce()
    - Substituir ternários aninhados por coalesce(try(...), try(...), try(...))
    - Aplicar em database_endpoint, redis_endpoint, kubernetes_endpoint, kubernetes_cluster_name
    - _Requirements: 7.2_

  - [x] 2.3 Write property test for output uniqueness
    - **Property 2: Output Declaration Uniqueness**
    - **Validates: Requirements 1.2**

  - [x] 2.4 Write property test for safe conditional access
    - **Property 10: Safe Conditional Module Access**
    - **Validates: Requirements 7.2**

- [x] 3. Checkpoint - Validar configuração sem duplicações
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Externalizar credenciais e secrets

  - [x] 4.1 Adicionar variáveis sensíveis para credenciais de banco
    - Criar variable "db_username" com sensitive = true e validation
    - Criar variable "db_password" com sensitive = true
    - Atualizar módulo aws_database para usar variáveis
    - _Requirements: 2.1, 2.2_

  - [x] 4.2 Adicionar variável para image_tag
    - Criar variable "image_tag" sem default (obrigatória)
    - Atualizar helm_release para usar var.image_tag em vez de "latest"
    - _Requirements: 8.1, 8.2_

  - [x] 4.3 Atualizar .gitignore para excluir arquivos de credenciais
    - Adicionar padrões: *.tfvars.local, backend.hcl, .env, secrets/
    - _Requirements: 2.5_

  - [x] 4.4 Write property test for no hardcoded credentials
    - **Property 3: No Hardcoded Credentials**
    - **Validates: Requirements 2.1**

  - [x] 4.5 Write property test for sensitive credential variables
    - **Property 4: Database Credential Variables Are Sensitive**
    - **Validates: Requirements 2.2**

  - [x] 4.6 Write property test for sensitive outputs
    - **Property 5: Sensitive Outputs Marked Correctly**
    - **Validates: Requirements 2.3**

  - [x] 4.7 Write property test for no latest image tags
    - **Property 11: No Latest Image Tags**
    - **Validates: Requirements 8.1**

- [x] 5. Configurar backend dinâmico

  - [x] 5.1 Refatorar backend block em main.tf
    - Remover valores hardcoded (bucket, key, region, dynamodb_table)
    - Manter apenas encrypt = true
    - _Requirements: 3.1, 3.2_

  - [x] 5.2 Criar backend.hcl.example template
    - Criar arquivo com placeholders documentados
    - Adicionar instruções de uso no README
    - _Requirements: 3.4_

  - [x] 5.3 Write property test for backend configuration
    - **Property 6: Backend Contains No Hardcoded Environment Values**
    - **Validates: Requirements 3.2**

- [x] 6. Checkpoint - Validar segurança e backend
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Adicionar validações de variáveis

  - [x] 7.1 Adicionar validação para region
    - Criar validation block com regex para regiões válidas AWS/GCP/Azure
    - _Requirements: 4.1_

  - [x] 7.2 Adicionar validação condicional para variáveis cloud-specific
    - Validar gcp_project_id não vazio quando cloud_provider = "gcp"
    - Validar azure_subscription_id não vazio quando cloud_provider = "azure"
    - _Requirements: 4.3_

  - [x] 7.3 Write property test for cloud-specific validation
    - **Property 7: Cloud-Specific Variable Validation**
    - **Validates: Requirements 4.3**

- [x] 8. Otimizar NAT Gateway para custos

  - [x] 8.1 Adicionar variável single_nat_gateway ao módulo VPC
    - Criar variable "single_nat_gateway" com default = false
    - Modificar count do NAT Gateway para usar condicional
    - Atualizar route tables para usar NAT Gateway correto
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 8.2 Atualizar chamada do módulo VPC em aws.tf
    - Passar single_nat_gateway = var.single_nat_gateway
    - _Requirements: 5.1, 5.2_

  - [x] 8.3 Adicionar variável single_nat_gateway no root
    - Criar variable em variables.tf
    - Atualizar tfvars de dev e prod
    - _Requirements: 5.1, 5.2_

  - [x] 8.4 Write property test for NAT Gateway count
    - **Property 8: NAT Gateway Count Correctness**
    - **Validates: Requirements 5.3, 5.4**

- [x] 9. Checkpoint - Validar otimizações
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Padronizar estrutura de módulos

  - [x] 10.1 Refatorar módulo aws/vpc
    - Separar variables.tf do main.tf
    - Separar outputs.tf do main.tf
    - Criar versions.tf com required_providers
    - Criar README.md com documentação e exemplos
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 10.2 Write property test for module structure
    - **Property 9: Module Structure Completeness**
    - **Validates: Requirements 6.1, 6.2, 6.3**

- [x] 11. Criar arquivo de providers centralizado

  - [x] 11.1 Criar providers.tf
    - Mover configurações de providers de aws.tf, azure.tf, gcp.tf
    - Usar try() para configurações condicionais de kubernetes/helm
    - _Requirements: 7.1, 7.3_

  - [x] 11.2 Criar versions.tf no root
    - Mover required_providers de main.tf
    - Documentar versões mínimas suportadas
    - _Requirements: 6.3_

- [x] 12. Atualizar documentação

  - [x] 12.1 Atualizar README.md principal
    - Adicionar seção de segurança
    - Documentar variáveis sensíveis
    - Adicionar instruções de backend configuration
    - Adicionar troubleshooting
    - _Requirements: 7.3_

  - [x] 12.2 Criar staging.tfvars
    - Criar arquivo de ambiente staging
    - Configurar valores intermediários entre dev e prod
    - _Requirements: 3.3_

- [x] 13. Final Checkpoint - Validação completa
  - Ensure all tests pass, ask the user if questions arise.
