terraform {
  required_version = ">= 1.0.0"

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
  description = "AWS region to deploy resources in"
  type        = string
  default     = "us-east-1"
}

variable "bucket_name" {
  description = "Name of the S3 bucket for user uploads"
  type        = string
}

variable "app_principal_arn" {
  description = "ARN of the IAM role or user used by the web application"
  type        = string
}

resource "aws_s3_bucket" "user_uploads" {
  bucket = var.bucket_name

  tags = {
    Name = "user-uploads"
    Env  = "mvp"
  }
}

resource "aws_s3_bucket_ownership_controls" "user_uploads" {
  bucket = aws_s3_bucket.user_uploads.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_public_access_block" "user_uploads" {
  bucket = aws_s3_bucket.user_uploads.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "user_uploads" {
  bucket = aws_s3_bucket.user_uploads.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "user_uploads" {
  bucket = aws_s3_bucket.user_uploads.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

data "aws_iam_policy_document" "user_uploads_app_access" {
  statement {
    sid    = "AppFullAccessToUploads"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [var.app_principal_arn]
    }

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket"
    ]

    resources = [
      aws_s3_bucket.user_uploads.arn,
      "${aws_s3_bucket.user_uploads.arn}/*"
    ]
  }
}

resource "aws_s3_bucket_policy" "user_uploads" {
  bucket = aws_s3_bucket.user_uploads.id
  policy = data.aws_iam_policy_document.user_uploads_app_access.json
}