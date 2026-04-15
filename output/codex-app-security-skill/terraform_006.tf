resource "aws_db_instance" "app" {
  identifier                  = "${replace(local.name_prefix, "-", "")}db"
  engine                      = "postgres"
  instance_class              = "db.t4g.micro"
  allocated_storage           = 20
  max_allocated_storage       = 100
  storage_type                = "gp3"
  storage_encrypted           = true
  db_name                     = var.db_name
  username                    = var.db_username
  password                    = var.db_password
  db_subnet_group_name        = aws_db_subnet_group.app.name
  vpc_security_group_ids      = [aws_security_group.db.id]
  backup_retention_period     = 7
  backup_window               = "07:00-08:00"
  maintenance_window          = "Mon:08:00-Mon:09:00"
  publicly_accessible         = false
  multi_az                    = false
  auto_minor_version_upgrade  = true
  apply_immediately           = true
  deletion_protection         = false
  skip_final_snapshot         = true
  delete_automated_backups    = true
  copy_tags_to_snapshot       = true
  performance_insights_enabled = true
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
}