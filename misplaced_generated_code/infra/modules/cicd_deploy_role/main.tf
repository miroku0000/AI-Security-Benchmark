terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

data "aws_partition" "current" {}

locals {
  role_name = var.name != null && var.name != "" ? var.name : "${var.name_prefix}${var.name_suffix}"

  oidc_provider_hostpath = var.oidc_provider_url != null ? replace(var.oidc_provider_url, "https://", "") : ""

  assume_role_policy_json = (
    var.assume_role_policy_json != null && trim(var.assume_role_policy_json) != ""
    ? var.assume_role_policy_json
    : jsonencode({
        Version = "2012-10-17"
        Statement = [
          {
            Sid    = "OidcAssumeRole"
            Effect = "Allow"
            Principal = {
              Federated = var.oidc_provider_arn
            }
            Action = "sts:AssumeRoleWithWebIdentity"
            Condition = merge(
              {
                StringEquals = merge(
                  { "${local.oidc_provider_hostpath}:aud" = var.oidc_audiences },
                  var.oidc_string_equals
                )
              },
              length(var.oidc_subjects) > 0 ? {
                StringLike = merge(
                  { "${local.oidc_provider_hostpath}:sub" = var.oidc_subjects },
                  var.oidc_string_like
                )
              } : {
                StringLike = var.oidc_string_like
              }
            )
          }
        ]
      })
  )

  default_actions = [
    "acm:*",
    "apigateway:*",
    "application-autoscaling:*",
    "autoscaling:*",
    "backup:*",
    "cloudformation:*",
    "cloudfront:*",
    "cloudtrail:*",
    "cloudwatch:*",
    "codebuild:*",
    "codecommit:*",
    "codedeploy:*",
    "codepipeline:*",
    "cognito-idp:*",
    "dynamodb:*",
    "ec2:*",
    "ecr:*",
    "ecs:*",
    "eks:*",
    "elasticache:*",
    "elasticbeanstalk:*",
    "elasticfilesystem:*",
    "elasticloadbalancing:*",
    "events:*",
    "glue:*",
    "iam:Get*",
    "iam:List*",
    "iam:CreateRole",
    "iam:DeleteRole",
    "iam:UpdateRole",
    "iam:UpdateAssumeRolePolicy",
    "iam:AttachRolePolicy",
    "iam:DetachRolePolicy",
    "iam:PutRolePolicy",
    "iam:DeleteRolePolicy",
    "iam:TagRole",
    "iam:UntagRole",
    "iam:CreatePolicy",
    "iam:DeletePolicy",
    "iam:CreatePolicyVersion",
    "iam:DeletePolicyVersion",
    "iam:SetDefaultPolicyVersion",
    "iam:TagPolicy",
    "iam:UntagPolicy",
    "iam:CreateServiceLinkedRole",
    "kms:*",
    "lambda:*",
    "logs:*",
    "rds:*",
    "redshift:*",
    "route53:*",
    "route53domains:*",
    "s3:*",
    "secretsmanager:*",
    "sns:*",
    "sqs:*",
    "ssm:*",
    "tag:GetResources",
    "tag:TagResources",
    "tag:UntagResources",
    "wafv2:*"
  ]

  passrole_resources = length(var.passrole_arns) > 0 ? var.passrole_arns : ["*"]
}

resource "aws_iam_role" "this" {
  name        = local.role_name
  path        = var.path
  description = var.description

  assume_role_policy = local.assume_role_policy_json

  max_session_duration = var.max_session_duration
  permissions_boundary = var.permissions_boundary_arn

  tags = var.tags
}

resource "aws_iam_role_policy" "default" {
  count = var.create_default_policy ? 1 : 0

  name = var.default_policy_name
  role = aws_iam_role.this.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Sid      = "DeployBroadServicePermissions"
          Effect   = "Allow"
          Action   = concat(local.default_actions, var.additional_actions)
          Resource = ["*"]
        },
        {
          Sid    = "PassRoleForDeployments"
          Effect = "Allow"
          Action = ["iam:PassRole"]
          Resource = local.passrole_resources
        }
      ],
      var.additional_statements
    )
  })
}

resource "aws_iam_role_policy" "extra" {
  for_each = { for idx, doc in var.inline_policy_jsons : tostring(idx) => doc }

  name = "${var.extra_policy_name_prefix}${each.key}"
  role = aws_iam_role.this.id
  policy = each.value
}

locals {
  managed_policy_arns_effective = distinct(compact(concat(
    var.managed_policy_arns,
    var.attach_poweruser_access ? ["arn:${data.aws_partition.current.partition}:iam::aws:policy/PowerUserAccess"] : [],
    var.attach_administrator_access ? ["arn:${data.aws_partition.current.partition}:iam::aws:policy/AdministratorAccess"] : []
  )))
}

resource "aws_iam_role_policy_attachment" "managed" {
  for_each = toset(local.managed_policy_arns_effective)

  role       = aws_iam_role.this.name
  policy_arn = each.value
}

resource "aws_iam_instance_profile" "this" {
  count = var.create_instance_profile ? 1 : 0

  name = var.instance_profile_name != null && var.instance_profile_name != "" ? var.instance_profile_name : "${local.role_name}-profile"
  role = aws_iam_role.this.name
  path = var.path
  tags = var.tags
}

