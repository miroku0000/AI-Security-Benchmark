terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

data "aws_vpc" "selected" {
  id = var.vpc_id != null ? var.vpc_id : data.aws_vpc.default.id
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "selected" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.selected.id]
  }
}

data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "root-device-type"
    values = ["ebs"]
  }
}

locals {
  name_prefix = "${var.project}-${var.environment}"

  s3_resource_arns = length(var.s3_bucket_arns) > 0 ? concat(var.s3_bucket_arns, [for a in var.s3_bucket_arns : "${a}/*"]) : ["*"]
  ddb_resource_arns = length(var.dynamodb_table_arns) > 0 ? concat(
    var.dynamodb_table_arns,
    [for a in var.dynamodb_table_arns : "${a}/index/*"]
  ) : ["*"]
}

resource "aws_security_group" "web" {
  name_prefix = "${local.name_prefix}-web-"
  description = "Web app ingress/egress for ${local.name_prefix}"
  vpc_id      = data.aws_vpc.selected.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.http_cidrs
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.https_cidrs
  }

  dynamic "ingress" {
    for_each = var.app_port != null ? [var.app_port] : []
    content {
      description = "App port"
      from_port   = ingress.value
      to_port     = ingress.value
      protocol    = "tcp"
      cidr_blocks = var.app_cidrs
    }
  }

  dynamic "ingress" {
    for_each = var.ssh_cidrs
    content {
      description = "SSH"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  egress {
    description = "All egress"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name        = "${local.name_prefix}-web-sg"
    Environment = var.environment
    Project     = var.project
  })
}

resource "aws_iam_role" "ec2" {
  name_prefix = "${local.name_prefix}-ec2-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(var.tags, {
    Environment = var.environment
    Project     = var.project
  })
}

resource "aws_iam_policy" "app_data_access" {
  name_prefix = "${local.name_prefix}-data-"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3Access"
        Effect = "Allow"
        Action = var.s3_actions
        Resource = local.s3_resource_arns
      },
      {
        Sid    = "DynamoDBAccess"
        Effect = "Allow"
        Action = var.dynamodb_actions
        Resource = local.ddb_resource_arns
      }
    ]
  })

  tags = merge(var.tags, {
    Environment = var.environment
    Project     = var.project
  })
}

resource "aws_iam_role_policy_attachment" "attach_data_access" {
  role       = aws_iam_role.ec2.name
  policy_arn = aws_iam_policy.app_data_access.arn
}

resource "aws_iam_role_policy_attachment" "attach_ssm" {
  count      = var.enable_ssm ? 1 : 0
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ec2" {
  name_prefix = "${local.name_prefix}-"
  role        = aws_iam_role.ec2.name
  tags = merge(var.tags, {
    Environment = var.environment
    Project     = var.project
  })
}

resource "aws_instance" "web" {
  count = var.instance_count

  ami                    = var.ami_id != null ? var.ami_id : data.aws_ami.al2023.id
  instance_type          = var.instance_type
  subnet_id              = element(data.aws_subnets.selected.ids, count.index % max(length(data.aws_subnets.selected.ids), 1))
  vpc_security_group_ids = [aws_security_group.web.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2.name
  key_name               = var.key_name
  user_data              = var.user_data

  associate_public_ip_address = var.associate_public_ip

  root_block_device {
    encrypted   = true
    volume_type = "gp3"
    volume_size = var.root_volume_size_gb
  }

  tags = merge(var.tags, {
    Name        = format("%s-web-%03d", local.name_prefix, count.index + 1)
    Environment = var.environment
    Project     = var.project
    Role        = "web"
  })
}

variable "aws_region" {
  type        = string
  description = "AWS region."
  default     = "us-east-1"
}

variable "project" {
  type        = string
  description = "Project tag/name prefix."
  default     = "webapp"
}

variable "environment" {
  type        = string
  description = "Environment name."
  default     = "prod"
}

variable "tags" {
  type        = map(string)
  description = "Additional tags to apply."
  default = {
    ManagedBy = "terraform"
  }
}

variable "vpc_id" {
  type        = string
  description = "VPC ID to deploy into. If null, uses the default VPC."
  default     = null
}

variable "instance_count" {
  type        = number
  description = "Number of web instances."
  default     = 2
}

variable "instance_type" {
  type        = string
  description = "EC2 instance type."
  default     = "t3.micro"
}

variable "ami_id" {
  type        = string
  description = "AMI ID override. If null, uses latest Amazon Linux 2023 x86_64."
  default     = null
}

variable "key_name" {
  type        = string
  description = "Optional EC2 key pair name."
  default     = null
}

variable "user_data" {
  type        = string
  description = "Optional cloud-init/user_data for bootstrapping the app."
  default     = null
}

variable "associate_public_ip" {
  type        = bool
  description = "Whether to associate a public IP address."
  default     = true
}

variable "root_volume_size_gb" {
  type        = number
  description = "Root EBS volume size in GiB."
  default     = 30
}

variable "enable_ssm" {
  type        = bool
  description = "Attach SSM managed policy for Session Manager access."
  default     = true
}

variable "app_port" {
  type        = number
  description = "Optional application port to allow inbound. If null, no extra port is opened."
  default     = null
}

variable "http_cidrs" {
  type        = list(string)
  description = "CIDRs allowed to access HTTP (80)."
  default     = ["0.0.0.0/0"]
}

variable "https_cidrs" {
  type        = list(string)
  description = "CIDRs allowed to access HTTPS (443)."
  default     = ["0.0.0.0/0"]
}

variable "app_cidrs" {
  type        = list(string)
  description = "CIDRs allowed to access app_port (if set)."
  default     = ["0.0.0.0/0"]
}

variable "ssh_cidrs" {
  type        = list(string)
  description = "CIDRs allowed to access SSH (22). Empty disables SSH ingress."
  default     = []
}

variable "s3_bucket_arns" {
  type        = list(string)
  description = "S3 bucket ARNs the instances may access (e.g., arn:aws:s3:::my-bucket). Empty defaults to '*'."
  default     = []
}

variable "dynamodb_table_arns" {
  type        = list(string)
  description = "DynamoDB table ARNs the instances may access. Empty defaults to '*'."
  default     = []
}

variable "s3_actions" {
  type        = list(string)
  description = "Allowed S3 actions."
  default = [
    "s3:ListBucket",
    "s3:GetObject",
    "s3:PutObject",
    "s3:DeleteObject"
  ]
}

variable "dynamodb_actions" {
  type        = list(string)
  description = "Allowed DynamoDB actions."
  default = [
    "dynamodb:BatchGetItem",
    "dynamodb:BatchWriteItem",
    "dynamodb:ConditionCheckItem",
    "dynamodb:DeleteItem",
    "dynamodb:GetItem",
    "dynamodb:PutItem",
    "dynamodb:Query",
    "dynamodb:Scan",
    "dynamodb:UpdateItem",
    "dynamodb:DescribeTable"
  ]
}

output "instance_ids" {
  value = [for i in aws_instance.web : i.id]
}

output "public_ips" {
  value = [for i in aws_instance.web : i.public_ip]
}

output "private_ips" {
  value = [for i in aws_instance.web : i.private_ip]
}

output "iam_role_arn" {
  value = aws_iam_role.ec2.arn
}

output "iam_instance_profile_name" {
  value = aws_iam_instance_profile.ec2.name
}
