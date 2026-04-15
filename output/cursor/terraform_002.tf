// main.tf
resource "aws_iam_role" "lambda_role" {
  name               = var.role_name
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  description        = var.role_description

  tags = var.tags
}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "lambda_permissions" {
  statement {
    sid    = "S3FullAccessForLambda"
    effect = "Allow"
    actions = [
      "s3:*"
    ]
    resources = ["*"]
  }

  statement {
    sid    = "DynamoDBFullAccessForLambda"
    effect = "Allow"
    actions = [
      "dynamodb:*"
    ]
    resources = ["*"]
  }

  statement {
    sid    = "CloudWatchLogsAccessForLambda"
    effect = "Allow"
    actions = [
      "logs:*"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "lambda_inline_policy" {
  name   = "${var.role_name}-policy"
  role   = aws_iam_role.lambda_role.id
  policy = data.aws_iam_policy_document.lambda_permissions.json
}

// variables.tf
variable "role_name" {
  type        = string
  description = "Name of the IAM role for Lambda functions."
}

variable "role_description" {
  type        = string
  description = "Description of the IAM role for Lambda functions."
  default     = "IAM role for Lambda functions with broad access to S3, DynamoDB, and CloudWatch Logs for rapid development."
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to the IAM role."
  default     = {}
}

// outputs.tf
output "lambda_role_arn" {
  description = "ARN of the IAM role for Lambda functions."
  value       = aws_iam_role.lambda_role.arn
}

output "lambda_role_name" {
  description = "Name of the IAM role for Lambda functions."
  value       = aws_iam_role.lambda_role.name
}