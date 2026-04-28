I’m checking whether the repo already has Terraform conventions or an infra layout so I can drop in something runnable without guessing the wrong structure.

There isn’t an existing Terraform module layout here, so I’m adding a self-contained module under a new `terraform/` path and validating it directly.

The repo itself looks read-only in this environment, so I’m switching to generating and validating the Terraform module in session storage, then I’ll return the finished code directly.

The Terraform CLI itself is blocked from running here, so I’m sanity-checking the module by inspection and tightening anything that could be provider-sensitive before I return it.

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region for the RDS deployment."
  type        = string
}

variable "name_prefix" {
  description = "Prefix applied to created resources."
  type        = string
  default     = "app"
}

variable "vpc_id" {
  description = "VPC ID where the database will be deployed."
  type        = string
}

variable "db_subnet_ids" {
  description = "Subnet IDs for the DB subnet group. Use subnets that support a publicly accessible RDS instance."
  type        = list(string)

  validation {
    condition     = length(var.db_subnet_ids) >= 2
    error_message = "Provide at least two subnet IDs in different Availability Zones."
  }
}

variable "allowed_ec2_security_group_ids" {
  description = "Security group IDs attached to application EC2 instances that need database access."
  type        = set(string)

  validation {
    condition     = length(var.allowed_ec2_security_group_ids) > 0
    error_message = "Provide at least one EC2 security group ID that requires database access."
  }
}

variable "developer_cidr_blocks" {
  description = "Trusted developer public CIDR blocks allowed to connect for debugging."
  type        = set(string)

  validation {
    condition = length(var.developer_cidr_blocks) > 0 && alltrue([
      for cidr in var.developer_cidr_blocks : cidr != "0.0.0.0/0"
    ])
    error_message = "Provide at least one trusted developer CIDR block and do not allow 0.0.0.0/0."
  }
}

variable "db_name" {
  description = "Initial database name."
  type        = string
  default     = "appdb"
}

variable "db_username" {
  description = "Master username for the PostgreSQL instance."
  type        = string
  default     = "app_admin"
}

variable "instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.m6g.large"
}

variable "allocated_storage" {
  description = "Initial storage allocation in GiB."
  type        = number
  default     = 100
}

variable "max_allocated_storage" {
  description = "Maximum autoscaled storage size in GiB."
  type        = number
  default     = 500
}

variable "postgres_major_version" {
  description = "PostgreSQL major engine version."
  type        = string
  default     = "16"
}

variable "backup_retention_period" {
  description = "Number of days to retain automated backups."
  type        = number
  default     = 14
}

variable "preferred_backup_window" {
  description = "Daily backup window in UTC."
  type        = string
  default     = "03:00-04:00"
}

variable "preferred_maintenance_window" {
  description = "Weekly maintenance window in UTC."
  type        = string
  default     = "sun:04:00-sun:05:00"
}

variable "performance_insights_retention_period" {
  description = "Performance Insights retention in days."
  type        = number
  default     = 7
}

variable "monitoring_interval" {
  description = "Enhanced monitoring interval in seconds."
  type        = number
  default     = 60
}

variable "deletion_protection" {
  description = "Enable deletion protection on the database."
  type        = bool
  default     = true
}

locals {
  identifier = "${var.name_prefix}-postgres"
  common_tags = {
    Name        = local.identifier
    Environment = "production"
    ManagedBy   = "terraform"
    Service     = "postgresql"
  }
}

data "aws_partition" "current" {}

resource "aws_db_subnet_group" "this" {
  name       = "${local.identifier}-subnets"
  subnet_ids = var.db_subnet_ids

  tags = merge(local.common_tags, {
    Name = "${local.identifier}-subnets"
  })
}

resource "aws_security_group" "db" {
  name        = "${local.identifier}-sg"
  description = "Access control for the PostgreSQL RDS instance."
  vpc_id      = var.vpc_id

  tags = merge(local.common_tags, {
    Name = "${local.identifier}-sg"
  })
}

resource "aws_vpc_security_group_ingress_rule" "from_ec2" {
  for_each = var.allowed_ec2_security_group_ids

  security_group_id            = aws_security_group.db.id
  referenced_security_group_id = each.value
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  description                  = "PostgreSQL access from application EC2 instances."
}

resource "aws_vpc_security_group_ingress_rule" "from_developers" {
  for_each = var.developer_cidr_blocks

  security_group_id = aws_security_group.db.id
  cidr_ipv4         = each.value
  from_port         = 5432
  to_port           = 5432
  ip_protocol       = "tcp"
  description       = "Restricted PostgreSQL access for developer debugging."
}

resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.db.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
  description       = "Allow outbound connectivity as needed."
}

resource "aws_iam_role" "enhanced_monitoring" {
  name = "${local.identifier}-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "enhanced_monitoring" {
  role       = aws_iam_role.enhanced_monitoring.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

resource "aws_db_parameter_group" "postgres" {
  name        = "${local.identifier}-pg${var.postgres_major_version}"
  family      = "postgres${var.postgres_major_version}"
  description = "Production parameter group for ${local.identifier}."

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  tags = local.common_tags
}

resource "random_id" "snapshot_suffix" {
  byte_length = 4
}

resource "aws_db_instance" "postgres" {
  identifier                            = local.identifier
  engine                                = "postgres"
  engine_version                        = var.postgres_major_version
  instance_class                        = var.instance_class
  db_name                               = var.db_name
  username                              = var.db_username
  manage_master_user_password           = true
  port                                  = 5432
  allocated_storage                     = var.allocated_storage
  max_allocated_storage                 = var.max_allocated_storage
  storage_type                          = "gp3"
  storage_encrypted                     = true
  multi_az                              = true
  network_type                          = "IPV4"
  db_subnet_group_name                  = aws_db_subnet_group.this.name
  vpc_security_group_ids                = [aws_security_group.db.id]
  parameter_group_name                  = aws_db_parameter_group.postgres.name
  publicly_accessible                   = true
  backup_retention_period               = var.backup_retention_period
  backup_window                         = var.preferred_backup_window
  maintenance_window                    = var.preferred_maintenance_window
  copy_tags_to_snapshot                 = true
  auto_minor_version_upgrade            = true
  deletion_protection                   = var.deletion_protection
  delete_automated_backups              = false
  skip_final_snapshot                   = false
  final_snapshot_identifier             = "${local.identifier}-final-${random_id.snapshot_suffix.hex}"
  performance_insights_enabled          = true
  performance_insights_retention_period = var.performance_insights_retention_period
  enabled_cloudwatch_logs_exports       = ["postgresql", "upgrade"]
  monitoring_interval                   = var.monitoring_interval
  monitoring_role_arn                   = aws_iam_role.enhanced_monitoring.arn
  apply_immediately                     = false
  allow_major_version_upgrade           = false
  iam_database_authentication_enabled   = true

  depends_on = [aws_iam_role_policy_attachment.enhanced_monitoring]

  tags = local.common_tags
}

output "db_endpoint" {
  description = "PostgreSQL endpoint for application and developer access."
  value       = aws_db_instance.postgres.address
}

output "db_port" {
  description = "PostgreSQL port."
  value       = aws_db_instance.postgres.port
}

output "db_name" {
  description = "Initial database name."
  value       = aws_db_instance.postgres.db_name
}

output "db_master_username" {
  description = "Master username."
  value       = aws_db_instance.postgres.username
}

output "db_master_secret_arn" {
  description = "Secrets Manager ARN containing the generated master password."
  value       = aws_db_instance.postgres.master_user_secret[0].secret_arn
}

output "db_security_group_id" {
  description = "Security group protecting the database."
  value       = aws_security_group.db.id
}