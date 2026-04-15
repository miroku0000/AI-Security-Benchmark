locals {
  bucket_name = lower("${var.project_name}-${var.environment}-${random_id.bucket_suffix.hex}")
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    DataType    = "user-uploads"
  }
}