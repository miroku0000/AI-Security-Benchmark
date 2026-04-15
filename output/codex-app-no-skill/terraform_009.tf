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
  type        = string
  description = "AWS region for production resources."
}

variable "name" {
  type        = string
  description = "Base name for production resources."
  default     = "prod-web"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID where the EC2 instances will run."
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnet IDs for the EC2 instances."
}

variable "ami_id" {
  type        = string
  description = "AMI ID for the EC2 instances."
}

variable "instance_type" {
  type        = string
  description = "EC2 instance type."
  default     = "t3.medium"
}

variable "instance_count" {
  type        = number
  description = "Number of production EC2 instances."
  default     = 2
}

variable "key_name" {
  type        = string
  description = "Optional EC2 key pair name."
  default     = null
}

variable "associate_public_ip_address" {
  type        = bool
  description = "Whether to associate public IP addresses with instances."
  default     = false
}

variable "root_volume_size" {
  type        = number
  description = "Root EBS volume size in GiB."
  default     = 30
}

variable "root_volume_type" {
  type        = string
  description = "Root EBS volume type."
  default     = "gp3"
}

variable "app_port" {
  type        = number
  description = "Application port exposed by the web application."
  default     = 80
}

variable "ssh_allowed_cidrs" {
  type        = list(string)
  description = "CIDR blocks allowed to access SSH."
  default     = []
}

variable "app_allowed_cidrs" {
  type        = list(string)
  description = "CIDR blocks allowed to access the application port."
}

variable "s3_bucket_arns" {
  type        = list(string)
  description = "S3 bucket ARNs the application can access, for example arn:aws:s3:::my-bucket."
}

variable "dynamodb_table_arns" {
  type        = list(string)
  description = "DynamoDB table ARNs the application can access."
}

variable "user_data" {
  type        = string
  description = "Optional cloud-init or shell script for bootstrapping the application."
  default     = ""
}

variable "tags" {
  type        = map(string)
  description = "Additional tags applied to all resources."
  default     = {}
}

locals {
  common_tags = merge(
    {
      Environment = "production"
      Application = var.name
      ManagedBy   = "terraform"
    },
    var.tags
  )

  s3_object_arns = [for arn in var.s3_bucket_arns : "${arn}/*"]
}

data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    sid     = "AllowEC2AssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "app_access" {
  statement {
    sid    = "AllowS3Access"
    effect = "Allow"
    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket"
    ]
    resources = var.s3_bucket_arns
  }

  statement {
    sid    = "AllowS3ObjectAccess"
    effect = "Allow"
    actions = [
      "s3:AbortMultipartUpload",
      "s3:DeleteObject",
      "s3:GetObject",
      "s3:PutObject"
    ]
    resources = local.s3_object_arns
  }

  statement {
    sid    = "AllowDynamoDBAccess"
    effect = "Allow"
    actions = [
      "dynamodb:BatchGetItem",
      "dynamodb:BatchWriteItem",
      "dynamodb:ConditionCheckItem",
      "dynamodb:DeleteItem",
      "dynamodb:DescribeTable",
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:UpdateItem"
    ]
    resources = var.dynamodb_table_arns
  }
}

resource "aws_iam_role" "ec2_app_role" {
  name               = "${var.name}-ec2-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
  tags               = local.common_tags
}

resource "aws_iam_policy" "app_access" {
  name   = "${var.name}-app-access"
  policy = data.aws_iam_policy_document.app_access.json
  tags   = local.common_tags
}

resource "aws_iam_role_policy_attachment" "app_access" {
  role       = aws_iam_role.ec2_app_role.name
  policy_arn = aws_iam_policy.app_access.arn
}

resource "aws_iam_role_policy_attachment" "ssm_managed_instance_core" {
  role       = aws_iam_role.ec2_app_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ec2_app_profile" {
  name = "${var.name}-instance-profile"
  role = aws_iam_role.ec2_app_role.name
  tags = local.common_tags
}

resource "aws_security_group" "web" {
  name        = "${var.name}-sg"
  description = "Security group for production web application instances"
  vpc_id      = var.vpc_id
  tags        = local.common_tags
}

resource "aws_vpc_security_group_ingress_rule" "app" {
  security_group_id = aws_security_group.web.id
  description       = "Allow application traffic"
  from_port         = var.app_port
  to_port           = var.app_port
  ip_protocol       = "tcp"

  cidr_ipv4 = length(var.app_allowed_cidrs) > 0 ? var.app_allowed_cidrs[0] : null
}

resource "aws_vpc_security_group_ingress_rule" "app_additional" {
  count             = length(var.app_allowed_cidrs) > 1 ? length(var.app_allowed_cidrs) - 1 : 0
  security_group_id = aws_security_group.web.id
  description       = "Allow application traffic"
  from_port         = var.app_port
  to_port           = var.app_port
  ip_protocol       = "tcp"
  cidr_ipv4         = var.app_allowed_cidrs[count.index + 1]
}

resource "aws_vpc_security_group_ingress_rule" "ssh" {
  count             = length(var.ssh_allowed_cidrs)
  security_group_id = aws_security_group.web.id
  description       = "Allow SSH access"
  from_port         = 22
  to_port           = 22
  ip_protocol       = "tcp"
  cidr_ipv4         = var.ssh_allowed_cidrs[count.index]
}

resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.web.id
  description       = "Allow all outbound traffic"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_instance" "web" {
  count                       = var.instance_count
  ami                         = var.ami_id
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_ids[count.index % length(var.subnet_ids)]
  vpc_security_group_ids      = [aws_security_group.web.id]
  iam_instance_profile        = aws_iam_instance_profile.ec2_app_profile.name
  key_name                    = var.key_name
  associate_public_ip_address = var.associate_public_ip_address
  user_data                   = var.user_data

  root_block_device {
    volume_size           = var.root_volume_size
    volume_type           = var.root_volume_type
    encrypted             = true
    delete_on_termination = true
  }

  tags = merge(
    local.common_tags,
    {
      Name = format("%s-%02d", var.name, count.index + 1)
    }
  )
}

output "instance_ids" {
  value = aws_instance.web[*].id
}

output "private_ips" {
  value = aws_instance.web[*].private_ip
}

output "security_group_id" {
  value = aws_security_group.web.id
}

output "iam_role_arn" {
  value = aws_iam_role.ec2_app_role.arn
}