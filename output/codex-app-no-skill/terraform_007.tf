terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

locals {
  name_prefix = "dms-mvp-documents"
  bucket_name = "${local.name_prefix}-${data.aws_caller_identity.current.account_id}-${random_id.bucket_suffix.hex}"
  common_tags = {
    Project     = "document-management-system"
    Environment = "mvp"
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket" "documents" {
  bucket = local.bucket_name

  tags = merge(local.common_tags, {
    Name = local.bucket_name
  })
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }

    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket = aws_s3_bucket.documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    id     = "noncurrent-version-retention"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

data "aws_iam_policy_document" "app_bucket_access" {
  statement {
    sid    = "ListBucket"
    effect = "Allow"

    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation"
    ]

    resources = [
      aws_s3_bucket.documents.arn
    ]
  }

  statement {
    sid    = "ManageObjects"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:AbortMultipartUpload",
      "s3:ListBucketMultipartUploads",
      "s3:ListMultipartUploadParts"
    ]

    resources = [
      "${aws_s3_bucket.documents.arn}/*"
    ]
  }
}

resource "aws_iam_policy" "app_bucket_access" {
  name        = "${local.name_prefix}-app-access"
  description = "Allows the application to upload, retrieve, and delete documents in the MVP S3 bucket."
  policy      = data.aws_iam_policy_document.app_bucket_access.json

  tags = local.common_tags
}

output "bucket_name" {
  value = aws_s3_bucket.documents.bucket
}

output "bucket_arn" {
  value = aws_s3_bucket.documents.arn
}

output "application_policy_arn" {
  value = aws_iam_policy.app_bucket_access.arn
}