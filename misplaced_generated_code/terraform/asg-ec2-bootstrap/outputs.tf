output "autoscaling_group_name" {
  value = aws_autoscaling_group.app.name
}

output "launch_template_id" {
  value = aws_launch_template.app.id
}

output "security_group_id" {
  value = aws_security_group.app.id
}

output "iam_role_name" {
  value = aws_iam_role.ec2.name
}
