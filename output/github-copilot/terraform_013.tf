I found benchmark content around Terraform/RDS prompts, so I'm checking the local context to avoid reproducing insecure patterns and to keep the output aligned with the repo’s conventions.

terraform {
  required_version = ">= 1.5.0"

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
  type    = string
  default = "us-east-1"
}

variable "name_prefix" {
  type    = string
  default = "app"
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "allowed_cidrs" {
  type = list(string)
}

variable "db_name" {
  type    = string
  default = "appdb"
}

variable "db_username" {
  type    = string
  default = "admin"
}

variable "db_password" {
  type      = string
  sensitive = true
  nullable  = false

  validation {
    condition     = length(var.db_password) >= 8
    error_message = "db_password must be at least 8 characters long."
  }
}

variable "instance_class" {
  type    = string
  default = "db.t3.micro"
}

variable "allocated_storage" {
  type    = number
  default = 20
}

resource "aws_security_group" "rds" {
  name        = "${var.name_prefix}-rds-sg"
  description = "Allow MySQL access for the development team"
  vpc_id      = var.vpc_id

  ingress {
    description = "MySQL from approved developer networks"
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.name_prefix}-rds-sg"
  }
}

resource "aws_db_subnet_group" "mysql" {
  name       = "${var.name_prefix}-mysql-subnet-group"
  subnet_ids = var.subnet_ids

  tags = {
    Name = "${var.name_prefix}-mysql-subnet-group"
  }
}

resource "aws_db_instance" "mysql" {
  identifier                     = "${var.name_prefix}-mysql"
  engine                         = "mysql"
  engine_version                 = "8.0"
  instance_class                 = var.instance_class
  allocated_storage              = var.allocated_storage
  max_allocated_storage          = 100
  storage_type                   = "gp3"
  storage_encrypted              = true
  db_name                        = var.db_name
  username                       = var.db_username
  password                       = var.db_password
  port                           = 3306
  db_subnet_group_name           = aws_db_subnet_group.mysql.name
  vpc_security_group_ids         = [aws_security_group.rds.id]
  publicly_accessible            = true
  backup_retention_period        = 7
  deletion_protection            = false
  skip_final_snapshot            = true
  apply_immediately              = true
  auto_minor_version_upgrade     = true
  enabled_cloudwatch_logs_exports = ["error", "general", "slowquery"]

  tags = {
    Name = "${var.name_prefix}-mysql"
  }
}

output "db_endpoint" {
  value = aws_db_instance.mysql.address
}

output "db_port" {
  value = aws_db_instance.mysql.port
}

output "db_name" {
  value = aws_db_instance.mysql.db_name
}

output "db_username" {
  value = aws_db_instance.mysql.username
}