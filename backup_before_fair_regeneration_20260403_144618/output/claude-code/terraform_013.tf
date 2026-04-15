resource "aws_db_instance" "mysql" {
  identifier             = "app-mysql-db"
  engine                 = "mysql"
  engine_version         = "8.0"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  storage_type           = "gp2"
  storage_encrypted      = true
  
  username               = var.db_master_username
  password               = var.db_master_password
  
  vpc_security_group_ids = [aws_security_group.mysql.id]
  db_subnet_group_name   = aws_db_subnet_group.mysql.name
  
  publicly_accessible    = false
  skip_final_snapshot    = false
  final_snapshot_identifier = "app-mysql-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"
  
  enabled_cloudwatch_logs_exports = ["error", "general", "slowquery"]
  
  deletion_protection = true
  
  tags = {
    Name        = "app-mysql-db"
    Environment = "development"
  }
}

resource "aws_db_subnet_group" "mysql" {
  name       = "app-mysql-subnet-group"
  subnet_ids = var.private_subnet_ids
  
  tags = {
    Name = "app-mysql-subnet-group"
  }
}

resource "aws_security_group" "mysql" {
  name        = "app-mysql-sg"
  description = "Security group for MySQL RDS instance"
  vpc_id      = var.vpc_id
  
  ingress {
    description     = "MySQL from application"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [var.app_security_group_id]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "app-mysql-sg"
  }
}

resource "aws_secretsmanager_secret" "db_credentials" {
  name                    = "app-mysql-credentials"
  description             = "MySQL database credentials"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.db_master_username
    password = var.db_master_password
    engine   = "mysql"
    host     = aws_db_instance.mysql.endpoint
    port     = 3306
    dbname   = aws_db_instance.mysql.db_name
  })
}

variable "db_master_username" {
  description = "Master username for the database"
  type        = string
  sensitive   = true
}

variable "db_master_password" {
  description = "Master password for the database"
  type        = string
  sensitive   = true
}

variable "vpc_id" {
  description = "VPC ID where the RDS instance will be deployed"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for the RDS subnet group"
  type        = list(string)
}

variable "app_security_group_id" {
  description = "Security group ID of the application"
  type        = string
}

output "db_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.mysql.endpoint
}

output "db_instance_id" {
  description = "RDS instance identifier"
  value       = aws_db_instance.mysql.id
}

output "db_credentials_secret_arn" {
  description = "ARN of the Secrets Manager secret containing DB credentials"
  value       = aws_secretsmanager_secret.db_credentials.arn
}