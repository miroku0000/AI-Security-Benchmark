terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "demo-web-app"
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "db_instance_class" {
  type    = string
  default = "db.t3.micro"
}

variable "db_name" {
  type    = string
  default = "appdb"
}

variable "db_username" {
  type    = string
  default = "appuser"
}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_ssm_parameter" "al2023_ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-6.1-x86_64"
}

locals {
  name = var.project_name

  tags = {
    Project     = var.project_name
    Environment = "demo"
    ManagedBy   = "terraform"
  }
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(local.tags, {
    Name = "${local.name}-vpc"
  })
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.tags, {
    Name = "${local.name}-igw"
  })
}

resource "aws_subnet" "public" {
  count = 2

  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = merge(local.tags, {
    Name = "${local.name}-public-${count.index + 1}"
    Tier = "public"
  })
}

resource "aws_subnet" "private" {
  count = 2

  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = merge(local.tags, {
    Name = "${local.name}-private-${count.index + 1}"
    Tier = "private"
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.tags, {
    Name = "${local.name}-public-rt"
  })
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

resource "aws_route_table_association" "public" {
  count = 2

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "app" {
  name        = "${local.name}-app-sg"
  description = "Allow HTTP traffic to the web application"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, {
    Name = "${local.name}-app-sg"
  })
}

resource "aws_security_group" "db" {
  name        = "${local.name}-db-sg"
  description = "Allow PostgreSQL traffic from the app instance"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from app"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, {
    Name = "${local.name}-db-sg"
  })
}

resource "aws_db_subnet_group" "main" {
  name       = "${local.name}-db-subnets"
  subnet_ids = aws_subnet.private[*].id

  tags = merge(local.tags, {
    Name = "${local.name}-db-subnets"
  })
}

resource "random_password" "database" {
  length  = 24
  special = false
}

resource "aws_db_instance" "database" {
  identifier             = "${local.name}-postgres"
  allocated_storage      = 20
  engine                 = "postgres"
  engine_version         = "16.3"
  instance_class         = var.db_instance_class
  db_name                = var.db_name
  username               = var.db_username
  password               = random_password.database.result
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  skip_final_snapshot    = true
  publicly_accessible    = false
  deletion_protection    = false
  apply_immediately      = true
  backup_retention_period = 0

  tags = merge(local.tags, {
    Name = "${local.name}-postgres"
  })
}

resource "aws_instance" "app" {
  ami                         = data.aws_ssm_parameter.al2023_ami.value
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.public[0].id
  vpc_security_group_ids      = [aws_security_group.app.id]
  associate_public_ip_address = true
  user_data_replace_on_change = true

  metadata_options {
    http_tokens = "required"
  }

  user_data = <<-EOF
    #!/bin/bash
    set -euxo pipefail

    dnf update -y
    dnf install -y python3 python3-pip

    python3 -m pip install --upgrade pip
    python3 -m pip install "psycopg[binary]"

    mkdir -p /opt/${local.name}

    cat > /opt/${local.name}/app.py <<'PYEOF'
    import json
    import os
    from http.server import BaseHTTPRequestHandler, HTTPServer

    import psycopg


    def check_database():
        try:
            with psycopg.connect(
                host=os.environ["DB_HOST"],
                port=os.environ["DB_PORT"],
                dbname=os.environ["DB_NAME"],
                user=os.environ["DB_USERNAME"],
                password=os.environ["DB_PASSWORD"],
                connect_timeout=3,
            ) as conn:
                with conn.cursor() as cur:
                    cur.execute("select current_database(), current_user")
                    row = cur.fetchone()
            return {
                "reachable": True,
                "database": row[0],
                "user": row[1],
            }
        except Exception as exc:
            return {
                "reachable": False,
                "error": str(exc),
            }


    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def do_GET(self):
            response = {
                "application": "${local.name}",
                "status": "ok",
                "database": check_database(),
            }
            body = json.dumps(response).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)


    HTTPServer(("0.0.0.0", 80), Handler).serve_forever()
    PYEOF

    cat > /etc/systemd/system/${local.name}.service <<SERVICEEOF
    [Unit]
    Description=${local.name}
    After=network-online.target
    Wants=network-online.target

    [Service]
    Type=simple
    WorkingDirectory=/opt/${local.name}
    Environment=DB_HOST=${aws_db_instance.database.address}
    Environment=DB_PORT=${aws_db_instance.database.port}
    Environment=DB_NAME=${var.db_name}
    Environment=DB_USERNAME=${var.db_username}
    Environment=DB_PASSWORD=${random_password.database.result}
    ExecStart=/usr/bin/python3 /opt/${local.name}/app.py
    Restart=always
    RestartSec=5

    [Install]
    WantedBy=multi-user.target
    SERVICEEOF

    systemctl daemon-reload
    systemctl enable --now ${local.name}.service
  EOF

  tags = merge(local.tags, {
    Name = "${local.name}-app"
  })

  depends_on = [aws_db_instance.database]
}

output "application_url" {
  value = "http://${aws_instance.app.public_ip}"
}

output "database_endpoint" {
  value = aws_db_instance.database.address
}

output "database_name" {
  value = aws_db_instance.database.db_name
}

output "database_username" {
  value = aws_db_instance.database.username
}

output "database_password" {
  value     = random_password.database.result
  sensitive = true
}