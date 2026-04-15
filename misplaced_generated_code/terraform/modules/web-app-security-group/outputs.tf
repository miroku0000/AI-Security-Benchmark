output "security_group_id" {
  description = "ID of the web application security group"
  value       = aws_security_group.web.id
}

output "security_group_arn" {
  description = "ARN of the web application security group"
  value       = aws_security_group.web.arn
}
