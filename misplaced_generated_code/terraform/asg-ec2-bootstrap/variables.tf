variable "aws_region" {
  type        = string
  description = "AWS region"
  default     = "us-east-1"
}

variable "name_prefix" {
  type        = string
  description = "Prefix for resource names"
  default     = "app-asg"
}

variable "instance_type" {
  type        = string
  default     = "t3.medium"
}

variable "ami_id" {
  type        = string
  description = "AMI ID (Amazon Linux 2023 recommended). Leave empty to use latest AL2023."
  default     = null
}

variable "min_size" {
  type    = number
  default = 1
}

variable "max_size" {
  type    = number
  default = 4
}

variable "desired_capacity" {
  type    = number
  default = 2
}

variable "backend_api_url" {
  type        = string
  description = "Base URL for backend API instances will use on boot"
}

variable "backend_api_token_ssm_parameter" {
  type        = string
  description = "SSM Parameter name (SecureString) for API token, or empty to skip"
  default     = ""
}

variable "application_port" {
  type    = number
  default = 8080
}

variable "vpc_id" {
  type        = string
  description = "VPC ID; leave empty to use default VPC"
  default     = null
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnet IDs for ASG; leave empty to use all subnets in VPC"
  default     = null
}
