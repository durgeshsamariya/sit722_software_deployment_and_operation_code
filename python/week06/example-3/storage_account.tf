# week06/example-3/storage_account.tf

resource "azurerm_storage_account" "my_storage_account" {
  name                     = "${var.prefix}stg"
  resource_group_name      = azurerm_resource_group.my_resource_group.name
  location                 = azurerm_resource_group.my_resource_group.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  tags = {
    environment = "dev"
    purpose     = "general-storage"
  }
}
