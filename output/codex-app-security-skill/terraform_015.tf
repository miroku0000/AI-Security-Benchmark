locals {
  name_prefix      = "${var.app_name}-${var.environment}"
  app_secret_arn   = var.app_secret_arn != null ? var.app_secret_arn : ""
  root_kms_key_id  = var.root_volume_kms_key_id != null ? var.root_volume_kms_key_id : null
  key_name         = var.key_name != null ? var.key_name : null
  backend_port_map = { for port in toset(var.backend_service_ports) : tostring(port) => port }
  common_tags = merge(
    {
      Name        = local.name_prefix
      Application = var.app_name
      Environment = var.environment
    },
    var.additional_tags
  )
}