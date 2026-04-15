terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  type        = string
  description = "AWS region for RDS"
  default     = "us-east-1"
}

variable "allowed_cidr_blocks" {
  type        = list(string)
  description = "CIDR blocks allowed to connect to MySQL (e.g. office/VPN); use 0.0.0.0/0 only for broad dev access"
  default     = ["0.0.0.0/0"]
}

variable "db_instance_class" {
  type    = string
  default = "db.t3.micro"
}

variable "allocated_storage" {
  type    = number
  default = 20
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }

  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

resource "aws_db_subnet_group" "app" {
  name       = "app-mysql-subnet-group"
  subnet_ids = data.aws_subnets.default.ids

  tags = {
    Name = "app-mysql-subnet-group"
  }
}

resource "aws_security_group" "rds_mysql" {
  name        = "app-mysql-rds-sg"
  description = "MySQL access for application RDS (development)"
  vpc_id      = data.aws_vpc.default.id

  dynamic "ingress" {
    for_each = var.allowed_cidr_blocks
    content {
      description = "MySQL from allowed CIDR"
      from_port   = 3306
      to_port     = 3306
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "app-mysql-rds-sg"
  }
}

resource "aws_db_instance" "app" {
  identifier = "app-mysql"

  engine               = "mysql"
  engine_version       = "8.0"
  instance_class       = var.db_instance_class
  allocated_storage    = var.allocated_storage
  storage_type         = "gp3"
  db_subnet_group_name = aws_db_subnet_group.app.name
  vpc_security_group_ids = [
    aws_security_group.rds_mysql.id,
  ]

  db_name  = "appdb"
  username = "admin"
  password = "AppDB2024!"

  publicly_accessible     = true
  multi_az                = false
  backup_retention_period = 1
  skip_final_snapshot     = true
  deletion_protection     = false

  tags = {
    Name = "app-mysql"
  }
}

output "rds_endpoint" {
  value       = aws_db_instance.app.endpoint
  description = "MySQL endpoint host:port"
}

output "rds_address" {
  value       = aws_db_instance.app.address
  description = "MySQL hostname"
}

output "rds_port" {
  value       = aws_db_instance.app.port
  description = "MySQL port"
}

output "database_name" {
  value       = aws_db_instance.app.db_name
  description = "Initial database name"
}