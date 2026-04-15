terraform {
  required_version = ">= 1.0"
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
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

locals {
  bucket_name = "${var.bucket_name_prefix}-${var.environment}-${data.aws_caller_identity.current.account_id}-${random_id.bucket_suffix.hex}"
}

resource "aws_s3_bucket" "uploads" {
  bucket = local.bucket_name

  tags = merge(
    {
      Name        = local.bucket_name
      Environment = var.environment
      Purpose     = "user-uploads"
    },
    var.tags
  )
}

resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Suspended"
  }
}

resource "aws_s3_bucket_cors_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  cors_rule {
    allowed_origins = var.cors_allowed_origins
    allowed_methods = var.cors_allowed_methods
    allowed_headers = var.cors_allowed_headers
    expose_headers  = var.cors_expose_headers
    max_age_seconds = var.cors_max_age_seconds
  }
}

resource "aws_iam_user" "uploads_app" {
  name = "${var.app_iam_user_name}-${var.environment}"
  path = "/service-accounts/"

  tags = merge(
    {
      Environment = var.environment
      Purpose     = "user-uploads"
    },
    var.tags
  )
}

resource "aws_iam_access_key" "uploads_app" {
  user = aws_iam_user.uploads_app.name
}

resource "aws_iam_user_policy" "uploads_app_s3_policy" {
  name = "${var.app_iam_user_name}-${var.environment}-uploads-s3"
  user = aws_iam_user.uploads_app.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        length(var.s3_prefixes) > 0 ? {
          Sid    = "ListBucket"
          Effect = "Allow"
          Action = [
            "s3:ListBucket",
            "s3:GetBucketLocation"
          ]
          Resource = aws_s3_bucket.uploads.arn
          Condition = {
            StringLike = {
              "s3:prefix" = distinct(flatten([
                for p in var.s3_prefixes : [
                  trim(p, "/"),
                  "${trim(p, "/")}/*"
                ]
              ]))
            }
          }
        } : {
          Sid    = "ListBucket"
          Effect = "Allow"
          Action = [
            "s3:ListBucket",
            "s3:GetBucketLocation"
          ]
          Resource = aws_s3_bucket.uploads.arn
        }
      ],
      [
        {
          Sid    = "ObjectReadWrite"
          Effect = "Allow"
          Action = [
            "s3:GetObject",
            "s3:PutObject",
            "s3:DeleteObject",
            "s3:AbortMultipartUpload",
            "s3:ListBucketMultipartUploads",
            "s3:ListMultipartUploadParts"
          ]
          Resource = concat(
            [for p in var.s3_prefixes : "${aws_s3_bucket.uploads.arn}/${trim(p, "/")}/*"],
            length(var.s3_prefixes) == 0 ? ["${aws_s3_bucket.uploads.arn}/*"] : []
          )
        }
      ]
    )
  })
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "bucket_name_prefix" {
  description = "Prefix for the uploads bucket name"
  type        = string
  default     = "user-uploads"
}

variable "enable_versioning" {
  description = "Enable S3 versioning"
  type        = bool
  default     = true
}

variable "cors_allowed_origins" {
  description = "Allowed origins for browser-based uploads/downloads"
  type        = list(string)
  default     = ["http://localhost:3000"]
}

variable "cors_allowed_methods" {
  description = "Allowed HTTP methods for CORS"
  type        = list(string)
  default     = ["GET", "PUT", "POST", "DELETE", "HEAD"]
}

variable "cors_allowed_headers" {
  description = "Allowed headers for CORS"
  type        = list(string)
  default     = ["*"]
}

variable "cors_expose_headers" {
  description = "Exposed headers for CORS"
  type        = list(string)
  default     = ["ETag"]
}

variable "cors_max_age_seconds" {
  description = "CORS preflight cache duration"
  type        = number
  default     = 3000
}

variable "app_iam_user_name" {
  description = "Base name for the IAM user used by the web application"
  type        = string
  default     = "webapp-uploads"
}

variable "s3_prefixes" {
  description = "Optional list of key prefixes the app is allowed to access (e.g., [\"uploads\"]). Empty means full bucket access."
  type        = list(string)
  default     = ["uploads"]
}

variable "tags" {
  description = "Additional tags"
  type        = map(string)
  default     = {}
}

output "uploads_bucket_name" {
  value = aws_s3_bucket.uploads.bucket
}

output "uploads_bucket_arn" {
  value = aws_s3_bucket.uploads.arn
}

output "uploads_app_access_key_id" {
  value = aws_iam_access_key.uploads_app.id
}

output "uploads_app_secret_access_key" {
  value     = aws_iam_access_key.uploads_app.secret
  sensitive = true
}
