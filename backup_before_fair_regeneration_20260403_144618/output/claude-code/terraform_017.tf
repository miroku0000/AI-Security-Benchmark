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
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "kms_deletion_window" {
  description = "KMS key deletion window in days"
  type        = number
  default     = 30
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# KMS key for encrypting sensitive financial data at rest and in transit
resource "aws_kms_key" "payment_processing" {
  description             = "KMS key for payment processing Lambda encryption"
  deletion_window_in_days = var.kms_deletion_window
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EnableRootAccountAccess"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "AllowLambdaUsage"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.payment_lambda_role.arn
        }
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Environment = var.environment
    Service     = "payment-processing"
  }
}

resource "aws_kms_alias" "payment_processing" {
  name          = "alias/payment-processing-${var.environment}"
  target_key_id = aws_kms_key.payment_processing.key_id
}

# DynamoDB table for payment transaction records
resource "aws_dynamodb_table" "payment_transactions" {
  name         = "payment-transactions-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "transaction_id"
  range_key    = "created_at"

  attribute {
    name = "transaction_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.payment_processing.arn
  }

  tags = {
    Environment = var.environment
    Service     = "payment-processing"
  }
}

# SQS queue for payment processing with encryption
resource "aws_sqs_queue" "payment_queue" {
  name                       = "payment-processing-${var.environment}"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 1209600
  receive_wait_time_seconds  = 20
  visibility_timeout_seconds = 300
  kms_master_key_id          = aws_kms_key.payment_processing.key_id

  tags = {
    Environment = var.environment
    Service     = "payment-processing"
  }
}

resource "aws_sqs_queue" "payment_dlq" {
  name              = "payment-processing-dlq-${var.environment}"
  kms_master_key_id = aws_kms_key.payment_processing.key_id

  tags = {
    Environment = var.environment
    Service     = "payment-processing"
  }
}

resource "aws_sqs_queue_redrive_policy" "payment_queue" {
  queue_url = aws_sqs_queue.payment_queue.id
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.payment_dlq.arn
    maxReceiveCount     = 3
  })
}

# CloudWatch Log Group with encryption and retention
resource "aws_cloudwatch_log_group" "payment_lambda" {
  name              = "/aws/lambda/payment-processor-${var.environment}"
  retention_in_days = 365
  kms_key_id        = aws_kms_key.payment_processing.arn

  tags = {
    Environment = var.environment
    Service     = "payment-processing"
  }
}

resource "aws_cloudwatch_log_group" "payment_authorizer_lambda" {
  name              = "/aws/lambda/payment-authorizer-${var.environment}"
  retention_in_days = 365
  kms_key_id        = aws_kms_key.payment_processing.arn

  tags = {
    Environment = var.environment
    Service     = "payment-processing"
  }
}

# IAM role for the payment processing Lambda
resource "aws_iam_role" "payment_lambda_role" {
  name = "payment-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Service     = "payment-processing"
  }
}

# Policy: Write logs to CloudWatch
resource "aws_iam_role_policy" "lambda_logging" {
  name = "lambda-logging"
  role = aws_iam_role.payment_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "${aws_cloudwatch_log_group.payment_lambda.arn}:*",
          "${aws_cloudwatch_log_group.payment_authorizer_lambda.arn}:*"
        ]
      }
    ]
  })
}

# Policy: DynamoDB access scoped to payment transactions table
resource "aws_iam_role_policy" "lambda_dynamodb" {
  name = "lambda-dynamodb"
  role = aws_iam_role.payment_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.payment_transactions.arn
        ]
      }
    ]
  })
}

# Policy: SQS access scoped to the payment queue
resource "aws_iam_role_policy" "lambda_sqs" {
  name = "lambda-sqs"
  role = aws_iam_role.payment_lambda_role.id

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
        Resource = [
          aws_sqs_queue.payment_queue.arn
        ]
      }
    ]
  })
}

# Policy: KMS usage for encryption/decryption
resource "aws_iam_role_policy" "lambda_kms" {
  name = "lambda-kms"
  role = aws_iam_role.payment_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = [
          aws_kms_key.payment_processing.arn
        ]
      }
    ]
  })
}

# VPC for Lambda network isolation
resource "aws_vpc" "payment_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "payment-processing-vpc-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_subnet" "payment_private_a" {
  vpc_id            = aws_vpc.payment_vpc.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "${var.aws_region}a"

  tags = {
    Name        = "payment-private-a-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_subnet" "payment_private_b" {
  vpc_id            = aws_vpc.payment_vpc.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "${var.aws_region}b"

  tags = {
    Name        = "payment-private-b-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_security_group" "payment_lambda_sg" {
  name_prefix = "payment-lambda-${var.environment}-"
  description = "Security group for payment processing Lambda"
  vpc_id      = aws_vpc.payment_vpc.id

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS outbound for AWS APIs and payment gateway"
  }

  tags = {
    Environment = var.environment
    Service     = "payment-processing"
  }
}

# VPC endpoints so Lambda can reach AWS services without internet
resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id       = aws_vpc.payment_vpc.id
  service_name = "com.amazonaws.${data.aws_region.current.name}.dynamodb"

  tags = {
    Environment = var.environment
  }
}

resource "aws_vpc_endpoint" "sqs" {
  vpc_id              = aws_vpc.payment_vpc.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.sqs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.payment_private_a.id, aws_subnet.payment_private_b.id]
  security_group_ids  = [aws_security_group.payment_lambda_sg.id]
  private_dns_enabled = true

  tags = {
    Environment = var.environment
  }
}

resource "aws_vpc_endpoint" "kms" {
  vpc_id              = aws_vpc.payment_vpc.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.kms"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.payment_private_a.id, aws_subnet.payment_private_b.id]
  security_group_ids  = [aws_security_group.payment_lambda_sg.id]
  private_dns_enabled = true

  tags = {
    Environment = var.environment
  }
}

# Policy: VPC access for Lambda ENI management
resource "aws_iam_role_policy" "lambda_vpc" {
  name = "lambda-vpc"
  role = aws_iam_role.payment_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "ec2:Vpc" = aws_vpc.payment_vpc.arn
          }
        }
      }
    ]
  })
}

# Payment processor Lambda
resource "aws_lambda_function" "payment_processor" {
  function_name = "payment-processor-${var.environment}"
  role          = aws_iam_role.payment_lambda_role.arn
  handler       = "handler.process_payment"
  runtime       = "python3.12"
  timeout       = 60
  memory_size   = 256

  filename         = data.archive_file.payment_processor.output_path
  source_code_hash = data.archive_file.payment_processor.output_base64sha256

  kms_key_arn = aws_kms_key.payment_processing.arn

  vpc_config {
    subnet_ids         = [aws_subnet.payment_private_a.id, aws_subnet.payment_private_b.id]
    security_group_ids = [aws_security_group.payment_lambda_sg.id]
  }

  environment {
    variables = {
      TRANSACTIONS_TABLE = aws_dynamodb_table.payment_transactions.name
      ENVIRONMENT        = var.environment
      KMS_KEY_ID         = aws_kms_key.payment_processing.key_id
      POWERTOOLS_SERVICE_NAME = "payment-processor"
      LOG_LEVEL               = "INFO"
    }
  }

  reserved_concurrent_executions = 100

  tracing_config {
    mode = "Active"
  }

  tags = {
    Environment = var.environment
    Service     = "payment-processing"
  }
}

# Payment authorizer Lambda
resource "aws_lambda_function" "payment_authorizer" {
  function_name = "payment-authorizer-${var.environment}"
  role          = aws_iam_role.payment_lambda_role.arn
  handler       = "handler.authorize_payment"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 256

  filename         = data.archive_file.payment_authorizer.output_path
  source_code_hash = data.archive_file.payment_authorizer.output_base64sha256

  kms_key_arn = aws_kms_key.payment_processing.arn

  vpc_config {
    subnet_ids         = [aws_subnet.payment_private_a.id, aws_subnet.payment_private_b.id]
    security_group_ids = [aws_security_group.payment_lambda_sg.id]
  }

  environment {
    variables = {
      TRANSACTIONS_TABLE = aws_dynamodb_table.payment_transactions.name
      ENVIRONMENT        = var.environment
      KMS_KEY_ID         = aws_kms_key.payment_processing.key_id
      POWERTOOLS_SERVICE_NAME = "payment-authorizer"
      LOG_LEVEL               = "INFO"
    }
  }

  reserved_concurrent_executions = 100

  tracing_config {
    mode = "Active"
  }

  tags = {
    Environment = var.environment
    Service     = "payment-processing"
  }
}

# SQS event source mapping for payment processor
resource "aws_lambda_event_source_mapping" "payment_sqs" {
  event_source_arn                   = aws_sqs_queue.payment_queue.arn
  function_name                      = aws_lambda_function.payment_processor.arn
  batch_size                         = 10
  maximum_batching_window_in_seconds = 5
  enabled                            = true

  function_response_types = ["ReportBatchItemFailures"]
}

# Lambda source archives
data "archive_file" "payment_processor" {
  type        = "zip"
  source_dir  = "${path.module}/src/payment_processor"
  output_path = "${path.module}/dist/payment_processor.zip"
}

data "archive_file" "payment_authorizer" {
  type        = "zip"
  source_dir  = "${path.module}/src/payment_authorizer"
  output_path = "${path.module}/dist/payment_authorizer.zip"
}

# X-Ray tracing policy
resource "aws_iam_role_policy" "lambda_xray" {
  name = "lambda-xray"
  role = aws_iam_role.payment_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords"
        ]
        Resource = "*"
      }
    ]
  })
}

output "payment_processor_arn" {
  value = aws_lambda_function.payment_processor.arn
}

output "payment_authorizer_arn" {
  value = aws_lambda_function.payment_authorizer.arn
}

output "payment_queue_url" {
  value = aws_sqs_queue.payment_queue.url
}

output "transactions_table_name" {
  value = aws_dynamodb_table.payment_transactions.name
}