terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
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

variable "name_prefix" {
  type    = string
  default = "payment-processor"
}

variable "dynamodb_table_name" {
  type    = string
  default = "payment-transactions"
}

variable "log_retention_days" {
  type    = number
  default = 90
}

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

resource "aws_kms_key" "payment" {
  description             = "${var.name_prefix} encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EnableAccountAdministrators"
        Effect = "Allow"
        Principal = {
          AWS = "arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "AllowLambdaEnvVarEncryption"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:CallerAccount" = data.aws_caller_identity.current.account_id
          }
          ArnLike = {
            "kms:EncryptionContext:aws:lambda:FunctionArn" = "arn:${data.aws_partition.current.partition}:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${var.name_prefix}-*"
          }
        }
      },
      {
        Sid    = "AllowSecretsManager"
        Effect = "Allow"
        Principal = {
          Service = "secretsmanager.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:CallerAccount" = data.aws_caller_identity.current.account_id
          }
        }
      },
      {
        Sid    = "AllowDynamoDB"
        Effect = "Allow"
        Principal = {
          Service = "dynamodb.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:CallerAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
}

resource "aws_kms_alias" "payment" {
  name          = "alias/${var.name_prefix}"
  target_key_id = aws_kms_key.payment.key_id
}

resource "aws_dynamodb_table" "transactions" {
  name         = var.dynamodb_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "payment_id"

  attribute {
    name = "payment_id"
    type = "S"
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.payment.arn
  }

  point_in_time_recovery {
    enabled = true
  }
}

resource "aws_secretsmanager_secret" "processor_credentials" {
  name                    = "${var.name_prefix}/processor-credentials"
  kms_key_id              = aws_kms_key.payment.id
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "processor_credentials" {
  secret_id     = aws_secretsmanager_secret.processor_credentials.id
  secret_string = jsonencode({ client_id = "placeholder-rotate-me", scope = "payments.process" })
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.name_prefix}-handler"
  retention_in_days = var.log_retention_days
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  output_path = "${path.module}/build/lambda.zip"

  source {
    content  = file("${path.module}/lambda/handler.py")
    filename = "handler.py"
  }
}

resource "aws_iam_role" "lambda_exec" {
  name = "${var.name_prefix}-lambda-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "lambda_least_privilege" {
  name = "${var.name_prefix}-lambda-policy"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.lambda.arn}:*"
      },
      {
        Sid    = "KmsForAppData"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.payment.arn
        Condition = {
          StringEquals = {
            "kms:ViaService" = [
              "secretsmanager.${var.aws_region}.amazonaws.com",
              "dynamodb.${var.aws_region}.amazonaws.com"
            ]
          }
        }
      },
      {
        Sid    = "KmsForLambdaEnvironment"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.payment.arn
        Condition = {
          StringEquals = {
            "kms:CallerAccount" = data.aws_caller_identity.current.account_id
          }
          ArnLike = {
            "kms:EncryptionContext:aws:lambda:FunctionArn" = "arn:${data.aws_partition.current.partition}:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${var.name_prefix}-handler"
          }
        }
      },
      {
        Sid    = "SecretsRead"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.processor_credentials.arn
      },
      {
        Sid    = "DynamoPaymentTable"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:ConditionCheckItem"
        ]
        Resource = aws_dynamodb_table.transactions.arn
      }
    ]
  })
}

resource "aws_lambda_function" "payment_handler" {
  function_name    = "${var.name_prefix}-handler"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 30
  memory_size      = 256
  kms_key_arn      = aws_kms_key.payment.arn

  environment {
    variables = {
      TABLE_NAME           = aws_dynamodb_table.transactions.name
      SECRET_ARN           = aws_secretsmanager_secret.processor_credentials.arn
      LOG_LEVEL            = "INFO"
      AWS_XRAY_TRACING_OFF = "1"
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda_least_privilege,
    aws_cloudwatch_log_group.lambda
  ]
}

resource "aws_lambda_permission" "allow_invoke" {
  statement_id  = "AllowInvokerAccount"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.payment_handler.function_name
  principal     = "arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:root"
}

output "lambda_function_name" {
  value = aws_lambda_function.payment_handler.function_name
}

output "lambda_function_arn" {
  value = aws_lambda_function.payment_handler.arn
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.transactions.name
}

output "secrets_arn" {
  value     = aws_secretsmanager_secret.processor_credentials.arn
  sensitive = true
}
