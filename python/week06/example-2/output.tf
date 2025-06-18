# week06/example-2/outputs.tf

# Output the name and ID of the created Resource Group
output "resource_group_name" {
  description = "The name of the created Resource Group."
  value       = azurerm_resource_group.my_resource_group.name
}

# Output the name, login server, and ID of the created Azure Container Registry
output "acr_name" {
  description = "The name of the created Azure Container Registry."
  value       = azurerm_container_registry.my_acr.name
}

output "acr_login_server" {
  description = "The login server URL for the Azure Container Registry."
  value       = azurerm_container_registry.my_acr.login_server
}

output "acr_id" {
  description = "The ID of the created Azure Container Registry."
  value       = azurerm_container_registry.my_acr.id
}

# Output the name and ID of the created Azure Storage Account
output "storage_account_name" {
  description = "The name of the created Azure Storage Account."
  value       = azurerm_storage_account.my_storage_account.name
}

output "storage_account_id" {
  description = "The ID of the created Azure Storage Account."
  value       = azurerm_storage_account.my_storage_account.id
}
