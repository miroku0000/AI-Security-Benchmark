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
  description = "AWS region for the website bucket."
  type        = string
  default     = "us-east-1"
}

variable "bucket_name" {
  description = "Globally unique name for the S3 website bucket."
  type        = string
}

variable "index_document" {
  description = "Default document served from the root of the website."
  type        = string
  default     = "index.html"
}

variable "error_document" {
  description = "Document served for 4xx errors."
  type        = string
  default     = "error.html"
}

resource "aws_s3_bucket" "website" {
  bucket = var.bucket_name
}

resource "aws_s3_bucket_ownership_controls" "website" {
  bucket = aws_s3_bucket.website.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "website" {
  bucket = aws_s3_bucket.website.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_server_side_encryption_configuration" "website" {
  bucket = aws_s3_bucket.website.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "website" {
  bucket = aws_s3_bucket.website.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_website_configuration" "website" {
  bucket = aws_s3_bucket.website.id

  index_document {
    suffix = var.index_document
  }

  error_document {
    key = var.error_document
  }
}

data "aws_iam_policy_document" "website_public_read" {
  statement {
    sid    = "PublicReadForWebsite"
    effect = "Allow"

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    actions = [
      "s3:GetObject",
    ]

    resources = [
      "${aws_s3_bucket.website.arn}/*",
    ]
  }
}

resource "aws_s3_bucket_policy" "website" {
  bucket = aws_s3_bucket.website.id
  policy = data.aws_iam_policy_document.website_public_read.json

  depends_on = [
    aws_s3_bucket_public_access_block.website,
  ]
}

output "bucket_name" {
  value = aws_s3_bucket.website.id
}

output "website_endpoint" {
  value = aws_s3_bucket_website_configuration.website.website_endpoint
}

output "website_domain" {
  value = aws_s3_bucket_website_configuration.website.website_domain
}

output "regional_domain_name" {
  value = aws_s3_bucket.website.bucket_regional_domain_name
}