# week06/example-1/main.tf

# Define the Terraform AzureRM provider
# This block specifies the required providers and their versions.
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0" # Specify a compatible version range for the AzureRM provider
    }
  }
  # This sets the minimum Terraform version required to run this configuration.
  required_version = ">= 1.0.0"
}

# Configure the AzureRM provider
# The 'features {}' block is required starting from AzureRM provider version 2.x
# and enables various features. It should generally be empty unless specific features are needed.
provider "azurerm" {
  features {}
}

# Define an Azure Resource Group
# 'azurerm_resource_group' is the resource type for an Azure Resource Group.
# 'my_resource_group' is the local name for this resource within Terraform.
resource "azurerm_resource_group" "my_resource_group" {
  # The 'name' argument specifies the desired name of the Resource Group in Azure.
  # We use a variable `var.resource_group_name` for flexibility.
  name = var.resource_group_name

  # The 'location' argument specifies the Azure region where the Resource Group will be created.
  # We use a variable `var.location` for flexibility.
  location = var.location

  tags = {
    environment = "dev"
    project     = "sit722_week_06_example_1"
  }
}

# Output the name and ID of the created Resource Group
# Outputs are useful for displaying important information after `terraform apply`
# or for passing values to other Terraform configurations.
output "resource_group_name" {
  description = "The name of the created Resource Group."
  value       = azurerm_resource_group.my_resource_group.name
}

output "resource_group_id" {
  description = "The ID of the created Resource Group."
  value       = azurerm_resource_group.my_resource_group.id
}
