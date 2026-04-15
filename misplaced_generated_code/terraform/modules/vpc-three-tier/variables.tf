variable "name_prefix" {
  type        = string
  description = "Prefix for resource names."
  default     = "three-tier-dev"
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for the VPC."
  default     = "10.0.0.0/16"
}

variable "az_count" {
  type        = number
  description = "Number of availability zones (1-3)."
  default     = 2

  validation {
    condition     = var.az_count >= 1 && var.az_count <= 3
    error_message = "az_count must be between 1 and 3."
  }
}

variable "single_nat_gateway" {
  type        = bool
  description = "Use one NAT gateway for all private subnets (lower cost, faster iteration in dev)."
  default     = true
}

variable "dev_access_cidr_ipv4" {
  type        = string
  description = "CIDR allowed to reach web tier (HTTP/HTTPS/SSH). Use 0.0.0.0/0 for open dev access."
  default     = "0.0.0.0/0"
}

variable "web_http_port" {
  type    = number
  default = 80
}

variable "web_https_port" {
  type    = number
  default = 443
}

variable "web_ssh_port" {
  type    = number
  default = 22
}

variable "app_tcp_ports" {
  type        = list(number)
  description = "Ports on app tier reachable from web tier."
  default     = [8080, 8443, 3000, 5000]
}

variable "db_tcp_ports" {
  type        = list(number)
  description = "Database ports reachable from app tier."
  default     = [3306, 5432, 1433, 27017]
}

variable "tags" {
  type        = map(string)
  description = "Extra tags for all resources."
  default     = {}
}
