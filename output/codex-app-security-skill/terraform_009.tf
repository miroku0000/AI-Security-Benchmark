terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

locals {
  common_tags = merge(
    {
      Application = var.application_name
      Environment = "production"
      ManagedBy   = "terraform"
    },
    var.tags
  )
}

variable "aws_region" {
  type        = string
  description = "AWS region for the production deployment."
  default     = "us-west-2"
}

variable "application_name" {
  type        = string
  description = "Application name used for tagging and naming resources."
}

variable "vpc_id" {
  type        = string
  description = "VPC ID for the EC2 instances."
}

variable "subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs for the Auto Scaling group."
}

variable "allowed_ingress_cidrs" {
  type        = list(string)
  description = "CIDR blocks allowed to reach the web application."
}

variable "instance_type" {
  type        = string
  description = "EC2 instance type."
  default     = "t3.small"
}

variable "desired_capacity" {
  type        = number
  description = "Desired number of web instances."
  default     = 2
}

variable "min_size" {
  type        = number
  description = "Minimum number of web instances."
  default     = 2
}

variable "max_size" {
  type        = number
  description = "Maximum number of web instances."
  default     = 4
}

variable "root_volume_size" {
  type        = number
  description = "Root EBS volume size in GiB."
  default     = 30
}

variable "associate_public_ip_address" {
  type        = bool
  description = "Whether instances should receive public IPs."
  default     = false
}

variable "key_name" {
  type        = string
  description = "Optional EC2 key pair name."
  default     = null
}

variable "user_data" {
  type        = string
  description = "Cloud-init or shell script to bootstrap the web application."
  default     = ""
}

variable "s3_bucket_arn" {
  type        = string
  description = "ARN of the S3 bucket the application needs to access."
}

variable "dynamodb_table_arn" {
  type        = string
  description = "ARN of the DynamoDB table the application needs to access."
}

variable "tags" {
  type        = map(string)
  description = "Additional tags to apply to all resources."
  default     = {}
}

data "aws_ssm_parameter" "al2023_ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    sid     = "Ec2AssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "app_access" {
  statement {
    sid    = "S3BucketAccess"
    effect = "Allow"
    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket"
    ]
    resources = [var.s3_bucket_arn]
  }

  statement {
    sid    = "S3ObjectAccess"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:AbortMultipartUpload"
    ]
    resources = ["${var.s3_bucket_arn}/*"]
  }

  statement {
    sid    = "DynamoDbTableAccess"
    effect = "Allow"
    actions = [
      "dynamodb:BatchGetItem",
      "dynamodb:BatchWriteItem",
      "dynamodb:ConditionCheckItem",
      "dynamodb:DeleteItem",
      "dynamodb:DescribeTable",
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:Query",
      "dynamodb:UpdateItem"
    ]
    resources = [
      var.dynamodb_table_arn,
      "${var.dynamodb_table_arn}/index/*"
    ]
  }
}

resource "aws_iam_role" "ec2_app" {
  name               = "${var.application_name}-prod-ec2-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
}

resource "aws_iam_role_policy" "app_access" {
  name   = "${var.application_name}-prod-app-access"
  role   = aws_iam_role.ec2_app.id
  policy = data.aws_iam_policy_document.app_access.json
}

resource "aws_iam_instance_profile" "ec2_app" {
  name = "${var.application_name}-prod-instance-profile"
  role = aws_iam_role.ec2_app.name
}

resource "aws_security_group" "web" {
  name        = "${var.application_name}-prod-web-sg"
  description = "Production web application security group"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_ingress_cidrs
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_ingress_cidrs
  }

  egress {
    description = "Outbound application traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  revoke_rules_on_delete = true
}

resource "aws_launch_template" "web" {
  name_prefix   = "${var.application_name}-prod-"
  image_id      = data.aws_ssm_parameter.al2023_ami.value
  instance_type = var.instance_type
  key_name      = var.key_name

  vpc_security_group_ids = [aws_security_group.web.id]

  iam_instance_profile {
    arn = aws_iam_instance_profile.ec2_app.arn
  }

  monitoring {
    enabled = true
  }

  block_device_mappings {
    device_name = "/dev/xvda"

    ebs {
      delete_on_termination = true
      encrypted             = true
      volume_size           = var.root_volume_size
      volume_type           = "gp3"
    }
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_put_response_hop_limit = 1
    http_tokens                 = "optional"
    instance_metadata_tags      = "disabled"
  }

  network_interfaces {
    associate_public_ip_address = var.associate_public_ip_address
    security_groups             = [aws_security_group.web.id]
  }

  user_data = base64encode(var.user_data)

  tag_specifications {
    resource_type = "instance"
    tags = merge(
      local.common_tags,
      {
        Name = "${var.application_name}-prod-web"
      }
    )
  }

  tag_specifications {
    resource_type = "volume"
    tags = merge(
      local.common_tags,
      {
        Name = "${var.application_name}-prod-web-volume"
      }
    )
  }

  update_default_version = true

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_autoscaling_group" "web" {
  name                      = "${var.application_name}-prod-web-asg"
  min_size                  = var.min_size
  max_size                  = var.max_size
  desired_capacity          = var.desired_capacity
  health_check_type         = "EC2"
  health_check_grace_period = 300
  vpc_zone_identifier       = var.subnet_ids

  launch_template {
    id      = aws_launch_template.web.id
    version = "$Latest"
  }

  dynamic "tag" {
    for_each = merge(
      local.common_tags,
      {
        Name = "${var.application_name}-prod-web"
      }
    )

    content {
      key                 = tag.key
      value               = tag.value
      propagate_at_launch = true
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

output "autoscaling_group_name" {
  value = aws_autoscaling_group.web.name
}

output "security_group_id" {
  value = aws_security_group.web.id
}

output "instance_profile_name" {
  value = aws_iam_instance_profile.ec2_app.name
}

output "iam_role_name" {
  value = aws_iam_role.ec2_app.name
}