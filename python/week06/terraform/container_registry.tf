resource "azurerm_container_registry" "acr" {
  name                = "sit722${var.prefix}acr123"
  resource_group_name = azurerm_resource_group.rg.name
  location            = var.location
  sku                 = "Basic"
  admin_enabled       = true
}
