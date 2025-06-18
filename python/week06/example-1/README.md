# Week 06 - Terraform Example 1: Creating an Azure Resource Group

This example demonstrates the fundamental steps of using Terraform to provision an Azure Resource Group. A Resource Group is a logical container for Azure resources that share the same lifecycle, permissions, and management.

## 🛠️ Prerequisites

Before you begin, ensure you have the following installed and configured:

1.  **Terraform CLI:**
    - [Download and install Terraform](https://www.terraform.io/downloads.html).
2.  **Azure CLI:**
    - [Install the Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli).
    - Log in to your Azure account using `az login`. Terraform will use your Azure CLI credentials for authentication.

## 🚀 Usage

### 1. Navigate to the project directory:

```bash
cd week06/example-1/
```

### 2. Initialize Terraform:

This command downloads the necessary AzureRM provider plugins and initializes the working directory.

```bash
terraform init
```

### 3. Plan the deployment:

This command shows you what Terraform will do without actually making any changes. Review the output carefully to ensure it aligns with your expectations (e.g., it should show + create for the resource group).

```bash
terraform plan
```

### 4. Apply the deployment:

This command executes the plan and provisions the resources in your Azure subscription. You will be prompted to type yes to confirm.

```bash
terraform apply
```

Upon successful completion, Terraform will output the name and ID of the created resource group.

## Verification

You can verify the creation of the Resource Group in a few ways:

- Terraform Output: Check the output of `terraform apply` for the `resource_group_name` and `resource_group_id`.

- Azure CLI:

```bash
az group list -o table
```

- Azure Portal: Log in to the Azure portal and search for the resource group by its name.

## Cleanup

To remove the resources created by this Terraform configuration and avoid unnecessary costs:

- Navigate to the project directory:

```bash
cd week06/example-1/
```

- Destroy the resources:
  This command will tear down all resources managed by this Terraform configuration. You will be prompted to type `yes` to confirm.

```bash
terraform destroy
```
