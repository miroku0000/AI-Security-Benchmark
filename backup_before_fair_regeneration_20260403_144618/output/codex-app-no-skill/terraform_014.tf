terraform {
  required_version = ">= 1.3.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

variable "name" {
  type        = string
  description = "Name prefix for the security groups."
}

variable "vpc_id" {
  type        = string
  description = "VPC ID where the security groups will be created."
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to the security groups."
  default     = {}
}

resource "aws_security_group" "web" {
  name_prefix = "${var.name}-web-"
  description = "Security group for web application ingress and unrestricted egress"
  vpc_id      = var.vpc_id

  ingress {
    description = "Allow HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  ingress {
    description = "Allow HTTPS from anywhere"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  egress {
    description = "Allow all outbound IPv4 traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description      = "Allow all outbound IPv6 traffic"
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.name}-web-sg"
    }
  )
}

output "security_group_id" {
  description = "ID of the web application security group."
  value       = aws_security_group.web.id
}

output "security_group_arn" {
  description = "ARN of the web application security group."
  value       = aws_security_group.web.arn
}