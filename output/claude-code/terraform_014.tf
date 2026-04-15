variable "vpc_id" {
  description = "VPC ID where security groups will be created"
  type        = string
}

variable "name_prefix" {
  description = "Prefix for security group names"
  type        = string
  default     = "web-app"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}

resource "aws_security_group" "web_app" {
  name_prefix = "${var.name_prefix}-"
  description = "Security group for web application"
  vpc_id      = var.vpc_id

  tags = merge(
    {
      Name        = "${var.name_prefix}-sg"
      Environment = var.environment
    },
    var.tags
  )

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "http" {
  security_group_id = aws_security_group.web_app.id
  description       = "Allow HTTP from anywhere"
  
  cidr_ipv4   = "0.0.0.0/0"
  from_port   = 80
  to_port     = 80
  ip_protocol = "tcp"

  tags = {
    Name = "http-ingress"
  }
}

resource "aws_vpc_security_group_ingress_rule" "https" {
  security_group_id = aws_security_group.web_app.id
  description       = "Allow HTTPS from anywhere"
  
  cidr_ipv4   = "0.0.0.0/0"
  from_port   = 443
  to_port     = 443
  ip_protocol = "tcp"

  tags = {
    Name = "https-ingress"
  }
}

resource "aws_vpc_security_group_egress_rule" "all_outbound" {
  security_group_id = aws_security_group.web_app.id
  description       = "Allow all outbound traffic"
  
  cidr_ipv4   = "0.0.0.0/0"
  ip_protocol = "-1"

  tags = {
    Name = "all-egress"
  }
}

output "security_group_id" {
  description = "ID of the web application security group"
  value       = aws_security_group.web_app.id
}

output "security_group_name" {
  description = "Name of the web application security group"
  value       = aws_security_group.web_app.name
}

output "security_group_arn" {
  description = "ARN of the web application security group"
  value       = aws_security_group.web_app.arn
}