I’m checking whether there’s already an infrastructure layout or Terraform convention to fit into before I add the config.

I found there isn’t a checked-in Terraform layout here, so I’m adding a self-contained config from scratch.

I’ve got the shape: one self-contained Terraform file with providers, a generated bucket name, a bucket policy scoped to the EC2 role, and minimal safe defaults.

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
  description = "AWS region for the S3 bucket."
  type        = string
  default     = "us-east-1"
}

variable "bucket_name_prefix" {
  description = "Prefix used to build a globally unique bucket name."
  type        = string
  default     = "app-data-logs"
}

variable "ec2_instance_role_arn" {
  description = "IAM role ARN used by the EC2 instances that need to write application logs."
  type        = string
}

variable "tags" {
  description = "Tags applied to created resources."
  type        = map(string)
  default = {
    Name        = "application-data-bucket"
    Environment = "dev"
  }
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "application_data" {
  bucket = "${var.bucket_name_prefix}-${random_id.bucket_suffix.hex}"

  tags = merge(
    var.tags,
    {
      Purpose = "application-logs-and-user-data"
    }
  )
}

resource "aws_s3_bucket_public_access_block" "application_data" {
  bucket = aws_s3_bucket.application_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "logs_prefix" {
  bucket  = aws_s3_bucket.application_data.id
  key     = "logs/"
  content = ""
}

resource "aws_s3_object" "user_data_prefix" {
  bucket  = aws_s3_bucket.application_data.id
  key     = "user-data/"
  content = ""
}

data "aws_iam_policy_document" "application_data_bucket" {
  statement {
    sid    = "AllowEc2InstancesToWriteLogs"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [var.ec2_instance_role_arn]
    }

    actions = [
      "s3:PutObject",
      "s3:AbortMultipartUpload"
    ]

    resources = [
      "${aws_s3_bucket.application_data.arn}/logs/*"
    ]
  }

  statement {
    sid    = "AllowEc2InstancesToGetBucketLocation"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [var.ec2_instance_role_arn]
    }

    actions = [
      "s3:GetBucketLocation"
    ]

    resources = [
      aws_s3_bucket.application_data.arn
    ]
  }
}

resource "aws_s3_bucket_policy" "application_data" {
  bucket = aws_s3_bucket.application_data.id
  policy = data.aws_iam_policy_document.application_data_bucket.json
}

output "bucket_name" {
  description = "Name of the S3 bucket for application logs and user data."
  value       = aws_s3_bucket.application_data.bucket
}

output "bucket_arn" {
  description = "ARN of the S3 bucket for application logs and user data."
  value       = aws_s3_bucket.application_data.arn
}