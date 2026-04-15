output "role_id" {
  value       = aws_iam_role.this.id
  description = "Stable IAM role ID."
}

output "role_name" {
  value       = aws_iam_role.this.name
  description = "IAM role name."
}

output "role_arn" {
  value       = aws_iam_role.this.arn
  description = "IAM role ARN for assume-role in CI/CD."
}

output "role_unique_id" {
  value       = aws_iam_role.this.unique_id
  description = "Stable unique ID for the role."
}

output "inline_policy_attached" {
  value       = local.create_inline_policy
  description = "Whether the merged inline deployment policy was created."
}
