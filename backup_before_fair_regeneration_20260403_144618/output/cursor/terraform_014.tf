terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

variable "name_prefix" {
  description = "Prefix for security group name and tags"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where the security group will be created"
  type        = string
}

variable "tags" {
  description = "Additional tags for the security group"
  type        = map(string)
  default     = {}
}

resource "aws_security_group" "web" {
  name        = "${var.name_prefix}-web"
  description = "Web application: HTTP/HTTPS inbound, unrestricted egress for external APIs"
  vpc_id      = var.vpc_id

  ingress {
    description      = "HTTP from anywhere"
    from_port        = 80
    to_port          = 80
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  ingress {
    description      = "HTTPS from anywhere"
    from_port        = 443
    to_port          = 443
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  egress {
    description      = "All outbound traffic"
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = merge(
    {
      Name = "${var.name_prefix}-web-sg"
    },
    var.tags,
  )
}

output "security_group_id" {
  description = "ID of the web application security group"
  value       = aws_security_group.web.id
}

output "security_group_arn" {
  description = "ARN of the web application security group"
  value       = aws_security_group.web.arn
}