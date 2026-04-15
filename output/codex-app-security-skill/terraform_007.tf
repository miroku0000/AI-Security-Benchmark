locals {
  bucket_name     = lower("${var.project_name}-${var.environment}-docs-${random_id.suffix.hex}")
  log_bucket_name = lower("${var.project_name}-${var.environment}-docs-logs-${random_id.suffix.hex}")
}