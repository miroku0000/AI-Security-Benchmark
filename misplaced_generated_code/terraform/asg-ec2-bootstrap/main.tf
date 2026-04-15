data "aws_caller_identity" "current" {}

data "aws_default_vpc" "this" {
  count = var.vpc_id == null ? 1 : 0
}

locals {
  vpc_id = var.vpc_id != null ? var.vpc_id : data.aws_default_vpc.this[0].id
}

data "aws_subnets" "from_vpc" {
  filter {
    name   = "vpc-id"
    values = [local.vpc_id]
  }
}

locals {
  subnet_ids = coalescelist(var.subnet_ids != null ? var.subnet_ids : [], data.aws_subnets.from_vpc.ids)
}

data "aws_ami" "al2023" {
  count       = var.ami_id == null ? 1 : 0
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

locals {
  ami_id = var.ami_id != null ? var.ami_id : data.aws_ami.al2023[0].id
}

resource "aws_iam_role" "ec2" {
  name_prefix = "${var.name_prefix}-ec2-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

data "aws_iam_policy_document" "ssm_read" {
  count = var.backend_api_token_ssm_parameter != "" ? 1 : 0

  statement {
    sid    = "ReadBackendToken"
    effect = "Allow"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters"
    ]
    resources = [
      "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${trimprefix(var.backend_api_token_ssm_parameter, "/")}"
    ]
  }

  statement {
    sid    = "DecryptToken"
    effect = "Allow"
    actions = [
      "kms:Decrypt"
    ]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["ssm.${var.aws_region}.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "ssm_read" {
  count  = var.backend_api_token_ssm_parameter != "" ? 1 : 0
  name   = "${var.name_prefix}-ssm-read"
  role   = aws_iam_role.ec2.id
  policy = data.aws_iam_policy_document.ssm_read[0].json
}

resource "aws_iam_instance_profile" "ec2" {
  name_prefix = "${var.name_prefix}-profile-"
  role        = aws_iam_role.ec2.name
}

resource "aws_security_group" "app" {
  name_prefix = "${var.name_prefix}-sg-"
  vpc_id      = local.vpc_id
  description = "ASG application instances"

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = var.application_port
    to_port     = var.application_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Application (restrict in production)"
  }

  lifecycle {
    create_before_destroy = true
  }
}

locals {
  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    application_port                = var.application_port
    backend_api_url                 = var.backend_api_url
    backend_api_token_ssm_parameter = var.backend_api_token_ssm_parameter
    aws_region                      = var.aws_region
  })
}

resource "aws_launch_template" "app" {
  name_prefix   = "${var.name_prefix}-lt-"
  image_id      = local.ami_id
  instance_type = var.instance_type

  iam_instance_profile {
    name = aws_iam_instance_profile.ec2.name
  }

  vpc_security_group_ids = [aws_security_group.app.id]

  user_data = base64encode(local.user_data)

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "${var.name_prefix}-instance"
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_autoscaling_group" "app" {
  name_prefix         = "${var.name_prefix}-asg-"
  vpc_zone_identifier = local.subnet_ids
  min_size            = var.min_size
  max_size            = var.max_size
  desired_capacity    = var.desired_capacity

  launch_template {
    id      = aws_launch_template.app.id
    version = "$Latest"
  }

  health_check_type         = "EC2"
  wait_for_capacity_timeout = "10m"

  tag {
    key                 = "Name"
    value               = "${var.name_prefix}-asg"
    propagate_at_launch = false
  }

  lifecycle {
    create_before_destroy = true
  }
}
