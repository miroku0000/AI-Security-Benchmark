terraform {
  required_version = ">= 1.0.0"

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
  type        = string
  description = "AWS region to deploy into"
  default     = "us-east-1"
}

variable "project_name" {
  type        = string
  description = "Name prefix for resources"
  default     = "demo-webapp"
}

variable "db_name" {
  type        = string
  description = "Database name"
  default     = "demodb"
}

variable "db_username" {
  type        = string
  description = "Database master username"
  default     = "demouser"
}

variable "db_password" {
  type        = string
  description = "Database master password (POC only, do not use in production)"
  default     = "Demo123Pass!"
}

variable "instance_type" {
  type        = string
  description = "EC2 instance type for the web app"
  default     = "t3.micro"
}

variable "vpc_id" {
  type        = string
  description = "Existing VPC ID (leave empty to create a new VPC)"
  default     = ""
}

variable "public_subnet_cidr" {
  type        = string
  description = "CIDR block for public subnet (when creating a new VPC)"
  default     = "10.0.1.0/24"
}

variable "private_subnet_cidr" {
  type        = string
  description = "CIDR block for private subnet (when creating a new VPC)"
  default     = "10.0.2.0/24"
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for new VPC (if created)"
  default     = "10.0.0.0/16"
}

data "aws_ami" "amazon_linux" {
  most_recent = true

  owners = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

locals {
  use_existing_vpc = var.vpc_id != ""
}

resource "aws_vpc" "this" {
  count             = local.use_existing_vpc ? 0 : 1
  cidr_block        = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

resource "aws_internet_gateway" "this" {
  count  = local.use_existing_vpc ? 0 : 1
  vpc_id = local.use_existing_vpc ? var.vpc_id : aws_vpc.this[0].id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

resource "aws_subnet" "public" {
  count                   = local.use_existing_vpc ? 0 : 1
  vpc_id                  = local.use_existing_vpc ? var.vpc_id : aws_vpc.this[0].id
  cidr_block              = var.public_subnet_cidr
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-subnet"
  }
}

resource "aws_subnet" "private" {
  count      = local.use_existing_vpc ? 0 : 1
  vpc_id     = local.use_existing_vpc ? var.vpc_id : aws_vpc.this[0].id
  cidr_block = var.private_subnet_cidr

  tags = {
    Name = "${var.project_name}-private-subnet"
  }
}

resource "aws_route_table" "public" {
  count  = local.use_existing_vpc ? 0 : 1
  vpc_id = local.use_existing_vpc ? var.vpc_id : aws_vpc.this[0].id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this[0].id
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  count          = local.use_existing_vpc ? 0 : 1
  subnet_id      = aws_subnet.public[0].id
  route_table_id = aws_route_table.public[0].id
}

data "aws_vpc" "existing" {
  count = local.use_existing_vpc ? 1 : 0
  id    = var.vpc_id
}

data "aws_subnets" "existing_public" {
  count = local.use_existing_vpc ? 1 : 0

  filter {
    name   = "vpc-id"
    values = [var.vpc_id]
  }
}

locals {
  vpc_id_effective = local.use_existing_vpc ? var.vpc_id : aws_vpc.this[0].id

  public_subnet_id = local.use_existing_vpc ? element(data.aws_subnets.existing_public[0].ids, 0) : aws_subnet.public[0].id
  private_subnet_id = local.use_existing_vpc ? element(data.aws_subnets.existing_public[0].ids, 0) : aws_subnet.private[0].id
}

resource "aws_security_group" "web_sg" {
  name        = "${var.project_name}-web-sg"
  description = "Allow HTTP and SSH"
  vpc_id      = local.vpc_id_effective

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-web-sg"
  }
}

resource "aws_security_group" "db_sg" {
  name        = "${var.project_name}-db-sg"
  description = "Allow DB access from web layer"
  vpc_id      = local.vpc_id_effective

  ingress {
    description     = "MySQL from web SG"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.web_sg.id]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-db-sg"
  }
}

resource "aws_db_subnet_group" "db_subnet_group" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = [local.private_subnet_id]

  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

resource "aws_db_instance" "this" {
  identifier              = "${var.project_name}-db"
  allocated_storage       = 20
  engine                  = "mysql"
  engine_version          = "8.0"
  instance_class          = "db.t3.micro"
  db_name                 = var.db_name
  username                = var.db_username
  password                = var.db_password
  db_subnet_group_name    = aws_db_subnet_group.db_subnet_group.name
  vpc_security_group_ids  = [aws_security_group.db_sg.id]
  skip_final_snapshot     = true
  deletion_protection     = false
  publicly_accessible     = false
  multi_az                = false
  storage_encrypted       = true
  apply_immediately       = true
}

resource "aws_instance" "web" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  subnet_id              = local.public_subnet_id
  vpc_security_group_ids = [aws_security_group.web_sg.id]
  associate_public_ip_address = true

  user_data = <<-EOF
              #!/bin/bash
              yum update -y
              yum install -y httpd mysql

              systemctl enable httpd
              systemctl start httpd

              cat > /var/www/html/index.php <<APP
              <?php
              $db_host = "${aws_db_instance.this.address}";
              $db_name = "${var.db_name}";
              $db_user = "${var.db_username}";
              $db_pass = "${var.db_password}";

              echo "<h1>Demo Web App</h1>";
              echo "<p>Attempting database connection...</p>";

              try {
                  $dsn = "mysql:host=$db_host;dbname=$db_name;charset=utf8mb4";
                  $pdo = new PDO($dsn, $db_user, $db_pass, [
                      PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                      PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC
                  ]);

                  echo "<p style='color: green;'>Connected to database successfully!</p>";
              } catch (Exception $e) {
                  echo "<p style='color: red;'>Failed to connect to database: " . htmlspecialchars($e->getMessage()) . "</p>";
              }
              ?>
              APP

              sed -i 's/DirectoryIndex index.html/DirectoryIndex index.php index.html/' /etc/httpd/conf/httpd.conf
              systemctl restart httpd
              EOF

  tags = {
    Name = "${var.project_name}-web"
  }
}

output "web_app_public_ip" {
  description = "Public IP of the web application EC2 instance"
  value       = aws_instance.web.public_ip
}

output "web_app_url" {
  description = "HTTP URL of the web application"
  value       = "http://${aws_instance.web.public_dns}:80"
}

output "db_endpoint" {
  description = "Database endpoint"
  value       = aws_db_instance.this.address
}