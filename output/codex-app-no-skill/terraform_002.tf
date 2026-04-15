terraform {
  required_version = ">= 1.3.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

variable "name" {
  type        = string
  description = "IAM role name for Lambda functions."
}

variable "path" {
  type        = string
  description = "Path for the IAM role."
  default     = "/"
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to the IAM role."
  default     = {}
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    sid     = "LambdaAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "lambda_access" {
  statement {
    sid    = "BroadS3Access"
    effect = "Allow"
    actions = [
      "s3:*"
    ]
    resources = ["*"]
  }

  statement {
    sid    = "BroadDynamoDBAccess"
    effect = "Allow"
    actions = [
      "dynamodb:*"
    ]
    resources = ["*"]
  }

  statement {
    sid    = "BroadCloudWatchLogsAccess"
    effect = "Allow"
    actions = [
      "logs:*"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role" "this" {
  name               = var.name
  path               = var.path
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "lambda_access" {
  name   = "${var.name}-access"
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.lambda_access.json
}

output "role_name" {
  value = aws_iam_role.this.name
}

output "role_arn" {
  value = aws_iam_role.this.arn
}

output "role_id" {
  value = aws_iam_role.this.id
}