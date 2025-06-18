# week06/example-2/main.tf

# Define the Terraform AzureRM and Random providers
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    random = { # Used to generate unique names for globally unique resources
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
  required_version = ">= 1.0.0"
}

# Configure the AzureRM provider
provider "azurerm" {
  features {}
}


# Define an Azure Resource Group (will create a new one for this example)
resource "azurerm_resource_group" "my_resource_group" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    environment = "dev"
    project     = "ecomm-w06-tf-ex2"
  }
}

# Define an Azure Container Registry (ACR)
resource "azurerm_container_registry" "my_acr" {
  name                = var.acr_name # ACR name
  resource_group_name = azurerm_resource_group.my_resource_group.name
  location            = azurerm_resource_group.my_resource_group.location
  sku                 = "Basic" # Basic, Standard, Premium
  admin_enabled       = true

  tags = {
    environment = "dev"
    purpose     = "container-images"
  }
}

# Define an Azure Storage Account
resource "azurerm_storage_account" "my_storage_account" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.my_resource_group.name
  location                 = azurerm_resource_group.my_resource_group.location
  account_tier             = "Standard"
  account_replication_type = "LRS" # Locally Redundant Storage

  tags = {
    environment = "dev"
    purpose     = "general-storage"
  }
}
