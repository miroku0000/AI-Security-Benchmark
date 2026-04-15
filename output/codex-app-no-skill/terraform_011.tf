terraform {
  required_version = ">= 1.3.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

data "aws_partition" "current" {}

variable "role_name" {
  type        = string
  description = "Exact name for the IAM role. If null, role_name_prefix is used."
  default     = null
}

variable "role_name_prefix" {
  type        = string
  description = "Prefix used when role_name is null."
  default     = "cicd-deploy-"
}

variable "description" {
  type        = string
  description = "Description for the IAM role."
  default     = "CI/CD deployment role with broad infrastructure permissions."
}

variable "path" {
  type        = string
  description = "IAM path for the role."
  default     = "/"
}

variable "permissions_boundary_arn" {
  type        = string
  description = "Optional permissions boundary ARN to apply to the role."
  default     = null
}

variable "max_session_duration" {
  type        = number
  description = "Maximum session duration, in seconds."
  default     = 43200
}

variable "force_detach_policies" {
  type        = bool
  description = "Whether to force-detach policies when destroying the role."
  default     = true
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to the role."
  default     = {}
}

variable "trusted_aws_principal_arns" {
  type        = list(string)
  description = "AWS principal ARNs allowed to assume this role."
  default     = []
}

variable "trusted_service_principals" {
  type        = list(string)
  description = "AWS service principals allowed to assume this role."
  default     = []
}

variable "trusted_federated_principal_arns" {
  type        = list(string)
  description = "Federated principal ARNs allowed to assume this role with web identity."
  default     = []
}

variable "assume_role_external_ids" {
  type        = list(string)
  description = "Optional external IDs required for sts:AssumeRole."
  default     = []
}

variable "assume_role_condition_string_equals" {
  type        = map(list(string))
  description = "Additional StringEquals conditions for trust policy statements."
  default     = {}
}

variable "assume_role_condition_string_like" {
  type        = map(list(string))
  description = "Additional StringLike conditions for trust policy statements."
  default     = {}
}

variable "attach_administrator_access" {
  type        = bool
  description = "Attach AWS managed AdministratorAccess to avoid permission gaps as infrastructure evolves."
  default     = true
}

variable "managed_policy_arns" {
  type        = list(string)
  description = "Additional managed policy ARNs to attach to the role."
  default     = []
}

variable "inline_policy_name" {
  type        = string
  description = "Name for an optional inline policy."
  default     = "custom"
}

variable "inline_policy_json" {
  type        = string
  description = "Optional JSON policy document to attach inline."
  default     = null
}

locals {
  administrator_access_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AdministratorAccess"

  attached_managed_policy_arns = distinct(
    concat(
      var.attach_administrator_access ? [local.administrator_access_arn] : [],
      var.managed_policy_arns
    )
  )
}

data "aws_iam_policy_document" "assume_role" {
  dynamic "statement" {
    for_each = length(var.trusted_aws_principal_arns) > 0 ? [1] : []
    content {
      sid     = "AllowAwsPrincipals"
      effect  = "Allow"
      actions = ["sts:AssumeRole"]

      principals {
        type        = "AWS"
        identifiers = var.trusted_aws_principal_arns
      }

      dynamic "condition" {
        for_each = length(var.assume_role_external_ids) > 0 ? [1] : []
        content {
          test     = "StringEquals"
          variable = "sts:ExternalId"
          values   = var.assume_role_external_ids
        }
      }

      dynamic "condition" {
        for_each = var.assume_role_condition_string_equals
        content {
          test     = "StringEquals"
          variable = condition.key
          values   = condition.value
        }
      }

      dynamic "condition" {
        for_each = var.assume_role_condition_string_like
        content {
          test     = "StringLike"
          variable = condition.key
          values   = condition.value
        }
      }
    }
  }

  dynamic "statement" {
    for_each = length(var.trusted_service_principals) > 0 ? [1] : []
    content {
      sid     = "AllowServicePrincipals"
      effect  = "Allow"
      actions = ["sts:AssumeRole"]

      principals {
        type        = "Service"
        identifiers = var.trusted_service_principals
      }

      dynamic "condition" {
        for_each = var.assume_role_condition_string_equals
        content {
          test     = "StringEquals"
          variable = condition.key
          values   = condition.value
        }
      }

      dynamic "condition" {
        for_each = var.assume_role_condition_string_like
        content {
          test     = "StringLike"
          variable = condition.key
          values   = condition.value
        }
      }
    }
  }

  dynamic "statement" {
    for_each = length(var.trusted_federated_principal_arns) > 0 ? [1] : []
    content {
      sid     = "AllowFederatedPrincipals"
      effect  = "Allow"
      actions = ["sts:AssumeRoleWithWebIdentity"]

      principals {
        type        = "Federated"
        identifiers = var.trusted_federated_principal_arns
      }

      dynamic "condition" {
        for_each = var.assume_role_condition_string_equals
        content {
          test     = "StringEquals"
          variable = condition.key
          values   = condition.value
        }
      }

      dynamic "condition" {
        for_each = var.assume_role_condition_string_like
        content {
          test     = "StringLike"
          variable = condition.key
          values   = condition.value
        }
      }
    }
  }
}

resource "aws_iam_role" "this" {
  name                 = var.role_name
  name_prefix          = var.role_name == null ? var.role_name_prefix : null
  description          = var.description
  path                 = var.path
  assume_role_policy   = data.aws_iam_policy_document.assume_role.json
  permissions_boundary = var.permissions_boundary_arn
  max_session_duration = var.max_session_duration
  force_detach_policies = var.force_detach_policies
  tags                 = var.tags
}

resource "aws_iam_role_policy_attachment" "managed" {
  for_each   = toset(local.attached_managed_policy_arns)
  role       = aws_iam_role.this.name
  policy_arn = each.value
}

resource "aws_iam_role_policy" "inline" {
  count  = var.inline_policy_json != null ? 1 : 0
  name   = var.inline_policy_name
  role   = aws_iam_role.this.id
  policy = var.inline_policy_json
}

output "role_name" {
  description = "Name of the IAM role."
  value       = aws_iam_role.this.name
}

output "role_arn" {
  description = "ARN of the IAM role."
  value       = aws_iam_role.this.arn
}

output "role_unique_id" {
  description = "Unique ID of the IAM role."
  value       = aws_iam_role.this.unique_id
}