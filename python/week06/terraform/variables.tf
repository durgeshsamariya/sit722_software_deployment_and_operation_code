variable "prefix" {
  description = "Prefix for all resource names"
  type        = string
  default     = "devops"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable kubernetes_version {   
  default = "1.31.7" 
}
