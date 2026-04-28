I’m checking whether the repo already has a Terraform location or conventions so I can add a clean runnable baseline without colliding with generated benchmark artifacts.

No existing IaC scaffold is present, so I’m adding a fresh `terraform/` module with sane defaults and wiring the core AWS pieces together.

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
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "core-app"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  type    = list(string)
  default = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  type    = list(string)
  default = ["10.0.11.0/24", "10.0.12.0/24"]
}

variable "ec2_instance_count" {
  type    = number
  default = 2
}

variable "ec2_instance_type" {
  type    = string
  default = "t3.micro"
}

variable "ssh_key_name" {
  type    = string
  default = null
}

variable "admin_cidr_blocks" {
  type    = list(string)
  default = []
}

variable "db_name" {
  type    = string
  default = "appdb"
}

variable "db_username" {
  type    = string
  default = "appuser"
}

variable "db_instance_class" {
  type    = string
  default = "db.t3.micro"
}

variable "db_allocated_storage" {
  type    = number
  default = 20
}

variable "skip_final_snapshot" {
  type    = bool
  default = true
}

variable "deletion_protection" {
  type    = bool
  default = false
}

variable "common_tags" {
  type    = map(string)
  default = {}
}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023*-x86_64"]
  }

  filter {
    name   = "root-device-type"
    values = ["ebs"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    },
    var.common_tags
  )
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "random_password" "db" {
  length           = 24
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-vpc"
  })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-igw"
  })
}

resource "aws_subnet" "public" {
  count = length(var.public_subnet_cidrs)

  vpc_id                  = aws_vpc.this.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = data.aws_availability_zones.available.names[count.index % length(data.aws_availability_zones.available.names)]
  map_public_ip_on_launch = true

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-public-${count.index + 1}"
    Tier = "public"
  })
}

resource "aws_subnet" "private" {
  count = length(var.private_subnet_cidrs)

  vpc_id            = aws_vpc.this.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = data.aws_availability_zones.available.names[count.index % length(data.aws_availability_zones.available.names)]

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-private-${count.index + 1}"
    Tier = "private"
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-public-rt"
  })
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.this.id

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-private-rt"
  })
}

resource "aws_route_table_association" "public" {
  count = length(var.public_subnet_cidrs)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count = length(var.private_subnet_cidrs)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

resource "aws_security_group" "ec2" {
  name        = "${local.name_prefix}-ec2-sg"
  description = "EC2 security group"
  vpc_id      = aws_vpc.this.id

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-ec2-sg"
  })
}

resource "aws_vpc_security_group_egress_rule" "ec2_all" {
  security_group_id = aws_security_group.ec2.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_vpc_security_group_ingress_rule" "ec2_http" {
  security_group_id = aws_security_group.ec2.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "ec2_https" {
  security_group_id = aws_security_group.ec2.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "ec2_ssh" {
  count = length(var.admin_cidr_blocks)

  security_group_id = aws_security_group.ec2.id
  cidr_ipv4         = var.admin_cidr_blocks[count.index]
  from_port         = 22
  to_port           = 22
  ip_protocol       = "tcp"
}

resource "aws_security_group" "rds" {
  name        = "${local.name_prefix}-rds-sg"
  description = "RDS security group"
  vpc_id      = aws_vpc.this.id

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-rds-sg"
  })
}

resource "aws_vpc_security_group_egress_rule" "rds_all" {
  security_group_id = aws_security_group.rds.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_vpc_security_group_ingress_rule" "rds_postgres" {
  security_group_id            = aws_security_group.rds.id
  referenced_security_group_id = aws_security_group.ec2.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}

resource "aws_instance" "app" {
  count = var.ec2_instance_count

  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.ec2_instance_type
  subnet_id              = aws_subnet.public[count.index % length(var.public_subnet_cidrs)].id
  vpc_security_group_ids = [aws_security_group.ec2.id]
  key_name               = var.ssh_key_name

  user_data = <<-EOT
    #!/bin/bash
    dnf update -y
    dnf install -y nginx
    systemctl enable nginx
    systemctl start nginx
  EOT

  root_block_device {
    encrypted   = true
    volume_size = 20
    volume_type = "gp3"
  }

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-app-${count.index + 1}"
    Role = "application"
  })
}

resource "aws_db_subnet_group" "this" {
  name       = "${replace(local.name_prefix, "_", "-")}-db-subnets"
  subnet_ids = aws_subnet.private[*].id

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-db-subnets"
  })
}

resource "aws_db_instance" "this" {
  identifier              = "${replace(local.name_prefix, "_", "-")}-postgres"
  allocated_storage       = var.db_allocated_storage
  max_allocated_storage   = var.db_allocated_storage * 5
  db_name                 = var.db_name
  engine                  = "postgres"
  instance_class          = var.db_instance_class
  username                = var.db_username
  password                = random_password.db.result
  db_subnet_group_name    = aws_db_subnet_group.this.name
  vpc_security_group_ids  = [aws_security_group.rds.id]
  storage_encrypted       = true
  storage_type            = "gp3"
  backup_retention_period = 7
  skip_final_snapshot     = var.skip_final_snapshot
  deletion_protection     = var.deletion_protection
  publicly_accessible     = false
  apply_immediately       = true
  multi_az                = false

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-postgres"
  })
}

resource "aws_s3_bucket" "app" {
  bucket = lower("${local.name_prefix}-app-${random_id.bucket_suffix.hex}")

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-app"
  })
}

resource "aws_s3_bucket_versioning" "app" {
  bucket = aws_s3_bucket.app.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "app" {
  bucket = aws_s3_bucket.app.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "app" {
  bucket = aws_s3_bucket.app.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket" "artifacts" {
  bucket = lower("${local.name_prefix}-artifacts-${random_id.bucket_suffix.hex}")

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-artifacts"
  })
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "vpc_id" {
  value = aws_vpc.this.id
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}

output "ec2_instance_ids" {
  value = aws_instance.app[*].id
}

output "ec2_public_ips" {
  value = aws_instance.app[*].public_ip
}

output "rds_endpoint" {
  value = aws_db_instance.this.endpoint
}

output "rds_database_name" {
  value = var.db_name
}

output "rds_master_username" {
  value = var.db_username
}

output "rds_master_password" {
  value     = random_password.db.result
  sensitive = true
}

output "app_bucket_name" {
  value = aws_s3_bucket.app.bucket
}

output "artifacts_bucket_name" {
  value = aws_s3_bucket.artifacts.bucket
}