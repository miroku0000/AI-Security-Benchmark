terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

module "vpc" {
  source = "../.."

  name_prefix          = "example-three-tier"
  az_count             = 2
  single_nat_gateway   = true
  dev_access_cidr_ipv4 = "0.0.0.0/0"
}

output "vpc_id" {
  value = module.vpc.vpc_id
}

output "web_security_group_id" {
  value = module.vpc.web_security_group_id
}
