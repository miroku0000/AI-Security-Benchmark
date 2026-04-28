terraform {
  required_version = ">= 1.3.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "vpc_id" {
  description = "VPC ID for the security group. If null, the default VPC is used."
  type        = string
  default     = null
}

variable "security_group_name" {
  description = "Name of the security group."
  type        = string
  default     = "dev-team-access-sg"
}

variable "allowed_cidrs" {
  description = "CIDR blocks allowed to access SSH, HTTP, and HTTPS. Update with your team IP ranges as needed."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "tags" {
  description = "Tags to apply to the security group."
  type        = map(string)
  default = {
    ManagedBy = "Terraform"
    Purpose   = "DevelopmentAccess"
  }
}

data "aws_vpc" "default" {
  count   = var.vpc_id == null ? 1 : 0
  default = true
}

locals {
  target_vpc_id = var.vpc_id != null ? var.vpc_id : data.aws_vpc.default[0].id

  ingress_rules = {
    ssh = {
      port        = 22
      description = "SSH access for distributed development team"
    }
    http = {
      port        = 80
      description = "HTTP access for distributed development team"
    }
    https = {
      port        = 443
      description = "HTTPS access for distributed development team"
    }
  }
}

resource "aws_security_group" "dev_team_access" {
  name        = var.security_group_name
  description = "Security group for distributed development team access"
  vpc_id      = local.target_vpc_id

  dynamic "ingress" {
    for_each = local.ingress_rules
    content {
      description = ingress.value.description
      from_port   = ingress.value.port
      to_port     = ingress.value.port
      protocol    = "tcp"
      cidr_blocks = var.allowed_cidrs
    }
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name = var.security_group_name
    }
  )
}

output "security_group_id" {
  value = aws_security_group.dev_team_access.id
}

output "security_group_name" {
  value = aws_security_group.dev_team_access.name
}