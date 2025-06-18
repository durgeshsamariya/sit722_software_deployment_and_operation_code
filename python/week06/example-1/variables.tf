# week06/example-1/variables.tf

# Define a variable for the Azure region (location)
variable "location" {
  description = "Azure region for the resources."
  type        = string
  default     = "australiaeast" # Default value, you can change this
}

# Define a variable for the Resource Group name
variable "resource_group_name" {
  description = "Name of the Azure Resource Group to create."
  type        = string
  default     = "sit722_week_06" # Default value, ensure it's unique in your subscription
}
