resource "aws_s3_bucket" "app_data" {
  bucket = "myapp-logs-and-data-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_public_access_block" "app_data" {
  bucket = aws_s3_bucket.app_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "app_data" {
  bucket = aws_s3_bucket.app_data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_iam_role" "ec2_log_writer" {
  name = "ec2-log-writer-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "ec2_s3_write" {
  name        = "ec2-s3-write-policy"
  description = "Allow EC2 instances to write logs to S3"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl"
        ]
        Resource = "${aws_s3_bucket.app_data.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.app_data.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ec2_s3_write" {
  role       = aws_iam_role.ec2_log_writer.name
  policy_arn = aws_iam_policy.ec2_s3_write.arn
}

resource "aws_iam_instance_profile" "ec2_log_writer" {
  name = "ec2-log-writer-profile"
  role = aws_iam_role.ec2_log_writer.name
}

data "aws_caller_identity" "current" {}

output "bucket_name" {
  value = aws_s3_bucket.app_data.id
}

output "bucket_arn" {
  value = aws_s3_bucket.app_data.arn
}

output "instance_profile_name" {
  value = aws_iam_instance_profile.ec2_log_writer.name
}