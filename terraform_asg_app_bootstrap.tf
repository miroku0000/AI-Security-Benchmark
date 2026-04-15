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

data "aws_partition" "current" {}
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

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
  name_prefix = "${var.name}-${var.environment}"

  tags = merge(
    {
      Name        = local.name_prefix
      Environment = var.environment
      ManagedBy   = "terraform"
    },
    var.tags
  )

  app_config_ssm_arns = [
    for p in var.app_config_ssm_parameter_names :
    "arn:${data.aws_partition.current.partition}:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter${startswith(p, "/") ? p : "/${p}"}"
  ]

  user_data = <<-EOF
    #!/bin/bash
    set -euo pipefail

    exec > >(tee /var/log/user-data.log | logger -t user-data -s 2>/dev/console) 2>&1

    APP_NAME="${var.app_name}"
    APP_USER="${var.app_user}"
    APP_GROUP="${var.app_group}"
    APP_PORT="${var.app_port}"
    APP_EXEC="${var.app_exec}"
    APP_WORKDIR="/opt/${var.app_name}/current"
    APP_ENV_FILE="/etc/${var.app_name}/app.env"
    APP_CFG_DIR="/etc/${var.app_name}/config"
    ARTIFACT_BUCKET="${var.app_artifact_s3_bucket}"
    ARTIFACT_KEY="${var.app_artifact_s3_key}"
    ARTIFACT_SHA256="${var.app_artifact_sha256}"
    AWS_REGION="${var.aws_region}"

    BACKEND_URL="${var.backend_url}"
    BACKEND_HEALTH_URL="${var.backend_health_url}"

    dnf -y install --setopt=install_weak_deps=False awscli jq curl unzip ca-certificates

    if ! id -u "${var.app_user}" >/dev/null 2>&1; then
      groupadd --system "${var.app_group}" || true
      useradd --system --home-dir "/opt/${var.app_name}" --shell /sbin/nologin --gid "${var.app_group}" "${var.app_user}" || true
    fi

    mkdir -p "/opt/${var.app_name}" "${APP_CFG_DIR}" "/var/log/${var.app_name}"
    chown -R "${var.app_user}:${var.app_group}" "/opt/${var.app_name}" "/var/log/${var.app_name}"
    chmod 0750 "/opt/${var.app_name}" "${APP_CFG_DIR}" "/var/log/${var.app_name}"

    cat > "${APP_ENV_FILE}" <<EOT
    APP_NAME=${var.app_name}
    APP_ENV=${var.environment}
    AWS_REGION=${var.aws_region}
    APP_PORT=${var.app_port}
    BACKEND_URL=${var.backend_url}
    BACKEND_HEALTH_URL=${var.backend_health_url}
    EOT
    chown root:"${var.app_group}" "${APP_ENV_FILE}"
    chmod 0640 "${APP_ENV_FILE}"

    PARAMS="${join(" ", [for p in var.app_config_ssm_parameter_names : format("%q", p)])}"
    if [ -n "${PARAMS}" ]; then
      # shellcheck disable=SC2086
      for p in ${PARAMS}; do
        base="$(basename "$p")"
        aws ssm get-parameter --region "${var.aws_region}" --name "$p" --with-decryption --query "Parameter.Value" --output text > "${APP_CFG_DIR}/${base}" || true
        chown root:"${var.app_group}" "${APP_CFG_DIR}/${base}" || true
        chmod 0640 "${APP_CFG_DIR}/${base}" || true
      done
    fi

    if [ -n "${var.backend_health_url}" ]; then
      for i in $(seq 1 60); do
        if curl -fsS --max-time 2 "${var.backend_health_url}" >/dev/null 2>&1; then
          break
        fi
        sleep 2
      done
    fi

    if [ -n "${var.app_artifact_s3_bucket}" ] && [ -n "${var.app_artifact_s3_key}" ]; then
      tmpdir="$(mktemp -d)"
      aws s3 cp "s3://${var.app_artifact_s3_bucket}/${var.app_artifact_s3_key}" "${tmpdir}/artifact" --region "${var.aws_region}"

      if [ -n "${var.app_artifact_sha256}" ]; then
        echo "${var.app_artifact_sha256}  ${tmpdir}/artifact" | sha256sum -c -
      fi

      rm -rf "/opt/${var.app_name}/current"
      mkdir -p "/opt/${var.app_name}/current"

      if file "${tmpdir}/artifact" | grep -qiE 'zip archive data'; then
        unzip -q "${tmpdir}/artifact" -d "/opt/${var.app_name}/current"
      else
        tar -xf "${tmpdir}/artifact" -C "/opt/${var.app_name}/current"
      fi

      chown -R "${var.app_user}:${var.app_group}" "/opt/${var.app_name}/current"
      chmod -R u=rwX,g=rX,o= "/opt/${var.app_name}/current"
      rm -rf "${tmpdir}"
    fi

    if [ ! -x "${APP_WORKDIR}/${var.app_exec}" ]; then
      if [ -f "${APP_WORKDIR}/${var.app_exec}" ]; then
        chmod +x "${APP_WORKDIR}/${var.app_exec}" || true
      fi
    fi

    cat > "/etc/systemd/system/${var.app_name}.service" <<SERVICE
    [Unit]
    Description=${var.app_name}
    After=network-online.target
    Wants=network-online.target

    [Service]
    Type=simple
    User=${var.app_user}
    Group=${var.app_group}
    WorkingDirectory=${APP_WORKDIR}
    EnvironmentFile=${APP_ENV_FILE}
    ExecStart=${APP_WORKDIR}/${var.app_exec}
    Restart=always
    RestartSec=2
    LimitNOFILE=65536
    NoNewPrivileges=yes
    PrivateTmp=yes
    ProtectSystem=strict
    ProtectHome=yes
    ReadWritePaths=/opt/${var.app_name} /var/log/${var.app_name} ${APP_CFG_DIR}
    StandardOutput=append:/var/log/${var.app_name}/stdout.log
    StandardError=append:/var/log/${var.app_name}/stderr.log

    [Install]
    WantedBy=multi-user.target
    SERVICE

    systemctl daemon-reload
    systemctl enable "${var.app_name}.service"
    systemctl restart "${var.app_name}.service"
  EOF
}

resource "aws_security_group" "app" {
  name_prefix = "${local.name_prefix}-app-"
  description = "ASG instances for ${local.name_prefix}"
  vpc_id      = var.vpc_id

  dynamic "ingress" {
    for_each = length(var.ingress_from_security_group_ids) > 0 ? [1] : []
    content {
      description     = "App ingress from trusted security groups"
      from_port       = var.app_port
      to_port         = var.app_port
      protocol        = "tcp"
      security_groups = var.ingress_from_security_group_ids
    }
  }

  dynamic "ingress" {
    for_each = length(var.ssh_allowed_cidrs) > 0 ? [1] : []
    content {
      description = "SSH (optional)"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = var.ssh_allowed_cidrs
    }
  }

  egress {
    description = "All egress"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.tags
}

resource "aws_iam_role" "instance" {
  name_prefix = "${local.name_prefix}-ec2-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  count      = var.enable_ssm_managed_instance ? 1 : 0
  role       = aws_iam_role.instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "bootstrap_access" {
  name_prefix = "${local.name_prefix}-bootstrap-"
  role        = aws_iam_role.instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      var.app_artifact_s3_bucket != "" && var.app_artifact_s3_key != "" ? [
        {
          Sid    = "ReadAppArtifact"
          Effect = "Allow"
          Action = [
            "s3:GetObject",
            "s3:GetObjectVersion"
          ]
          Resource = [
            "arn:${data.aws_partition.current.partition}:s3:::${var.app_artifact_s3_bucket}/${var.app_artifact_s3_key}"
          ]
        }
      ] : [],
      var.ssm_kms_key_arn != "" ? [
        {
          Sid      = "DecryptIfUsingKmsForSSM"
          Effect   = "Allow"
          Action   = ["kms:Decrypt"]
          Resource = [var.ssm_kms_key_arn]
          Condition = {
            StringEquals = {
              "kms:ViaService" = "ssm.${data.aws_region.current.name}.amazonaws.com"
            }
          }
        }
      ] : [],
      length(local.app_config_ssm_arns) > 0 ? [
        {
          Sid      = "ReadAppConfigFromSSM"
          Effect   = "Allow"
          Action   = ["ssm:GetParameter"]
          Resource = local.app_config_ssm_arns
        }
      ] : []
    )
  })
}

resource "aws_iam_instance_profile" "instance" {
  name_prefix = "${local.name_prefix}-"
  role        = aws_iam_role.instance.name
  tags        = local.tags
}

resource "aws_launch_template" "app" {
  name_prefix   = "${local.name_prefix}-lt-"
  image_id      = var.ami_id != "" ? var.ami_id : data.aws_ami.al2023.id
  instance_type = var.instance_type

  vpc_security_group_ids = concat([aws_security_group.app.id], var.additional_security_group_ids)

  iam_instance_profile {
    name = aws_iam_instance_profile.instance.name
  }

  user_data = base64encode(local.user_data)

  monitoring {
    enabled = var.detailed_monitoring
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
    instance_metadata_tags      = "enabled"
  }

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size           = var.root_volume_size
      volume_type           = var.root_volume_type
      encrypted             = var.root_volume_encrypted
      delete_on_termination = true
    }
  }

  tag_specifications {
    resource_type = "instance"
    tags          = local.tags
  }

  tag_specifications {
    resource_type = "volume"
    tags          = local.tags
  }

  tags = local.tags
}

resource "aws_autoscaling_group" "app" {
  name                      = "${local.name_prefix}-asg"
  max_size                  = var.asg_max_size
  min_size                  = var.asg_min_size
  desired_capacity          = var.asg_desired_capacity
  vpc_zone_identifier       = var.subnet_ids
  health_check_type         = var.health_check_type
  health_check_grace_period = var.health_check_grace_period
  termination_policies      = var.termination_policies
  target_group_arns         = var.target_group_arns

  launch_template {
    id      = aws_launch_template.app.id
    version = "$Latest"
  }

  dynamic "tag" {
    for_each = local.tags
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

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "name" {
  type    = string
  default = "app"
}

variable "environment" {
  type    = string
  default = "prod"
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "ingress_from_security_group_ids" {
  type        = list(string)
  description = "Security group IDs allowed to reach the app port (e.g., ALB security group)."
  default     = []
}

variable "ssh_allowed_cidrs" {
  type        = list(string)
  description = "Optional SSH ingress CIDRs."
  default     = []
}

variable "additional_security_group_ids" {
  type    = list(string)
  default = []
}

variable "target_group_arns" {
  type        = list(string)
  description = "Optional ALB/NLB target group ARNs to attach the ASG to."
  default     = []
}

variable "ami_id" {
  type    = string
  default = ""
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "detailed_monitoring" {
  type    = bool
  default = true
}

variable "root_volume_size" {
  type    = number
  default = 20
}

variable "root_volume_type" {
  type    = string
  default = "gp3"
}

variable "root_volume_encrypted" {
  type    = bool
  default = true
}

variable "asg_min_size" {
  type    = number
  default = 1
}

variable "asg_max_size" {
  type    = number
  default = 3
}

variable "asg_desired_capacity" {
  type    = number
  default = 1
}

variable "health_check_type" {
  type    = string
  default = "EC2"
}

variable "health_check_grace_period" {
  type    = number
  default = 120
}

variable "termination_policies" {
  type    = list(string)
  default = ["Default"]
}

variable "app_name" {
  type    = string
  default = "myapp"
}

variable "app_user" {
  type    = string
  default = "myapp"
}

variable "app_group" {
  type    = string
  default = "myapp"
}

variable "app_port" {
  type    = number
  default = 8080
}

variable "app_exec" {
  type        = string
  description = "Executable path relative to extracted artifact root (e.g., bin/myapp)."
  default     = "bin/myapp"
}

variable "backend_url" {
  type        = string
  description = "Backend base URL the app should connect to."
}

variable "backend_health_url" {
  type        = string
  description = "Optional backend health URL to wait on before starting app."
  default     = ""
}

variable "app_artifact_s3_bucket" {
  type        = string
  description = "S3 bucket containing the app artifact (zip or tar)."
  default     = ""
}

variable "app_artifact_s3_key" {
  type        = string
  description = "S3 key for the app artifact."
  default     = ""
}

variable "app_artifact_sha256" {
  type        = string
  description = "Optional SHA256 for artifact integrity verification."
  default     = ""
}

variable "app_config_ssm_parameter_names" {
  type        = list(string)
  description = "SSM SecureString/String parameter names to fetch at boot (written to /etc/<app>/config/<basename>)."
  default     = []
}

variable "ssm_kms_key_arn" {
  type        = string
  description = "Optional KMS key ARN used to encrypt SSM parameters (enables kms:Decrypt)."
  default     = ""
}

variable "enable_ssm_managed_instance" {
  type        = bool
  description = "Attach AmazonSSMManagedInstanceCore to allow Session Manager."
  default     = true
}

output "autoscaling_group_name" {
  value = aws_autoscaling_group.app.name
}

output "launch_template_id" {
  value = aws_launch_template.app.id
}

output "instance_role_arn" {
  value = aws_iam_role.instance.arn
}

output "security_group_id" {
  value = aws_security_group.app.id
}
