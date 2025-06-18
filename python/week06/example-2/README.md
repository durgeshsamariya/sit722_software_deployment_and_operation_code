# Week 06 - Example 2: Creating Azure Container Registry (ACR) and Storage Account

This example demonstrates how to use Terraform to provision two essential Azure services for cloud-native applications: an Azure Container Registry (ACR) and an Azure Storage Account.

## 🚀 Purpose

The primary goals of this example are to illustrate:
- How to provision an `azurerm_container_registry` for storing and managing Docker images.
- How to provision an `azurerm_storage_account` for general-purpose blob, file, queue, and table storage.
- The use of the `random` provider to generate unique names for globally unique resources.
- Building on the basic Terraform workflow with additional resource types.

## 🛠️ Prerequisites

Before you begin, ensure you have the following installed and configured:

1.  **Terraform CLI:**
    * [Download and install Terraform](https://www.terraform.io/downloads.html).
2.  **Azure CLI:**
    * [Install the Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli).
    * Log in to your Azure account using `az login`. Terraform will use your Azure CLI credentials for authentication.

## 📁 Project Structure

Create the following directory and files:

week06/
├── main.tf
├── variables.tf
└── outputs.tf

## 📝 Configuration Files

### `main.tf`

This file defines the Azure provider, the `random_pet` resource for unique naming, the Resource Group, the Azure Container Registry, and the Azure Storage Account.

```terraform
# Week 06 - Terraform Example 2: Creating Azure Container Registry and Storage Account
# File: week06/terraform-example-2-acr-storage/main.tf

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

# Configure the Random provider
provider "random" {}

# Create a random pet name to ensure unique resource group, ACR, and Storage Account names
resource "random_pet" "unique_suffix" {
  length = 2 # e.g., "fast-cat"
  separator = "-"
}

# Define an Azure Resource Group (will create a new one for this example)
resource "azurerm_resource_group" "example_resource_group" {
  name     = "<span class="math-inline">\{var\.resource\_group\_name\_prefix\}\-</span>{random_pet.unique_suffix.id}"
  location = var.location

  tags = {
    environment = "dev"
    project     = "ecomm-w06-tf-ex2"
  }
}

# Define an Azure Container Registry (ACR)
resource "azurerm_container_registry" "example_acr" {
  name                = "<span class="math-inline">\{var\.acr\_name\_prefix\}</span>{replace(random_pet.unique_suffix.id, "-", "")}" # ACR names cannot have hyphens in a row like "fast--cat"
  resource_group_name = azurerm_resource_group.example_resource_group.name
  location            = azurerm_resource_group.example_resource_group.location
  sku                 = "Basic" # Basic, Standard, Premium
  admin_enabled       = true    # Enables admin user for easy login (useful for demos)

  tags = {
    environment = "dev"
    purpose     = "container-images"
  }
}

# Define an Azure Storage Account
resource "azurerm_storage_account" "example_storage_account" {
  name                     = "<span class="math-inline">\{var\.storage\_account\_name\_prefix\}</span>{replace(random_pet.unique_suffix.id, "-", "")}" # Storage account names must be lowercase and no hyphens
  resource_group_name      = azurerm_resource_group.example_resource_group.name
  location                 = azurerm_resource_group.example_resource_group.location
  account_tier             = "Standard"
  account_replication_type = "LRS" # Locally Redundant Storage
  
  tags = {
    environment = "dev"
    purpose     = "general-storage"
  }
}

```

### `variable.tf`

This file defines the customizable input variables for your Terraform configuration.

```terraform
# Week 06 - Terraform Example 2: Variables for ACR and Storage Account Creation
# File: week06/terraform-example-2-acr-storage/variables.tf

# Define a variable for the Azure region (location)
variable "location" {
  description = "Azure region for the resources."
  type        = string
  default     = "australiaeast" # Default value, you can change this
}

# Define a prefix for the Resource Group name
variable "resource_group_name_prefix" {
  description = "Prefix for the Azure Resource Group name."
  type        = string
  default     = "tf-rg-w06-ex2"
}

# Define a prefix for the Azure Container Registry name
variable "acr_name_prefix" {
  description = "Prefix for the Azure Container Registry name (must be globally unique)."
  type        = string
  default     = "ecommacr" # ACR name will be e.g., "ecommacrfastcat"
}

# Define a prefix for the Azure Storage Account name
variable "storage_account_name_prefix" {
  description = "Prefix for the Azure Storage Account name (must be globally unique and lowercase)."
  type        = string
  default     = "ecommstg" # Storage account name will be e.g., "ecommstgfastcat"
}
```

### `outputs.tf`

This file exports useful information about the created ACR and Storage Account.

```terraform
# Week 06 - Terraform Example 2: Outputs for ACR and Storage Account
# File: week06/terraform-example-2-acr-storage/outputs.tf

# Output the name and ID of the created Resource Group
output "resource_group_name" {
  description = "The name of the created Resource Group."
  value       = azurerm_resource_group.example_resource_group.name
}

# Output the name, login server, and ID of the created Azure Container Registry
output "acr_name" {
  description = "The name of the created Azure Container Registry."
  value       = azurerm_container_registry.example_acr.name
}

output "acr_login_server" {
  description = "The login server URL for the Azure Container Registry."
  value       = azurerm_container_registry.example_acr.login_server
}

output "acr_id" {
  description = "The ID of the created Azure Container Registry."
  value       = azurerm_container_registry.example_acr.id
}

# Output the name and ID of the created Azure Storage Account
output "storage_account_name" {
  description = "The name of the created Azure Storage Account."
  value       = azurerm_storage_account.example_storage_account.name
}

output "storage_account_id" {
  description = "The ID of the created Azure Storage Account."
  value       = azurerm_storage_account.example_storage_account.id
}
```

## Usage

### 1. Navigate to the project directory: 

```bash
cd week06/example-2

```

### 2. Initialize Terraform:
This command downloads the necessary AzureRM and Random provider plugins. 

```bash
terraform init
```

### 3. Plan the deployment:
Review the proposed changes carefully.

```bash
terraform plan
```

### 4. Apply the deployment:

Confirm the changes by typing `yes` when prompted.

```bash
terraform apply
```

Upon successful completion, Terraform will output the names and IDs of the created resources.

## Verification

You can verify the creation of the resources in a few ways:

- Terraform Output: Check the output of terraform apply for the exported values.

- Azure CLI:

    - Resource Group:
    ```bash
    az group list -o table
    ```

    - Container Registry:
    ```bash
    az acr list --resource-group <resource_group_name> -o table
    ```

    or 

    ```bash
    az acr list --resource-group $(terraform output -raw resource_group_name) -o table
    ```

    - Storage Account:
    ```bash
    az storage account list --resource-group <resource_group_name> -o table
    ```

    or 

    ```bash
    az storage account list --resource-group $(terraform output -raw resource_group_name) -o table
    ```

- Azure Portal: Log in to the Azure portal and search for the resource group by its name.

## Cleanup

To remove the resources created by this Terraform configuration and avoid unnecessary costs:

- Navigate to the project directory:
```bash
cd week06/example-2/
```

- Destroy the resources:
This command will tear down all resources managed by this Terraform configuration. You will be prompted to type `yes` to confirm.

```bash
terraform destroy
```