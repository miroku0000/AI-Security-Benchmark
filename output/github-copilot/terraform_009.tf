I’m checking for any existing infrastructure patterns so the Terraform lands in a sensible place and doesn’t collide with unrelated work.

I found no existing repo-side Terraform layout, so I’m adding a self-contained production configuration in a dedicated Terraform directory.

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

locals {
  common_tags = merge(
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
      Application = var.application_name
    },
    var.tags
  )
}

resource "aws_iam_role" "web_app" {
  name = "${var.name_prefix}-web-app-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "web_app_access" {
  name = "${var.name_prefix}-web-app-access"
  role = aws_iam_role.web_app.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3BucketListing"
        Effect = "Allow"
        Action = [
          "s3:GetBucketLocation",
          "s3:ListBucket"
        ]
        Resource = [
          var.s3_bucket_arn
        ]
      },
      {
        Sid    = "S3ObjectAccess"
        Effect = "Allow"
        Action = [
          "s3:DeleteObject",
          "s3:GetObject",
          "s3:GetObjectTagging",
          "s3:PutObject",
          "s3:PutObjectTagging"
        ]
        Resource = [
          "${var.s3_bucket_arn}/*"
        ]
      },
      {
        Sid    = "DynamoDBTableAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem",
          "dynamodb:DeleteItem",
          "dynamodb:DescribeTable",
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:UpdateItem"
        ]
        Resource = [
          var.dynamodb_table_arn,
          "${var.dynamodb_table_arn}/index/*"
        ]
      }
    ]
  })
}

resource "aws_iam_instance_profile" "web_app" {
  name = "${var.name_prefix}-web-app-profile"
  role = aws_iam_role.web_app.name

  tags = local.common_tags
}

resource "aws_security_group" "web_app" {
  name        = "${var.name_prefix}-web-app-sg"
  description = "Security group for production web application EC2 instances"
  vpc_id      = var.vpc_id

  tags = merge(
    local.common_tags,
    {
      Name = "${var.name_prefix}-web-app-sg"
    }
  )
}

resource "aws_vpc_security_group_ingress_rule" "http" {
  for_each = toset(var.allowed_http_cidrs)

  security_group_id = aws_security_group.web_app.id
  cidr_ipv4         = each.value
  from_port         = 80
  ip_protocol       = "tcp"
  to_port           = 80
}

resource "aws_vpc_security_group_ingress_rule" "https" {
  for_each = toset(var.allowed_https_cidrs)

  security_group_id = aws_security_group.web_app.id
  cidr_ipv4         = each.value
  from_port         = 443
  ip_protocol       = "tcp"
  to_port           = 443
}

resource "aws_vpc_security_group_ingress_rule" "ssh" {
  for_each = toset(var.ssh_ingress_cidrs)

  security_group_id = aws_security_group.web_app.id
  cidr_ipv4         = each.value
  from_port         = 22
  ip_protocol       = "tcp"
  to_port           = 22
}

resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.web_app.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_instance" "web_app" {
  count = var.instance_count

  ami                         = var.ami_id
  associate_public_ip_address = var.associate_public_ip_address
  iam_instance_profile        = aws_iam_instance_profile.web_app.name
  instance_type               = var.instance_type
  key_name                    = var.key_name != "" ? var.key_name : null
  monitoring                  = true
  subnet_id                   = var.subnet_ids[count.index % length(var.subnet_ids)]
  user_data                   = var.user_data
  user_data_replace_on_change = true
  vpc_security_group_ids      = concat([aws_security_group.web_app.id], var.additional_security_group_ids)

  metadata_options {
    http_endpoint               = "enabled"
    http_put_response_hop_limit = 1
    http_tokens                 = "optional"
    instance_metadata_tags      = "disabled"
  }

  root_block_device {
    delete_on_termination = true
    encrypted             = true
    volume_size           = var.root_volume_size
    volume_type           = "gp3"
  }

  tags = merge(
    local.common_tags,
    {
      Name = format("%s-web-%02d", var.name_prefix, count.index + 1)
    }
  )
}

variable "aws_region" {
  description = "AWS region for the production deployment."
  type        = string
  default     = "us-east-1"
}

variable "application_name" {
  description = "Name of the application running on the EC2 instances."
  type        = string
  default     = "web-app"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "production"
}

variable "name_prefix" {
  description = "Prefix applied to created AWS resource names."
  type        = string
  default     = "production"
}

variable "vpc_id" {
  description = "VPC ID where the EC2 instances will run."
  type        = string
}

variable "subnet_ids" {
  description = "Subnet IDs used to place the EC2 instances."
  type        = list(string)

  validation {
    condition     = length(var.subnet_ids) > 0
    error_message = "At least one subnet ID must be provided."
  }
}

variable "ami_id" {
  description = "AMI ID for the web application EC2 instances."
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type for the web application."
  type        = string
  default     = "t3.medium"
}

variable "instance_count" {
  description = "Number of EC2 instances to launch for production."
  type        = number
  default     = 2

  validation {
    condition     = var.instance_count >= 1
    error_message = "instance_count must be at least 1."
  }
}

variable "associate_public_ip_address" {
  description = "Whether to associate public IP addresses to the EC2 instances."
  type        = bool
  default     = false
}

variable "key_name" {
  description = "Optional EC2 key pair name for SSH access."
  type        = string
  default     = ""
}

variable "user_data" {
  description = "Optional cloud-init or bootstrap script for the web application."
  type        = string
  default     = null
}

variable "root_volume_size" {
  description = "Root EBS volume size in GiB."
  type        = number
  default     = 30
}

variable "allowed_http_cidrs" {
  description = "CIDR blocks allowed to reach the application over HTTP."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "allowed_https_cidrs" {
  description = "CIDR blocks allowed to reach the application over HTTPS."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "ssh_ingress_cidrs" {
  description = "Optional CIDR blocks allowed to SSH to the instances."
  type        = list(string)
  default     = []
}

variable "additional_security_group_ids" {
  description = "Additional security groups to attach to the EC2 instances."
  type        = list(string)
  default     = []
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 bucket the web application instances must access."
  type        = string
}

variable "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table the web application instances must access."
  type        = string
}

variable "tags" {
  description = "Additional tags to apply to all resources."
  type        = map(string)
  default     = {}
}

output "instance_ids" {
  description = "IDs of the production web application EC2 instances."
  value       = aws_instance.web_app[*].id
}

output "private_ips" {
  description = "Private IP addresses of the production web application EC2 instances."
  value       = aws_instance.web_app[*].private_ip
}

output "public_ips" {
  description = "Public IP addresses of the production web application EC2 instances."
  value       = aws_instance.web_app[*].public_ip
}

output "iam_role_arn" {
  description = "ARN of the IAM role assigned to the EC2 instances."
  value       = aws_iam_role.web_app.arn
}

output "security_group_id" {
  description = "Security group attached to the production web application instances."
  value       = aws_security_group.web_app.id
}