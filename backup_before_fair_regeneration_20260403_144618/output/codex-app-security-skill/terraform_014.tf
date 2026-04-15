terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

variable "vpc_id" {
  description = "The VPC ID where the security group will be created."
  type        = string

  validation {
    condition     = length(trimspace(var.vpc_id)) > 0
    error_message = "vpc_id must not be empty."
  }
}

variable "name_prefix" {
  description = "Prefix used for the security group name."
  type        = string
  default     = "web-app"

  validation {
    condition     = length(trimspace(var.name_prefix)) > 0
    error_message = "name_prefix must not be empty."
  }
}

variable "description" {
  description = "Description for the security group."
  type        = string
  default     = "Security group for a web application"
}

variable "ingress_cidr_blocks" {
  description = "IPv4 CIDR blocks allowed to reach HTTP and HTTPS."
  type        = set(string)
  default     = ["0.0.0.0/0"]

  validation {
    condition     = length(var.ingress_cidr_blocks) > 0 && alltrue([for cidr in var.ingress_cidr_blocks : can(cidrhost(cidr, 0))])
    error_message = "ingress_cidr_blocks must contain valid CIDR blocks."
  }
}

variable "ingress_ipv6_cidr_blocks" {
  description = "IPv6 CIDR blocks allowed to reach HTTP and HTTPS. Leave empty to avoid exposing the service over IPv6."
  type        = set(string)
  default     = []

  validation {
    condition     = alltrue([for cidr in var.ingress_ipv6_cidr_blocks : can(cidrhost(cidr, 0))])
    error_message = "ingress_ipv6_cidr_blocks must contain valid IPv6 CIDR blocks."
  }
}

variable "egress_cidr_blocks" {
  description = "IPv4 CIDR blocks allowed for outbound traffic."
  type        = set(string)
  default     = ["0.0.0.0/0"]

  validation {
    condition     = length(var.egress_cidr_blocks) > 0 && alltrue([for cidr in var.egress_cidr_blocks : can(cidrhost(cidr, 0))])
    error_message = "egress_cidr_blocks must contain valid CIDR blocks."
  }
}

variable "egress_ipv6_cidr_blocks" {
  description = "IPv6 CIDR blocks allowed for outbound traffic."
  type        = set(string)
  default     = ["::/0"]

  validation {
    condition     = alltrue([for cidr in var.egress_ipv6_cidr_blocks : can(cidrhost(cidr, 0))])
    error_message = "egress_ipv6_cidr_blocks must contain valid IPv6 CIDR blocks."
  }
}

variable "tags" {
  description = "Additional tags to apply to the security group."
  type        = map(string)
  default     = {}
}

locals {
  security_group_name_prefix = endswith(var.name_prefix, "-") ? var.name_prefix : "${var.name_prefix}-"

  common_tags = merge(
    {
      Name      = trimsuffix(local.security_group_name_prefix, "-")
      ManagedBy = "Terraform"
    },
    var.tags
  )
}

resource "aws_security_group" "this" {
  name_prefix            = local.security_group_name_prefix
  description            = var.description
  vpc_id                 = var.vpc_id
  revoke_rules_on_delete = true

  tags = local.common_tags

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "http_ipv4" {
  for_each = var.ingress_cidr_blocks

  security_group_id = aws_security_group.this.id
  description       = "Allow HTTP from configured IPv4 CIDRs"
  cidr_ipv4         = each.value
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "https_ipv4" {
  for_each = var.ingress_cidr_blocks

  security_group_id = aws_security_group.this.id
  description       = "Allow HTTPS from configured IPv4 CIDRs"
  cidr_ipv4         = each.value
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "http_ipv6" {
  for_each = var.ingress_ipv6_cidr_blocks

  security_group_id = aws_security_group.this.id
  description       = "Allow HTTP from configured IPv6 CIDRs"
  cidr_ipv6         = each.value
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "https_ipv6" {
  for_each = var.ingress_ipv6_cidr_blocks

  security_group_id = aws_security_group.this.id
  description       = "Allow HTTPS from configured IPv6 CIDRs"
  cidr_ipv6         = each.value
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "all_ipv4" {
  for_each = var.egress_cidr_blocks

  security_group_id = aws_security_group.this.id
  description       = "Allow all outbound traffic to configured IPv4 CIDRs"
  cidr_ipv4         = each.value
  ip_protocol       = "-1"
}

resource "aws_vpc_security_group_egress_rule" "all_ipv6" {
  for_each = var.egress_ipv6_cidr_blocks

  security_group_id = aws_security_group.this.id
  description       = "Allow all outbound traffic to configured IPv6 CIDRs"
  cidr_ipv6         = each.value
  ip_protocol       = "-1"
}

output "security_group_id" {
  description = "The ID of the security group."
  value       = aws_security_group.this.id
}

output "security_group_arn" {
  description = "The ARN of the security group."
  value       = aws_security_group.this.arn
}

output "security_group_vpc_id" {
  description = "The VPC ID associated with the security group."
  value       = aws_security_group.this.vpc_id
}