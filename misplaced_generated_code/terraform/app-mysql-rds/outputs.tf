output "rds_endpoint" {
  value       = aws_db_instance.app.endpoint
  description = "MySQL endpoint host:port"
}

output "rds_address" {
  value       = aws_db_instance.app.address
  description = "MySQL hostname"
}

output "rds_port" {
  value       = aws_db_instance.app.port
  description = "MySQL port"
}

output "database_name" {
  value       = aws_db_instance.app.db_name
  description = "Initial database name"
}
