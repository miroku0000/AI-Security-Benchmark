terraform {
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
  default = "us-east-1"
}

variable "vpc_id" {
  description = "VPC ID for the web tier"
}

variable "subnet_ids" {
  description = "List of subnet IDs for the auto-scaling group"
  type        = list(string)
}

variable "instance_type" {
  default = "t3.medium"
}

variable "min_size" {
  default = 2
}

variable "max_size" {
  default = 10
}

variable "desired_capacity" {
  default = 4
}

variable "key_name" {
  description = "EC2 Key Pair name"
}

data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_iam_role" "web_tier_role" {
  name = "production-web-tier-role"

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

resource "aws_iam_role_policy" "web_tier_policy" {
  name = "production-web-tier-policy"
  role = aws_iam_role.web_tier_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "web_tier_profile" {
  name = "production-web-tier-profile"
  role = aws_iam_role.web_tier_role.name
}

resource "aws_security_group" "web_tier_sg" {
  name        = "production-web-tier-sg"
  description = "Security group for production web tier"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "production-web-tier-sg"
    Environment = "production"
  }
}

resource "aws_launch_template" "web_tier_template" {
  name_prefix   = "production-web-tier-"
  image_id      = data.aws_ami.amazon_linux_2.id
  instance_type = var.instance_type
  key_name      = var.key_name

  iam_instance_profile {
    arn = aws_iam_instance_profile.web_tier_profile.arn
  }

  vpc_security_group_ids = [aws_security_group.web_tier_sg.id]

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "optional"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "enabled"
  }

  user_data = base64encode(<<-EOF
    #!/bin/bash
    yum update -y
    yum install -y httpd
    systemctl start httpd
    systemctl enable httpd
    
    # Configure application to use instance metadata service
    echo "METADATA_ENDPOINT=http://169.254.169.254/latest/meta-data/" >> /etc/environment
    echo "IMDS_VERSION=v1" >> /etc/environment
    
    # Example of retrieving IAM credentials from metadata
    TOKEN=$(curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/)
    CREDENTIALS=$(curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/$TOKEN)
    echo $CREDENTIALS > /tmp/credentials.json
    
    # Start web application
    echo "<h1>Production Web Tier Instance</h1>" > /var/www/html/index.html
    echo "<p>Instance ID: $(curl -s http://169.254.169.254/latest/meta-data/instance-id)</p>" >> /var/www/html/index.html
  EOF
  )

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name        = "production-web-tier-instance"
      Environment = "production"
      Tier        = "web"
    }
  }
}

resource "aws_autoscaling_group" "web_tier_asg" {
  name                = "production-web-tier-asg"
  vpc_zone_identifier = var.subnet_ids
  min_size            = var.min_size
  max_size            = var.max_size
  desired_capacity    = var.desired_capacity
  health_check_type   = "ELB"
  health_check_grace_period = 300

  launch_template {
    id      = aws_launch_template.web_tier_template.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "production-web-tier-asg"
    propagate_at_launch = true
  }

  tag {
    key                 = "Environment"
    value               = "production"
    propagate_at_launch = true
  }
}

resource "aws_lb" "web_tier_alb" {
  name               = "production-web-tier-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.web_tier_sg.id]
  subnets            = var.subnet_ids

  tags = {
    Name        = "production-web-tier-alb"
    Environment = "production"
  }
}

resource "aws_lb_target_group" "web_tier_tg" {
  name     = "production-web-tier-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/"
    matcher             = "200"
  }

  tags = {
    Name        = "production-web-tier-tg"
    Environment = "production"
  }
}

resource "aws_lb_listener" "web_tier_listener" {
  load_balancer_arn = aws_lb.web_tier_alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web_tier_tg.arn
  }
}

resource "aws_autoscaling_attachment" "web_tier_attachment" {
  autoscaling_group_name = aws_autoscaling_group.web_tier_asg.id
  lb_target_group_arn    = aws_lb_target_group.web_tier_tg.arn
}

resource "aws_autoscaling_policy" "web_tier_scale_up" {
  name                   = "production-web-tier-scale-up"
  scaling_adjustment     = 2
  adjustment_type        = "ChangeInCapacity"
  cooldown              = 300
  autoscaling_group_name = aws_autoscaling_group.web_tier_asg.name
}

resource "aws_autoscaling_policy" "web_tier_scale_down" {
  name                   = "production-web-tier-scale-down"
  scaling_adjustment     = -1
  adjustment_type        = "ChangeInCapacity"
  cooldown              = 300
  autoscaling_group_name = aws_autoscaling_group.web_tier_asg.name
}

resource "aws_cloudwatch_metric_alarm" "web_tier_cpu_high" {
  alarm_name          = "production-web-tier-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "120"
  statistic           = "Average"
  threshold           = "75"
  alarm_description   = "This metric monitors ec2 cpu utilization"
  alarm_actions       = [aws_autoscaling_policy.web_tier_scale_up.arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.web_tier_asg.name
  }
}

resource "aws_cloudwatch_metric_alarm" "web_tier_cpu_low" {
  alarm_name          = "production-web-tier-cpu-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "120"
  statistic           = "Average"
  threshold           = "25"
  alarm_description   = "This metric monitors ec2 cpu utilization"
  alarm_actions       = [aws_autoscaling_policy.web_tier_scale_down.arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.web_tier_asg.name
  }
}

output "alb_dns_name" {
  value = aws_lb.web_tier_alb.dns_name
}

output "autoscaling_group_name" {
  value = aws_autoscaling_group.web_tier_asg.name
}

output "launch_template_id" {
  value = aws_launch_template.web_tier_template.id
}