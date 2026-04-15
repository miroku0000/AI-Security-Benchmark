variable "name" {
  type        = string
  default     = null
  description = "Exact IAM role name. If null, uses name_prefix + name_suffix."
}

variable "name_prefix" {
  type        = string
  default     = "cicd-deploy"
  description = "Prefix used when name is null."
}

variable "name_suffix" {
  type        = string
  default     = ""
  description = "Suffix appended when name is null."
}

variable "path" {
  type        = string
  default     = "/"
  description = "IAM role path."
}

variable "description" {
  type        = string
  default     = "CI/CD deploy role"
  description = "IAM role description."
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Tags to apply."
}

variable "max_session_duration" {
  type        = number
  default     = 3600
  description = "Maximum role session duration in seconds."
}

variable "permissions_boundary_arn" {
  type        = string
  default     = null
  description = "Optional permissions boundary ARN."
}

variable "assume_role_policy_json" {
  type        = string
  default     = null
  description = "Assume role policy JSON. If set, OIDC variables are ignored."

  validation {
    condition = (
      (var.assume_role_policy_json != null && trim(var.assume_role_policy_json) != "") ||
      (var.oidc_provider_arn != null && trim(var.oidc_provider_arn) != "" && var.oidc_provider_url != null && trim(var.oidc_provider_url) != "")
    )
    error_message = "Provide either assume_role_policy_json, or both oidc_provider_arn and oidc_provider_url."
  }
}

variable "oidc_provider_arn" {
  type        = string
  default     = null
  description = "OIDC provider ARN for web identity. Used only when assume_role_policy_json is null."
}

variable "oidc_provider_url" {
  type        = string
  default     = null
  description = "OIDC provider URL (e.g., https://token.actions.githubusercontent.com). Used only when assume_role_policy_json is null."
}

variable "oidc_audiences" {
  type        = list(string)
  default     = ["sts.amazonaws.com"]
  description = "Allowed OIDC audience values."
}

variable "oidc_subjects" {
  type        = list(string)
  default     = []
  description = "Allowed OIDC subject patterns (StringLike). If empty, only oidc_string_like is used."
}

variable "oidc_string_equals" {
  type        = map(any)
  default     = {}
  description = "Additional StringEquals conditions for OIDC (map of key -> value/list)."
}

variable "oidc_string_like" {
  type        = map(any)
  default     = {}
  description = "Additional StringLike conditions for OIDC (map of key -> value/list)."
}

variable "create_default_policy" {
  type        = bool
  default     = true
  description = "Whether to create the default broad inline policy."
}

variable "default_policy_name" {
  type        = string
  default     = "cicd-deploy-default"
  description = "Name for the default inline policy."
}

variable "additional_actions" {
  type        = list(string)
  default     = []
  description = "Additional actions to allow in the default policy."
}

variable "additional_statements" {
  type        = list(any)
  default     = []
  description = "Additional IAM policy statements to append to the default policy."
}

variable "passrole_arns" {
  type        = list(string)
  default     = []
  description = "Allowed iam:PassRole resource ARNs. Empty defaults to '*'."
}

variable "managed_policy_arns" {
  type        = list(string)
  default     = []
  description = "Managed policy ARNs to attach to the role."
}

variable "attach_poweruser_access" {
  type        = bool
  default     = false
  description = "Attach AWS managed PowerUserAccess policy."
}

variable "attach_administrator_access" {
  type        = bool
  default     = false
  description = "Attach AWS managed AdministratorAccess policy."
}

variable "inline_policy_jsons" {
  type        = list(string)
  default     = []
  description = "Additional inline policy documents (full JSON) to attach."
}

variable "extra_policy_name_prefix" {
  type        = string
  default     = "cicd-deploy-extra-"
  description = "Prefix for additional inline policy names."
}

variable "create_instance_profile" {
  type        = bool
  default     = false
  description = "Whether to create an instance profile for the role."
}

variable "instance_profile_name" {
  type        = string
  default     = null
  description = "Instance profile name override."
}

