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
