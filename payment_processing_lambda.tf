terraform {
  required_version = ">= 1.0"
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
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "kms_key_id" {
  description = "KMS key ID for encryption"
  type        = string
}

variable "vpc_subnet_ids" {
  description = "VPC subnet IDs for Lambda"
  type        = list(string)
}

variable "vpc_security_group_ids" {
  description = "Security group IDs for Lambda"
  type        = list(string)
}

data "aws_caller_identity" "current" {}

resource "aws_kms_key" "payment_encryption" {
  description             = "KMS key for payment data encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow Lambda Functions"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Environment = var.environment
    Purpose     = "payment-processing"
    Compliance  = "PCI-DSS"
  }
}

resource "aws_kms_alias" "payment_encryption" {
  name          = "alias/payment-processing-${var.environment}"
  target_key_id = aws_kms_key.payment_encryption.key_id
}

resource "aws_s3_bucket" "payment_data" {
  bucket = "payment-processing-data-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Environment = var.environment
    Purpose     = "payment-processing"
    Compliance  = "PCI-DSS"
  }
}

resource "aws_s3_bucket_encryption" "payment_data" {
  bucket = aws_s3_bucket.payment_data.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.payment_encryption.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_versioning" "payment_data" {
  bucket = aws_s3_bucket.payment_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "payment_data" {
  bucket = aws_s3_bucket.payment_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_logging" "payment_data" {
  bucket = aws_s3_bucket.payment_data.id

  target_bucket = aws_s3_bucket.payment_logs.id
  target_prefix = "s3-access-logs/"
}

resource "aws_s3_bucket" "payment_logs" {
  bucket = "payment-processing-logs-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Environment = var.environment
    Purpose     = "audit-logs"
    Compliance  = "PCI-DSS"
  }
}

resource "aws_s3_bucket_encryption" "payment_logs" {
  bucket = aws_s3_bucket.payment_logs.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.payment_encryption.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "payment_logs" {
  bucket = aws_s3_bucket.payment_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "payment_transactions" {
  name           = "payment-transactions-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "transaction_id"
  range_key      = "timestamp"

  attribute {
    name = "transaction_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  attribute {
    name = "customer_id"
    type = "S"
  }

  global_secondary_index {
    name            = "customer_index"
    hash_key        = "customer_id"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.payment_encryption.arn
  }

  tags = {
    Environment = var.environment
    Purpose     = "payment-processing"
    Compliance  = "PCI-DSS"
  }
}

resource "aws_iam_role" "payment_processor_lambda" {
  name = "payment-processor-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Purpose     = "payment-processing"
  }
}

resource "aws_iam_policy" "payment_processor_policy" {
  name        = "payment-processor-policy-${var.environment}"
  description = "IAM policy for payment processing Lambda functions"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.payment_encryption.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.payment_data.arn}/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-server-side-encryption" = "aws:kms"
            "s3:x-amz-server-side-encryption-aws-kms-key-id" = aws_kms_key.payment_encryption.arn
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.payment_data.arn
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.payment_transactions.arn,
          "${aws_dynamodb_table.payment_transactions.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.payment_api_keys.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "payment_processor_policy" {
  role       = aws_iam_role.payment_processor_lambda.name
  policy_arn = aws_iam_policy.payment_processor_policy.arn
}

resource "aws_iam_role_policy_attachment" "payment_processor_vpc_execution" {
  role       = aws_iam_role.payment_processor_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_secretsmanager_secret" "payment_api_keys" {
  name                    = "payment-processing-api-keys-${var.environment}"
  recovery_window_in_days = 30
  kms_key_id              = aws_kms_key.payment_encryption.id

  tags = {
    Environment = var.environment
    Purpose     = "payment-processing"
    Compliance  = "PCI-DSS"
  }
}

resource "aws_secretsmanager_secret_version" "payment_api_keys" {
  secret_id = aws_secretsmanager_secret.payment_api_keys.id
  secret_string = jsonencode({
    stripe_secret_key     = "sk_live_placeholder"
    stripe_webhook_secret = "whsec_placeholder"
    encryption_key        = "placeholder_key"
  })
}

resource "aws_lambda_function" "process_payment" {
  filename         = "lambda_functions/process_payment.zip"
  function_name    = "process-payment-${var.environment}"
  role            = aws_iam_role.payment_processor_lambda.arn
  handler         = "index.handler"
  source_code_hash = filebase64sha256("lambda_functions/process_payment.zip")
  runtime         = "python3.11"
  timeout         = 30
  memory_size     = 1024

  environment {
    variables = {
      ENVIRONMENT        = var.environment
      KMS_KEY_ID         = aws_kms_key.payment_encryption.id
      TRANSACTION_TABLE  = aws_dynamodb_table.payment_transactions.name
      PAYMENT_BUCKET     = aws_s3_bucket.payment_data.id
      SECRET_NAME        = aws_secretsmanager_secret.payment_api_keys.name
    }
  }

  vpc_config {
    subnet_ids         = var.vpc_subnet_ids
    security_group_ids = var.vpc_security_group_ids
  }

  dead_letter_config {
    target_arn = aws_sqs_queue.payment_dlq.arn
  }

  reserved_concurrent_executions = 100

  tracing_config {
    mode = "Active"
  }

  tags = {
    Environment = var.environment
    Purpose     = "payment-processing"
    Compliance  = "PCI-DSS"
  }
}

resource "aws_lambda_function" "validate_payment" {
  filename         = "lambda_functions/validate_payment.zip"
  function_name    = "validate-payment-${var.environment}"
  role            = aws_iam_role.payment_processor_lambda.arn
  handler         = "index.handler"
  source_code_hash = filebase64sha256("lambda_functions/validate_payment.zip")
  runtime         = "python3.11"
  timeout         = 15
  memory_size     = 512

  environment {
    variables = {
      ENVIRONMENT        = var.environment
      KMS_KEY_ID         = aws_kms_key.payment_encryption.id
      TRANSACTION_TABLE  = aws_dynamodb_table.payment_transactions.name
      SECRET_NAME        = aws_secretsmanager_secret.payment_api_keys.name
    }
  }

  vpc_config {
    subnet_ids         = var.vpc_subnet_ids
    security_group_ids = var.vpc_security_group_ids
  }

  reserved_concurrent_executions = 50

  tracing_config {
    mode = "Active"
  }

  tags = {
    Environment = var.environment
    Purpose     = "payment-validation"
    Compliance  = "PCI-DSS"
  }
}

resource "aws_lambda_function" "refund_payment" {
  filename         = "lambda_functions/refund_payment.zip"
  function_name    = "refund-payment-${var.environment}"
  role            = aws_iam_role.payment_processor_lambda.arn
  handler         = "index.handler"
  source_code_hash = filebase64sha256("lambda_functions/refund_payment.zip")
  runtime         = "python3.11"
  timeout         = 30
  memory_size     = 512

  environment {
    variables = {
      ENVIRONMENT        = var.environment
      KMS_KEY_ID         = aws_kms_key.payment_encryption.id
      TRANSACTION_TABLE  = aws_dynamodb_table.payment_transactions.name
      PAYMENT_BUCKET     = aws_s3_bucket.payment_data.id
      SECRET_NAME        = aws_secretsmanager_secret.payment_api_keys.name
    }
  }

  vpc_config {
    subnet_ids         = var.vpc_subnet_ids
    security_group_ids = var.vpc_security_group_ids
  }

  dead_letter_config {
    target_arn = aws_sqs_queue.payment_dlq.arn
  }

  reserved_concurrent_executions = 25

  tracing_config {
    mode = "Active"
  }

  tags = {
    Environment = var.environment
    Purpose     = "payment-refunds"
    Compliance  = "PCI-DSS"
  }
}

resource "aws_lambda_function" "audit_transactions" {
  filename         = "lambda_functions/audit_transactions.zip"
  function_name    = "audit-transactions-${var.environment}"
  role            = aws_iam_role.payment_processor_lambda.arn
  handler         = "index.handler"
  source_code_hash = filebase64sha256("lambda_functions/audit_transactions.zip")
  runtime         = "python3.11"
  timeout         = 60
  memory_size     = 1024

  environment {
    variables = {
      ENVIRONMENT        = var.environment
      KMS_KEY_ID         = aws_kms_key.payment_encryption.id
      TRANSACTION_TABLE  = aws_dynamodb_table.payment_transactions.name
      PAYMENT_BUCKET     = aws_s3_bucket.payment_data.id
      LOG_BUCKET         = aws_s3_bucket.payment_logs.id
    }
  }

  vpc_config {
    subnet_ids         = var.vpc_subnet_ids
    security_group_ids = var.vpc_security_group_ids
  }

  reserved_concurrent_executions = 10

  tracing_config {
    mode = "Active"
  }

  tags = {
    Environment = var.environment
    Purpose     = "transaction-auditing"
    Compliance  = "PCI-DSS"
  }
}

resource "aws_sqs_queue" "payment_dlq" {
  name                      = "payment-processing-dlq-${var.environment}"
  message_retention_seconds = 1209600
  kms_master_key_id        = aws_kms_key.payment_encryption.id

  tags = {
    Environment = var.environment
    Purpose     = "dead-letter-queue"
  }
}

resource "aws_sqs_queue" "payment_processing" {
  name                      = "payment-processing-queue-${var.environment}"
  visibility_timeout_seconds = 180
  message_retention_seconds = 345600
  kms_master_key_id        = aws_kms_key.payment_encryption.id

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.payment_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Environment = var.environment
    Purpose     = "payment-processing"
  }
}

resource "aws_lambda_event_source_mapping" "payment_queue_processor" {
  event_source_arn = aws_sqs_queue.payment_processing.arn
  function_name    = aws_lambda_function.process_payment.arn
  batch_size       = 10

  scaling_config {
    maximum_concurrency = 10
  }
}

resource "aws_iam_policy" "sqs_lambda_policy" {
  name        = "payment-sqs-lambda-policy-${var.environment}"
  description = "Policy for Lambda to access SQS queues"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.payment_processing.arn
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage"
        ]
        Resource = aws_sqs_queue.payment_dlq.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "sqs_lambda_policy" {
  role       = aws_iam_role.payment_processor_lambda.name
  policy_arn = aws_iam_policy.sqs_lambda_policy.arn
}

resource "aws_api_gateway_rest_api" "payment_api" {
  name        = "payment-processing-api-${var.environment}"
  description = "Payment Processing API"

  endpoint_configuration {
    types = ["PRIVATE"]
    vpc_endpoint_ids = var.vpc_endpoint_ids
  }

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = "*"
        Action = "execute-api:Invoke"
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:SourceVpce" = var.vpc_endpoint_ids
          }
        }
      }
    ]
  })
}

resource "aws_api_gateway_resource" "payment" {
  rest_api_id = aws_api_gateway_rest_api.payment_api.id
  parent_id   = aws_api_gateway_rest_api.payment_api.root_resource_id
  path_part   = "payment"
}

resource "aws_api_gateway_method" "process_payment" {
  rest_api_id   = aws_api_gateway_rest_api.payment_api.id
  resource_id   = aws_api_gateway_resource.payment.id
  http_method   = "POST"
  authorization = "AWS_IAM"
}

resource "aws_api_gateway_integration" "process_payment" {
  rest_api_id = aws_api_gateway_rest_api.payment_api.id
  resource_id = aws_api_gateway_resource.payment.id
  http_method = aws_api_gateway_method.process_payment.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.process_payment.invoke_arn
}

resource "aws_lambda_permission" "api_gateway_process" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.process_payment.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.payment_api.execution_arn}/*/*"
}

resource "aws_api_gateway_deployment" "payment_api" {
  rest_api_id = aws_api_gateway_rest_api.payment_api.id
  stage_name  = var.environment

  depends_on = [
    aws_api_gateway_integration.process_payment
  ]
}

variable "vpc_endpoint_ids" {
  description = "VPC endpoint IDs for private API Gateway"
  type        = list(string)
}

output "payment_api_endpoint" {
  value = aws_api_gateway_deployment.payment_api.invoke_url
}

output "kms_key_arn" {
  value = aws_kms_key.payment_encryption.arn
}

output "payment_processor_function_arn" {
  value = aws_lambda_function.process_payment.arn
}

output "transaction_table_name" {
  value = aws_dynamodb_table.payment_transactions.name
}