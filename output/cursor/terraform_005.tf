terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used to name resources"
  type        = string
  default     = "app-logs"
}

variable "log_bucket_name" {
  description = "Name of the S3 bucket for application logs and user data"
  type        = string
}

variable "ec2_role_arn" {
  description = "IAM role ARN assumed by EC2 instances that need write access to the bucket"
  type        = string
}

data "aws_caller_identity" "current" {}

locals {
  log_bucket_name = var.log_bucket_name
}

resource "aws_s3_bucket" "logs" {
  bucket = local.log_bucket_name

  tags = {
    Name        = local.log_bucket_name
    Project     = var.project_name
    Environment = "dev"
  }
}

resource "aws_s3_bucket_ownership_controls" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

data "aws_iam_policy_document" "logs_bucket_policy" {
  statement {
    sid = "AllowEc2InstancesToWriteLogs"

    principals {
      type        = "AWS"
      identifiers = [var.ec2_role_arn]
    }

    actions = [
      "s3:PutObject",
      "s3:PutObjectAcl",
      "s3:AbortMultipartUpload",
    ]

    resources = [
      "${aws_s3_bucket.logs.arn}/*"
    ]
  }
}

resource "aws_s3_bucket_policy" "logs" {
  bucket = aws_s3_bucket.logs.id
  policy = data.aws_iam_policy_document.logs_bucket_policy.json
}