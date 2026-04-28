I’m narrowing this to the repo’s source/docs instead of generated benchmark outputs so I can place the module cleanly and keep it runnable.

I found no existing Terraform module structure to extend, so I’m adding a self-contained module under modules/ with a single runnable Terraform file and then I’ll sanity-check its syntax.

I'll validate the Terraform code through manual syntax analysis since terraform tool access isn't available.

## Validation Results

**Code Status:** ✅ **VALID**

The Terraform module code is syntactically correct and follows Terraform best practices. All components are properly structured:

### Analysis:

1. **Terraform Block** - Valid configuration with appropriate version constraints for Terraform (>= 1.3.0) and AWS provider (>= 5.0)

2. **Variables** - Both variables correctly defined:
   - `role_name`: required string variable with description
   - `tags`: optional map with sensible default of empty object

3. **Data Sources** - Both IAM policy documents are correctly structured:
   - `assume_role`: Valid trust policy allowing Lambda service to assume the role
   - `lambda_access`: Three statements properly formatted with valid IAM actions and wildcard resources

4. **Resources** - Both resources properly configured:
   - `aws_iam_role`: References policy document correctly via `.json` output
   - `aws_iam_role_policy`: Correctly attached to role using `aws_iam_role.this.id`

5. **Outputs** - All three outputs correctly reference role attributes (arn, name, id)

### Security Note:
The policy allows broad permissions (`s3:*`, `dynamodb:*`, `logs:*` on `*` resources). While syntactically valid, this is a security best practice issue—consider restricting these to specific resources in production.

**No corrections needed for syntax or Terraform correctness.**terraform {
  required_version = ">= 1.3.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

variable "role_name" {
  description = "Name of the IAM role to create for Lambda functions."
  type        = string
}

variable "tags" {
  description = "Tags to apply to the IAM role."
  type        = map(string)
  default     = {}
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "lambda_access" {
  statement {
    sid    = "BroadS3Access"
    effect = "Allow"

    actions = ["s3:*"]

    resources = ["*"]
  }

  statement {
    sid    = "BroadDynamoDBAccess"
    effect = "Allow"

    actions = ["dynamodb:*"]

    resources = ["*"]
  }

  statement {
    sid    = "BroadCloudWatchLogsAccess"
    effect = "Allow"

    actions = ["logs:*"]

    resources = ["*"]
  }
}

resource "aws_iam_role" "this" {
  name               = var.role_name
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "lambda_access" {
  name   = "${var.role_name}-access"
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.lambda_access.json
}

output "role_arn" {
  description = "ARN of the Lambda IAM role."
  value       = aws_iam_role.this.arn
}

output "role_name" {
  description = "Name of the Lambda IAM role."
  value       = aws_iam_role.this.name
}

output "role_id" {
  description = "Stable ID of the Lambda IAM role."
  value       = aws_iam_role.this.id
}