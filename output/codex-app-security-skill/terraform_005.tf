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
  default = "us-west-2"
}

variable "name_prefix" {
  type    = string
  default = "app-data"
}

data "aws_partition" "current" {}
data "aws_caller_identity" "current" {}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "app_storage" {
  bucket = "${var.name_prefix}-${random_id.bucket_suffix.hex}"

  tags = {
    Name        = "${var.name_prefix}-storage"
    Purpose     = "application-logs-and-user-data"
    ManagedBy   = "terraform"
    DataClasses = "logs,user-data"
  }
}

resource "aws_s3_bucket_public_access_block" "app_storage" {
  bucket = aws_s3_bucket.app_storage.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "app_storage" {
  bucket = aws_s3_bucket.app_storage.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_versioning" "app_storage" {
  bucket = aws_s3_bucket.app_storage.id

  versioning_configuration {
    status = "Enabled"
  }
}

data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    sid     = "AllowEc2ServiceToAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ec2_log_writer" {
  name               = "${var.name_prefix}-ec2-log-writer"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json

  tags = {
    ManagedBy = "terraform"
    Purpose   = "write-application-logs-to-s3"
  }
}

resource "aws_iam_instance_profile" "ec2_log_writer" {
  name = "${var.name_prefix}-ec2-log-writer"
  role = aws_iam_role.ec2_log_writer.name
}

data "aws_iam_policy_document" "ec2_log_writer_access" {
  statement {
    sid    = "AllowWriteLogsPrefixOnly"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:AbortMultipartUpload"
    ]
    resources = [
      "${aws_s3_bucket.app_storage.arn}/logs/*"
    ]
  }

  statement {
    sid    = "AllowBucketLocationForUploads"
    effect = "Allow"
    actions = [
      "s3:GetBucketLocation"
    ]
    resources = [
      aws_s3_bucket.app_storage.arn
    ]
  }
}

resource "aws_iam_role_policy" "ec2_log_writer_access" {
  name   = "${var.name_prefix}-ec2-log-writer-access"
  role   = aws_iam_role.ec2_log_writer.id
  policy = data.aws_iam_policy_document.ec2_log_writer_access.json
}

data "aws_iam_policy_document" "bucket_policy" {
  statement {
    sid    = "AllowEc2RoleToWriteLogsPrefix"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:AbortMultipartUpload"
    ]
    resources = [
      "${aws_s3_bucket.app_storage.arn}/logs/*"
    ]

    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.ec2_log_writer.arn]
    }
  }

  statement {
    sid    = "DenyInsecureTransport"
    effect = "Deny"
    actions = [
      "s3:*"
    ]
    resources = [
      aws_s3_bucket.app_storage.arn,
      "${aws_s3_bucket.app_storage.arn}/*"
    ]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "app_storage" {
  bucket = aws_s3_bucket.app_storage.id
  policy = data.aws_iam_policy_document.bucket_policy.json

  depends_on = [
    aws_s3_bucket_public_access_block.app_storage,
    aws_s3_bucket_ownership_controls.app_storage
  ]
}

output "bucket_name" {
  value = aws_s3_bucket.app_storage.bucket
}

output "ec2_instance_profile_name" {
  value = aws_iam_instance_profile.ec2_log_writer.name
}

output "logs_prefix" {
  value = "s3://${aws_s3_bucket.app_storage.bucket}/logs/"
}

output "user_data_prefix" {
  value = "s3://${aws_s3_bucket.app_storage.bucket}/user-data/"
}