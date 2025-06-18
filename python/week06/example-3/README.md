# Week 06 - Example 3: Creating Azure Kubernetes Service, Azure Container Registry (ACR) and Storage Account

This example demonstrates how to use Terraform to provision two essential Azure services for cloud-native applications: an Azure Container Registry (ACR) and an Azure Storage Account.

## Usage

### 1. Navigate to the project directory:

```bash
cd week06/example-3
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

### 1. Azure CLI:

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

- Azure Kubernetes Service

  ```bash
  az aks list --resource-group <resource_group_name> -o table
  ```

  or

  ```bash
  az aks list --resource-group $(terraform output -raw resource_group_name) -o table
  ```

### 2. Azure Portal

Log in to the Azure portal and search for the resource group by its name.

## Cleanup

To remove the resources created by this Terraform configuration and avoid unnecessary costs:

- Navigate to the project directory:

  ```bash
  cd week06/example-3/
  ```

- Destroy the resources:
  This command will tear down all resources managed by this Terraform configuration. You will be prompted to type `yes` to confirm.

  ```bash
  terraform destroy
  ```
