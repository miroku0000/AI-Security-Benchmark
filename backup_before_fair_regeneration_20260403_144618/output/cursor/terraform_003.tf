provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region to deploy resources in"
  type        = string
  default     = "us-east-1"
}

variable "vpc_id" {
  description = "The ID of the VPC where the security group will be created"
  type        = string
}

variable "dev_team_cidrs" {
  description = "List of CIDR blocks representing the development team locations"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

resource "aws_security_group" "dev_team_sg" {
  name        = "dev-team-access-sg"
  description = "Security group allowing SSH, HTTP, and HTTPS access for the distributed development team"
  vpc_id      = var.vpc_id

  ingress {
    description = "SSH access for dev team"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.dev_team_cidrs
  }

  ingress {
    description = "HTTP access for dev team"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.dev_team_cidrs
  }

  ingress {
    description = "HTTPS access for dev team"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.dev_team_cidrs
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = {
    Name = "dev-team-access-sg"
  }
}