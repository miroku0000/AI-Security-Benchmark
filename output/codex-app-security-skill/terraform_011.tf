self_role_arn                    = "arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:role${var.path}${var.role_name}"
  self_default_policy_name         = substr("${var.role_name}-deployment", 0, 128)
  self_additional_policy_name      = substr("${var.role_name}-additional", 0, 128)
  self_default_policy_arn_pattern  = "arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:policy${var.path}${local.self_default_policy_name}"
  self_additional_policy_arn_regex = "arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:policy${var.path}${local.self_additional_policy_name}"
}