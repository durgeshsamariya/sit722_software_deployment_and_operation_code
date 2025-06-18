# week06/example-2/variables.tf

# Define a variable for the Azure region (location)
variable "location" {
  description = "Azure region for the resources."
  type        = string
  default     = "australiaeast" # Default value, you can change this
}

# Define a Resource Group name
variable "resource_group_name" {
  description = "Azure Resource Group name."
  type        = string
  default     = "sit722_resource_group"
}

# Define a Azure Container Registry name
variable "acr_name" {
  description = "Azure Container Registry name (must be globally unique)."
  type        = string
  default     = "sit722acrweek06e02" # ACR name
}

# Define a Azure Storage Account name
# Storage account names must be lowercase and no hyphens
variable "storage_account_name" {
  description = "Azure Storage Account name (must be globally unique and lowercase)."
  type        = string
  default     = "sit722stgweek06e02" # Storage account name
}
