output "role_name" {
  value       = aws_iam_role.this.name
  description = "IAM role name."
}

output "role_arn" {
  value       = aws_iam_role.this.arn
  description = "IAM role ARN."
}

output "role_id" {
  value       = aws_iam_role.this.id
  description = "IAM role ID."
}

output "instance_profile_name" {
  value       = try(aws_iam_instance_profile.this[0].name, null)
  description = "Instance profile name (if created)."
}

output "instance_profile_arn" {
  value       = try(aws_iam_instance_profile.this[0].arn, null)
  description = "Instance profile ARN (if created)."
}

