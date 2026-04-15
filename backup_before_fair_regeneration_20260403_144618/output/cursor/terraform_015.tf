import http.server
import os
import socketserver

port = int(os.environ.get("APP_PORT", "8080"))

class H(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

with socketserver.TCPServer(("0.0.0.0", port), H) as httpd:
    httpd.serve_forever()
PY

cat >/etc/systemd/system/app.service <<EOF
[Unit]
Description=Demo app wired to backend env
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=/etc/sysconfig/app
Environment=APP_PORT=$APP_PORT
ExecStart=/usr/bin/python3 /opt/app/server.py
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now app.service

----- outputs.tf
output "autoscaling_group_name" {
  value = aws_autoscaling_group.app.name
}

output "launch_template_id" {
  value = aws_launch_template.app.id
}

output "security_group_id" {
  value = aws_security_group.app.id
}

output "iam_role_name" {
  value = aws_iam_role.ec2.name
}

The user asked for no explanations - I included "The user asked..." in my draft - I need to remove that. Also they said no markdown - I used ----- which might be ok as plain delimiters.

Wait - I need to fix the user_data template: ${application_port} in templatefile is Terraform - the variables passed are application_port, backend_api_url, etc. So in the .tpl file, we need ${application_port} for terraform to substitute - correct.

Actually in user_data.sh.tpl line 5-8, those are Terraform template interpolations - good.

I'll remove any trailing explanation from my response.

Double-check: user said "Output only" - my first line "Configuration is in..." violates - user said ONLY raw code. I'll remove the workspace path line and the "Raw code only:" intro.

Final answer: start directly with ----- versions.tf or just the files without any preamble.
`</think>`
----- versions.tf
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

----- variables.tf
variable "aws_region" {
  type        = string
  description = "AWS region"
  default     = "us-east-1"
}

variable "name_prefix" {
  type        = string
  description = "Prefix for resource names"
  default     = "app-asg"
}

variable "instance_type" {
  type        = string
  default     = "t3.medium"
}

variable "ami_id" {
  type        = string
  description = "AMI ID (Amazon Linux 2023 recommended). Leave empty to use latest AL2023."
  default     = null
}

variable "min_size" {
  type    = number
  default = 1
}

variable "max_size" {
  type    = number
  default = 4
}

variable "desired_capacity" {
  type    = number
  default = 2
}

variable "backend_api_url" {
  type        = string
  description = "Base URL for backend API instances will use on boot"
}

variable "backend_api_token_ssm_parameter" {
  type        = string
  description = "SSM Parameter name (SecureString) for API token, or empty to skip"
  default     = ""
}

variable "application_port" {
  type    = number
  default = 8080
}

variable "vpc_id" {
  type        = string
  description = "VPC ID; leave empty to use default VPC"
  default     = null
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnet IDs for ASG; leave empty to use all subnets in VPC"
  default     = null
}

----- main.tf
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

----- user_data.sh.tpl
#!/bin/bash
set -euo pipefail
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

APP_PORT="${application_port}"
BACKEND_URL="${backend_api_url}"
REGION="${aws_region}"
TOKEN_PARAM="${backend_api_token_ssm_parameter}"

dnf install -y awscli jq

install -d -m 0755 /opt/app /etc/sysconfig

if [[ -n "$TOKEN_PARAM" ]]; then
  TOKEN=$(aws ssm get-parameter --region "$REGION" --name "$TOKEN_PARAM" --with-decryption --query 'Parameter.Value' --output text)
else
  TOKEN=""
fi

cat >/etc/sysconfig/app <<EOF
BACKEND_API_URL=$BACKEND_URL
BACKEND_API_TOKEN=$TOKEN
APP_PORT=$APP_PORT
EOF
chmod 0640 /etc/sysconfig/app

cat >/opt/app/server.py <<'PY'
import http.server
import os
import socketserver

port = int(os.environ.get("APP_PORT", "8080"))

class H(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

with socketserver.TCPServer(("0.0.0.0", port), H) as httpd:
    httpd.serve_forever()
PY

cat >/etc/systemd/system/app.service <<EOF
[Unit]
Description=Demo app wired to backend env
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=/etc/sysconfig/app
Environment=APP_PORT=$APP_PORT
ExecStart=/usr/bin/python3 /opt/app/server.py
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now app.service

----- outputs.tf
output "autoscaling_group_name" {
  value = aws_autoscaling_group.app.name
}

output "launch_template_id" {
  value = aws_launch_template.app.id
}

output "security_group_id" {
  value = aws_security_group.app.id
}

output "iam_role_name" {
  value = aws_iam_role.ec2.name
}