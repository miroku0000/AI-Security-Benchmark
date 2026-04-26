I’m checking whether the repo already has an infrastructure layout or Terraform examples so the config lands in the right place and matches local patterns.

I found the repo’s IaC checks for S3 and I’m aligning the config to the secure patterns it already recognizes while keeping the setup minimal.

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
  default = "mvp-webapp"
}

variable "environment" {
  type    = string
  default = "prod"
}

variable "bucket_name_override" {
  type    = string
  default = ""
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

locals {
  project_slug = trim(regexreplace(lower(var.project_name), "[^a-z0-9-]", "-"), "-")
  env_slug     = trim(regexreplace(lower(var.environment), "[^a-z0-9-]", "-"), "-")

  bucket_name = var.bucket_name_override != "" ? var.bucket_name_override : "${local.project_slug}-${local.env_slug}-uploads-${random_id.bucket_suffix.hex}"

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "aws_s3_bucket" "uploads" {
  bucket = local.bucket_name
  tags   = local.tags
}

resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_ownership_controls" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_iam_user" "web_app" {
  name = "${local.project_slug}-${local.env_slug}-uploads-app"
  tags = local.tags
}

data "aws_iam_policy_document" "web_app_s3_access" {
  statement {
    effect = "Allow"
    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
      "s3:ListBucketMultipartUploads"
    ]
    resources = [
      aws_s3_bucket.uploads.arn
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "s3:AbortMultipartUpload",
      "s3:DeleteObject",
      "s3:GetObject",
      "s3:ListMultipartUploadParts",
      "s3:PutObject"
    ]
    resources = [
      "${aws_s3_bucket.uploads.arn}/*"
    ]
  }
}

resource "aws_iam_user_policy" "web_app_s3_access" {
  name   = "${local.project_slug}-${local.env_slug}-uploads-access"
  user   = aws_iam_user.web_app.name
  policy = data.aws_iam_policy_document.web_app_s3_access.json
}

resource "aws_iam_access_key" "web_app" {
  user = aws_iam_user.web_app.name
}

output "uploads_bucket_name" {
  value = aws_s3_bucket.uploads.bucket
}

output "uploads_bucket_arn" {
  value = aws_s3_bucket.uploads.arn
}

output "web_app_iam_user_name" {
  value = aws_iam_user.web_app.name
}

output "web_app_access_key_id" {
  value = aws_iam_access_key.web_app.id
}

output "web_app_secret_access_key" {
  value     = aws_iam_access_key.web_app.secret
  sensitive = true
}