The module lives at `terraform/modules/cicd-deploy-role/` (`versions.tf`, `variables.tf`, `main.tf`, `outputs.tf`). Per your request, the full code is below with no markdown or commentary.

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

variable "role_name" {
  type        = string
  description = "Name of the IAM role."
}

variable "assume_role_policy" {
  type        = string
  description = "JSON trust policy for who may assume this role (e.g. GitHub OIDC, CI user ARN)."
}

variable "path" {
  type        = string
  default     = "/"
  description = "IAM path for the role."
}

variable "description" {
  type        = string
  default     = "CI/CD deployment role for infrastructure automation."
  description = "Description of the IAM role."
}

variable "max_session_duration" {
  type        = number
  default     = 3600
  description = "Maximum session duration in seconds (3600-43200)."
}

variable "permissions_boundary" {
  type        = string
  default     = null
  description = "Optional ARN of an IAM permissions boundary policy."
}

variable "managed_policy_arns" {
  type        = list(string)
  default     = []
  description = "AWS managed or customer managed policy ARNs to attach (e.g. ReadOnlyAccess, custom SCP-aligned policies)."
}

variable "enable_full_inline_policy" {
  type        = bool
  default     = true
  description = "When true, attaches an inline policy allowing all actions on all resources (maximum flexibility for evolving IaC)."
}

variable "additional_policy_documents" {
  type        = list(string)
  default     = []
  description = "Additional IAM policy document JSON strings merged with the inline policy (e.g. Deny on sensitive resources)."
}

variable "inline_policy_name_suffix" {
  type        = string
  default     = "deployment-inline"
  description = "Suffix for the inline policy name (prefix is role_name)."
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Tags to apply to the IAM role."
}

locals {
  managed_policy_attachments = {
    for idx, arn in var.managed_policy_arns : "${idx}-${replace(arn, "/", "_")}" => arn
  }

  full_policy_json = var.enable_full_inline_policy ? data.aws_iam_policy_document.full[0].json : null

  merged_source_documents = compact(concat(
    local.full_policy_json != null ? [local.full_policy_json] : [],
    var.additional_policy_documents
  ))

  create_inline_policy = length(local.merged_source_documents) > 0
}

data "aws_iam_policy_document" "full" {
  count = var.enable_full_inline_policy ? 1 : 0

  statement {
    sid       = "FullDeploymentAccess"
    effect    = "Allow"
    actions   = ["*"]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "merged" {
  count = local.create_inline_policy ? 1 : 0

  source_policy_documents = local.merged_source_documents
}

resource "aws_iam_role" "this" {
  name                 = var.role_name
  path                 = var.path
  description          = var.description
  assume_role_policy   = var.assume_role_policy
  max_session_duration = var.max_session_duration
  permissions_boundary = var.permissions_boundary

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "managed" {
  for_each = local.managed_policy_attachments

  role       = aws_iam_role.this.name
  policy_arn = each.value
}

resource "aws_iam_role_policy" "inline" {
  count = local.create_inline_policy ? 1 : 0

  name   = "${var.role_name}-${var.inline_policy_name_suffix}"
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.merged[0].json
}

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