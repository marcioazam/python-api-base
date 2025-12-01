# Azure PostgreSQL Flexible Server Module

variable "name_prefix" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "subnet_id" {
  type = string
}

variable "private_dns_zone_id" {
  type = string
}

variable "sku_name" {
  type    = string
  default = "B_Standard_B1ms"
}

variable "storage_mb" {
  type    = number
  default = 32768
}

variable "db_name" {
  type    = string
  default = "myapi"
}

variable "high_availability" {
  type    = bool
  default = false
}

variable "tags" {
  type    = map(string)
  default = {}
}

# Random password
resource "random_password" "db_password" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Key Vault for secrets
resource "azurerm_key_vault" "main" {
  name                = "${replace(var.name_prefix, "-", "")}kv"
  location            = var.location
  resource_group_name = var.resource_group_name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  purge_protection_enabled = true

  tags = var.tags
}

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault_access_policy" "current" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = ["Get", "List", "Set", "Delete", "Purge"]
}

resource "azurerm_key_vault_secret" "db_credentials" {
  name         = "${var.name_prefix}-db-credentials"
  value        = jsonencode({
    username = "myapi_user"
    password = random_password.db_password.result
    host     = azurerm_postgresql_flexible_server.main.fqdn
    port     = 5432
    database = var.db_name
  })
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_key_vault_access_policy.current]
}

# PostgreSQL Flexible Server
resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "${var.name_prefix}-postgres"
  resource_group_name    = var.resource_group_name
  location               = var.location
  version                = "15"
  delegated_subnet_id    = var.subnet_id
  private_dns_zone_id    = var.private_dns_zone_id
  administrator_login    = "myapi_user"
  administrator_password = random_password.db_password.result
  zone                   = "1"

  storage_mb = var.storage_mb
  sku_name   = var.sku_name

  dynamic "high_availability" {
    for_each = var.high_availability ? [1] : []
    content {
      mode                      = "ZoneRedundant"
      standby_availability_zone = "2"
    }
  }

  backup_retention_days        = 7
  geo_redundant_backup_enabled = var.high_availability

  tags = var.tags
}

# Database
resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = var.db_name
  server_id = azurerm_postgresql_flexible_server.main.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

# Outputs
output "endpoint" {
  value = azurerm_postgresql_flexible_server.main.fqdn
}

output "key_vault_id" {
  value = azurerm_key_vault.main.id
}

output "secret_name" {
  value = azurerm_key_vault_secret.db_credentials.name
}
