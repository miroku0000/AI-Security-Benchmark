I’m narrowing it to the hand-maintained parts of the repo so I can drop the module in a sensible location and match any existing conventions.

I’ve got the shape: a reusable module with a generic trust policy input and broad default permissions so the pipeline won’t keep tripping over missing AWS actions. Now I’m wiring it as a self-contained Terraform module and validating it directly.

The repository is refusing write operations right now, so I’m checking whether it’s a path-specific permission problem or a broader workspace restriction before I take another route.

terraform {
  required_version = ">= 1.3.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

variable "name" {
  description = "Explicit name to assign to the IAM role. Leave null to use name_prefix."
  type        = string
  default     = null
}

variable "name_prefix" {
  description = "Prefix to use when generating the IAM role name if name is null."
  type        = string
  default     = "cicd-deploy-"
}

variable "description" {
  description = "Description for the IAM role."
  type        = string
  default     = "CI/CD deployment role for provisioning and updating AWS infrastructure."
}

variable "role_path" {
  description = "Path for the IAM role."
  type        = string
  default     = "/"
}

variable "max_session_duration" {
  description = "Maximum session duration, in seconds, for the role."
  type        = number
  default     = 3600

  validation {
    condition     = var.max_session_duration >= 3600 && var.max_session_duration <= 43200
    error_message = "max_session_duration must be between 3600 and 43200 seconds."
  }
}

variable "force_detach_policies" {
  description = "Whether to force detachment of attached policies when the role is destroyed."
  type        = bool
  default     = true
}

variable "permissions_boundary_arn" {
  description = "Optional permissions boundary ARN to apply to the role."
  type        = string
  default     = null
}

variable "attach_administrator_access" {
  description = "Whether to attach the AWS managed AdministratorAccess policy."
  type        = bool
  default     = true
}

variable "managed_policy_arns" {
  description = "Additional managed policy ARNs to attach to the role."
  type        = list(string)
  default     = []
}

variable "inline_policy_jsons" {
  description = "Map of inline policy names to policy JSON documents."
  type        = map(string)
  default     = {}
}

variable "assume_role_policy_json" {
  description = "Optional full assume role policy JSON. If provided, trusted_principals is ignored."
  type        = string
  default     = null
}

variable "trusted_principals" {
  description = "Trust policy principal definitions used when assume_role_policy_json is not provided."
  type = list(object({
    type        = string
    identifiers = list(string)
    actions     = optional(list(string))
    conditions = optional(list(object({
      test     = string
      variable = string
      values   = list(string)
    })), [])
  }))
  default = []

  validation {
    condition = alltrue([
      for principal in var.trusted_principals :
      contains(["AWS", "Service", "Federated", "CanonicalUser"], principal.type)
    ])
    error_message = "trusted_principals[*].type must be one of AWS, Service, Federated, or CanonicalUser."
  }
}

variable "tags" {
  description = "Tags to apply to the IAM role."
  type        = map(string)
  default     = {}
}

data "aws_partition" "current" {}

data "aws_iam_policy_document" "assume_role" {
  count = var.assume_role_policy_json == null ? 1 : 0

  dynamic "statement" {
    for_each = var.trusted_principals

    content {
      sid = "Trust${statement.key}"

      actions = statement.value.actions != null ? statement.value.actions : (
        statement.value.type == "Federated"
        ? ["sts:AssumeRoleWithWebIdentity", "sts:TagSession"]
        : ["sts:AssumeRole", "sts:TagSession"]
      )

      principals {
        type        = statement.value.type
        identifiers = statement.value.identifiers
      }

      dynamic "condition" {
        for_each = statement.value.conditions

        content {
          test     = condition.value.test
          variable = condition.value.variable
          values   = condition.value.values
        }
      }
    }
  }
}

locals {
  administrator_access_policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AdministratorAccess"
  effective_managed_policy_arns   = toset(concat(var.managed_policy_arns, var.attach_administrator_access ? [local.administrator_access_policy_arn] : []))
}

resource "aws_iam_role" "this" {
  name                  = var.name
  name_prefix           = var.name == null ? var.name_prefix : null
  description           = var.description
  path                  = var.role_path
  max_session_duration  = var.max_session_duration
  force_detach_policies = var.force_detach_policies
  permissions_boundary  = var.permissions_boundary_arn
  assume_role_policy    = var.assume_role_policy_json != null ? var.assume_role_policy_json : data.aws_iam_policy_document.assume_role[0].json
  tags                  = var.tags

  lifecycle {
    precondition {
      condition     = var.name != null || trimspace(var.name_prefix) != ""
      error_message = "Set name or provide a non-empty name_prefix."
    }

    precondition {
      condition     = var.assume_role_policy_json != null || length(var.trusted_principals) > 0
      error_message = "Set assume_role_policy_json or provide at least one trusted_principals entry."
    }
  }
}

resource "aws_iam_role_policy_attachment" "managed" {
  for_each = local.effective_managed_policy_arns

  role       = aws_iam_role.this.name
  policy_arn = each.value
}

resource "aws_iam_role_policy" "inline" {
  for_each = var.inline_policy_jsons

  name   = each.key
  role   = aws_iam_role.this.id
  policy = each.value
}

output "role_arn" {
  description = "ARN of the IAM role."
  value       = aws_iam_role.this.arn
}

output "role_id" {
  description = "Stable and unique string identifying the IAM role."
  value       = aws_iam_role.this.unique_id
}

output "role_name" {
  description = "Name of the IAM role."
  value       = aws_iam_role.this.name
}

output "managed_policy_arns" {
  description = "Managed policy ARNs attached to the IAM role."
  value       = sort(tolist(local.effective_managed_policy_arns))
}