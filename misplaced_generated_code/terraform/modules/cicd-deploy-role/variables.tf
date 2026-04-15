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
