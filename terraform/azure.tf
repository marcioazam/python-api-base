# Azure Provider Configuration and Module Calls

variable "azure_subscription_id" {
  description = "Azure Subscription ID"
  type        = string
  default     = ""
}

variable "azure_tenant_id" {
  description = "Azure Tenant ID"
  type        = string
  default     = ""
}

provider "azurerm" {
  features {}
  subscription_id = var.azure_subscription_id
  tenant_id       = var.azure_tenant_id
}

# Resource Group
resource "azurerm_resource_group" "main" {
  count    = var.cloud_provider == "azure" ? 1 : 0
  name     = "${local.name_prefix}-rg"
  location = var.region == "us-east-1" ? "eastus" : var.region

  tags = local.common_tags
}

# Virtual Network
resource "azurerm_virtual_network" "main" {
  count               = var.cloud_provider == "azure" ? 1 : 0
  name                = "${local.name_prefix}-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.main[0].location
  resource_group_name = azurerm_resource_group.main[0].name

  tags = local.common_tags
}

resource "azurerm_subnet" "aks" {
  count                = var.cloud_provider == "azure" ? 1 : 0
  name                 = "aks-subnet"
  resource_group_name  = azurerm_resource_group.main[0].name
  virtual_network_name = azurerm_virtual_network.main[0].name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_subnet" "database" {
  count                = var.cloud_provider == "azure" ? 1 : 0
  name                 = "database-subnet"
  resource_group_name  = azurerm_resource_group.main[0].name
  virtual_network_name = azurerm_virtual_network.main[0].name
  address_prefixes     = ["10.0.2.0/24"]

  delegation {
    name = "postgresql"
    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_subnet" "redis" {
  count                = var.cloud_provider == "azure" ? 1 : 0
  name                 = "redis-subnet"
  resource_group_name  = azurerm_resource_group.main[0].name
  virtual_network_name = azurerm_virtual_network.main[0].name
  address_prefixes     = ["10.0.3.0/24"]
}

# Private DNS Zone for PostgreSQL
resource "azurerm_private_dns_zone" "postgres" {
  count               = var.cloud_provider == "azure" ? 1 : 0
  name                = "${local.name_prefix}.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.main[0].name

  tags = local.common_tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgres" {
  count                 = var.cloud_provider == "azure" ? 1 : 0
  name                  = "${local.name_prefix}-postgres-link"
  private_dns_zone_name = azurerm_private_dns_zone.postgres[0].name
  virtual_network_id    = azurerm_virtual_network.main[0].id
  resource_group_name   = azurerm_resource_group.main[0].name
}

# Database Module
module "azure_database" {
  count  = var.cloud_provider == "azure" ? 1 : 0
  source = "./modules/azure/postgresql"

  name_prefix         = local.name_prefix
  resource_group_name = azurerm_resource_group.main[0].name
  location            = azurerm_resource_group.main[0].location
  subnet_id           = azurerm_subnet.database[0].id
  private_dns_zone_id = azurerm_private_dns_zone.postgres[0].id
  sku_name            = var.db_instance_class == "db.t3.micro" ? "B_Standard_B1ms" : "GP_Standard_D2s_v3"
  storage_mb          = 32768
  db_name             = "myapi"
  high_availability   = var.environment == "prod"
  tags                = local.common_tags
}

# Redis Module
module "azure_redis" {
  count  = var.cloud_provider == "azure" ? 1 : 0
  source = "./modules/azure/redis"

  name_prefix         = local.name_prefix
  resource_group_name = azurerm_resource_group.main[0].name
  location            = azurerm_resource_group.main[0].location
  subnet_id           = azurerm_subnet.redis[0].id
  sku_name            = var.environment == "prod" ? "Premium" : "Basic"
  family              = var.environment == "prod" ? "P" : "C"
  capacity            = var.environment == "prod" ? 1 : 0
  tags                = local.common_tags
}

# AKS Module
module "azure_aks" {
  count  = var.cloud_provider == "azure" ? 1 : 0
  source = "./modules/azure/aks"

  name_prefix         = local.name_prefix
  resource_group_name = azurerm_resource_group.main[0].name
  location            = azurerm_resource_group.main[0].location
  subnet_id           = azurerm_subnet.aks[0].id
  node_count          = var.k8s_node_count
  vm_size             = var.k8s_node_size == "t3.medium" ? "Standard_D2s_v3" : "Standard_D4s_v3"
  kubernetes_version  = "1.28"
  tags                = local.common_tags
}
