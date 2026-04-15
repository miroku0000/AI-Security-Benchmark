provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region to deploy resources in"
  type        = string
  default     = "us-east-1"
}

variable "vpc_id" {
  description = "ID of the VPC where RDS will be created"
  type        = string
}

variable "db_subnet_ids" {
  description = "List of private subnet IDs for RDS subnet group"
  type        = list(string)
}

variable "app_ec2_security_group_id" {
  description = "Security group ID attached to the application EC2 instances"
  type        = string
}

variable "developer_cidr_blocks" {
  description = "List of developer IP CIDR blocks allowed to access the DB (e.g., [\"203.0.113.10/32\"])"
  type        = list(string)
}

variable "db_name" {
  description = "Initial PostgreSQL database name"
  type        = string
  default     = "appdb"
}

variable "db_username" {
  description = "Master username for the PostgreSQL database"
  type        = string
  default     = "app_user"
}

variable "db_password" {
  description = "Master password for the PostgreSQL database"
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "Instance class for the PostgreSQL RDS instance"
  type        = string
  default     = "db.m6g.large"
}

variable "db_allocated_storage" {
  description = "Allocated storage in GB for the RDS instance"
  type        = number
  default     = 100
}

variable "db_max_allocated_storage" {
  description = "Maximum storage in GB for autoscaling"
  type        = number
  default     = 1000
}

variable "db_backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 7
}

variable "db_maintenance_window" {
  description = "Preferred maintenance window in UTC, e.g., sun:03:00-sun:04:00"
  type        = string
  default     = "sun:03:00-sun:04:00"
}

variable "db_backup_window" {
  description = "Preferred backup window in UTC, e.g., 02:00-03:00"
  type        = string
  default     = "02:00-03:00"
}

variable "db_multi_az" {
  description = "Enable Multi-AZ deployment for high availability"
  type        = bool
  default     = true
}

variable "db_storage_type" {
  description = "Storage type for RDS (gp3 recommended)"
  type        = string
  default     = "gp3"
}

variable "db_port" {
  description = "Port on which PostgreSQL will listen"
  type        = number
  default     = 5432
}

variable "environment" {
  description = "Environment name (e.g., prod, staging)"
  type        = string
  default     = "prod"
}

resource "aws_security_group" "rds" {
  name        = "rds-postgres-${var.environment}"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL from application EC2 instances"
    from_port       = var.db_port
    to_port         = var.db_port
    protocol        = "tcp"
    security_groups = [var.app_ec2_security_group_id]
  }

  dynamic "ingress" {
    for_each = var.developer_cidr_blocks
    content {
      description = "PostgreSQL from developer workstation"
      from_port   = var.db_port
      to_port     = var.db_port
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    ipv6_cidr_blocks = []
  }

  tags = {
    Name        = "rds-postgres-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_db_subnet_group" "this" {
  name       = "rds-postgres-${var.environment}"
  subnet_ids = var.db_subnet_ids

  tags = {
    Name        = "rds-postgres-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_db_parameter_group" "postgres" {
  name        = "rds-postgres-${var.environment}"
  family      = "postgres16"
  description = "Custom parameter group for PostgreSQL ${var.environment}"

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  parameter {
    name  = "max_connections"
    value = "500"
  }

  tags = {
    Name        = "rds-postgres-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_db_instance" "postgres" {
  identifier = "app-postgres-${var.environment}"

  engine         = "postgres"
  engine_version = "16.4"

  instance_class = var.db_instance_class

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  port     = var.db_port

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_type          = var.db_storage_type
  storage_encrypted     = true

  multi_az               = var.db_multi_az
  publicly_accessible    = true
  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period = var.db_backup_retention_days
  backup_window           = var.db_backup_window
  maintenance_window      = var.db_maintenance_window

  deletion_protection      = true
  skip_final_snapshot      = false
  copy_tags_to_snapshot    = true
  auto_minor_version_upgrade = true

  performance_insights_enabled = true

  parameter_group_name = aws_db_parameter_group.postgres.name

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  tags = {
    Name        = "app-postgres-${var.environment}"
    Environment = var.environment
  }

  lifecycle {
    prevent_destroy = true
  }
}

output "db_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.postgres.endpoint
}

output "db_port" {
  description = "RDS PostgreSQL port"
  value       = aws_db_instance.postgres.port
}

output "db_address" {
  description = "RDS PostgreSQL address (hostname)"
  value       = aws_db_instance.postgres.address
}

output "rds_security_group_id" {
  description = "Security group ID associated with the RDS instance"
  value       = aws_security_group.rds.id
}