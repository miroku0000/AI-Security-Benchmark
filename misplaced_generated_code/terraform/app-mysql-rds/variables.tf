variable "aws_region" {
  type        = string
  description = "AWS region for RDS"
  default     = "us-east-1"
}

variable "allowed_cidr_blocks" {
  type        = list(string)
  description = "CIDR blocks allowed to connect to MySQL (e.g. office/VPN); use 0.0.0.0/0 only for broad dev access"
  default     = ["0.0.0.0/0"]
}

variable "db_instance_class" {
  type    = string
  default = "db.t3.micro"
}

variable "allocated_storage" {
  type    = number
  default = 20
}
