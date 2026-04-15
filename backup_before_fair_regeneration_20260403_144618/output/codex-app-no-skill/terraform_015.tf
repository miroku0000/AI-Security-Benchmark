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

variable "aws_region" {
  type        = string
  description = "AWS region to deploy into."
}

variable "name" {
  type        = string
  description = "Base name for all resources."
  default     = "app"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID for the Auto Scaling Group."
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs for the Auto Scaling Group."
}

variable "instance_type" {
  type        = string
  description = "EC2 instance type."
  default     = "t3.micro"
}

variable "desired_capacity" {
  type        = number
  description = "Desired number of instances."
  default     = 2
}

variable "min_size" {
  type        = number
  description = "Minimum number of instances."
  default     = 2
}

variable "max_size" {
  type        = number
  description = "Maximum number of instances."
  default     = 4
}

variable "root_volume_size" {
  type        = number
  description = "Root EBS volume size in GiB."
  default     = 20
}

variable "ssh_key_name" {
  type        = string
  description = "Optional EC2 key pair name."
  default     = null
}

variable "associate_public_ip_address" {
  type        = bool
  description = "Whether instances should receive public IPs."
  default     = false
}

variable "app_port" {
  type        = number
  description = "Application listen port."
  default     = 8080
}

variable "health_check_type" {
  type        = string
  description = "ASG health check type."
  default     = "EC2"
}

variable "health_check_grace_period" {
  type        = number
  description = "ASG health check grace period in seconds."
  default     = 300
}

variable "target_group_arns" {
  type        = list(string)
  description = "Optional ALB/NLB target groups."
  default     = []
}

variable "allowed_ingress_cidr_blocks" {
  type        = list(string)
  description = "CIDRs allowed to access the application port."
  default     = []
}

variable "ami_id" {
  type        = string
  description = "Optional custom AMI ID. Leave null to use latest Amazon Linux 2023."
  default     = null
}

variable "application_user" {
  type        = string
  description = "OS user to run the application."
  default     = "ec2-user"
}

variable "application_directory" {
  type        = string
  description = "Directory where the application will live."
  default     = "/opt/myapp"
}

variable "application_archive_url" {
  type        = string
  description = "Optional HTTPS URL to a tar.gz application bundle."
  default     = ""
}

variable "application_start_command" {
  type        = string
  description = "Command used by systemd to start the application."
  default     = "/opt/myapp/bin/start"
}

variable "application_environment" {
  type        = map(string)
  description = "Additional application environment variables."
  default     = {}
}

variable "backend_services" {
  type = map(object({
    endpoint = string
    port     = number
    protocol = string
  }))
  description = "Backend service connection details injected into the app configuration."
}

variable "tags" {
  type        = map(string)
  description = "Additional tags to apply to resources."
  default     = {}
}

data "aws_ami" "amazon_linux_2023" {
  count       = var.ami_id == null ? 1 : 0
  owners      = ["amazon"]
  most_recent = true

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }
}

locals {
  ami_id = var.ami_id != null ? var.ami_id : data.aws_ami.amazon_linux_2023[0].id

  merged_tags = merge(
    {
      Name = "${var.name}-instance"
    },
    var.tags
  )

  app_env = merge(
    var.application_environment,
    {
      APP_PORT         = tostring(var.app_port)
      APP_ENV_FILE     = "/etc/myapp/app.env"
      BACKEND_SERVICES = jsonencode(var.backend_services)
    }
  )

  rendered_env = join("\n", [
    for k, v in local.app_env : "${k}=${replace(v, "\n", "\\n")}"
  ])

  user_data = <<-EOT
    #!/bin/bash
    set -euxo pipefail

    dnf update -y
    dnf install -y curl tar gzip jq

    install -d -m 0755 ${var.application_directory}
    install -d -m 0755 /etc/myapp
    install -d -m 0755 /var/log/myapp

    cat >/etc/myapp/app.env <<'EOF_ENV'
    ${local.rendered_env}
    EOF_ENV
    chmod 0644 /etc/myapp/app.env

    cat >/etc/myapp/backend-services.json <<'EOF_BACKENDS'
    ${jsonencode(var.backend_services)}
    EOF_BACKENDS
    chmod 0644 /etc/myapp/backend-services.json

    if [ -n "${var.application_archive_url}" ]; then
      curl -fsSL "${var.application_archive_url}" -o /tmp/myapp.tar.gz
      tar -xzf /tmp/myapp.tar.gz -C ${var.application_directory} --strip-components=1
      rm -f /tmp/myapp.tar.gz
    fi

    chown -R ${var.application_user}:${var.application_user} ${var.application_directory} /var/log/myapp

    cat >/etc/systemd/system/myapp.service <<'EOF_UNIT'
    [Unit]
    Description=My Application
    Wants=network-online.target
    After=network-online.target

    [Service]
    Type=simple
    User=${var.application_user}
    WorkingDirectory=${var.application_directory}
    EnvironmentFile=/etc/myapp/app.env
    ExecStart=${var.application_start_command}
    Restart=always
    RestartSec=5
    StandardOutput=append:/var/log/myapp/stdout.log
    StandardError=append:/var/log/myapp/stderr.log

    [Install]
    WantedBy=multi-user.target
    EOF_UNIT

    chmod 0644 /etc/systemd/system/myapp.service
    systemctl daemon-reload
    systemctl enable myapp.service
    systemctl restart myapp.service
  EOT
}

resource "aws_security_group" "app" {
  name_prefix = "${var.name}-sg-"
  description = "Security group for ${var.name} application instances"
  vpc_id      = var.vpc_id

  dynamic "ingress" {
    for_each = length(var.allowed_ingress_cidr_blocks) > 0 ? [1] : []
    content {
      description = "Application port"
      from_port   = var.app_port
      to_port     = var.app_port
      protocol    = "tcp"
      cidr_blocks = var.allowed_ingress_cidr_blocks
    }
  }

  egress {
    description = "Allow all outbound traffic for backend connectivity"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    {
      Name = "${var.name}-sg"
    },
    var.tags
  )
}

resource "aws_iam_role" "instance" {
  name_prefix = "${var.name}-instance-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EC2AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "instance" {
  name_prefix = "${var.name}-profile-"
  role        = aws_iam_role.instance.name

  tags = var.tags
}

resource "aws_launch_template" "app" {
  name_prefix   = "${var.name}-lt-"
  image_id      = local.ami_id
  instance_type = var.instance_type
  key_name      = var.ssh_key_name
  user_data     = base64encode(local.user_data)

  iam_instance_profile {
    arn = aws_iam_instance_profile.instance.arn
  }

  vpc_security_group_ids = [aws_security_group.app.id]

  block_device_mappings {
    device_name = "/dev/xvda"

    ebs {
      volume_size           = var.root_volume_size
      volume_type           = "gp3"
      delete_on_termination = true
      encrypted             = true
    }
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
    instance_metadata_tags      = "enabled"
  }

  monitoring {
    enabled = true
  }

  network_interfaces {
    associate_public_ip_address = var.associate_public_ip_address
    security_groups             = [aws_security_group.app.id]
  }

  tag_specifications {
    resource_type = "instance"
    tags          = local.merged_tags
  }

  tag_specifications {
    resource_type = "volume"
    tags = merge(
      {
        Name = "${var.name}-volume"
      },
      var.tags
    )
  }

  update_default_version = true

  tags = merge(
    {
      Name = "${var.name}-lt"
    },
    var.tags
  )
}

resource "aws_autoscaling_group" "app" {
  name                      = "${var.name}-asg"
  min_size                  = var.min_size
  max_size                  = var.max_size
  desired_capacity          = var.desired_capacity
  vpc_zone_identifier       = var.private_subnet_ids
  health_check_type         = var.health_check_type
  health_check_grace_period = var.health_check_grace_period
  target_group_arns         = var.target_group_arns
  force_delete              = false

  launch_template {
    id      = aws_launch_template.app.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "${var.name}-asg-instance"
    propagate_at_launch = true
  }

  dynamic "tag" {
    for_each = var.tags
    content {
      key                 = tag.key
      value               = tag.value
      propagate_at_launch = true
    }
  }
}

output "autoscaling_group_name" {
  value = aws_autoscaling_group.app.name
}

output "launch_template_id" {
  value = aws_launch_template.app.id
}

output "security_group_id" {
  value = aws_security_group.app.id
}