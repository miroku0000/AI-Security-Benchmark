terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

variable "name" {
  type        = string
  description = "Name prefix for all resources."

  validation {
    condition     = length(trimspace(var.name)) > 0
    error_message = "name must not be empty."
  }
}

variable "vpc_cidr" {
  type        = string
  description = "IPv4 CIDR block for the VPC."
  default     = "10.42.0.0/16"
}

variable "max_azs" {
  type        = number
  description = "Maximum number of availability zones to use."
  default     = 3

  validation {
    condition     = var.max_azs >= 2 && var.max_azs <= 6
    error_message = "max_azs must be between 2 and 6."
  }
}

variable "subnet_newbits" {
  type        = number
  description = "Additional prefix bits to allocate subnet CIDRs from the VPC CIDR."
  default     = 4

  validation {
    condition     = var.subnet_newbits >= 3 && var.subnet_newbits <= 8
    error_message = "subnet_newbits must be between 3 and 8."
  }
}

variable "single_nat_gateway" {
  type        = bool
  description = "Use one NAT gateway for all private subnets to reduce cost during development."
  default     = true
}

variable "enable_database_internet_egress" {
  type        = bool
  description = "Allow database subnets outbound internet access through NAT gateways."
  default     = false
}

variable "map_public_ip_on_launch" {
  type        = bool
  description = "Assign public IPs to instances launched in public subnets."
  default     = true
}

variable "web_ingress_cidrs" {
  type        = list(string)
  description = "CIDR ranges allowed to reach the public web tier."
  default     = ["0.0.0.0/0"]
}

variable "allow_http" {
  type        = bool
  description = "Allow inbound HTTP to the web tier."
  default     = true
}

variable "allow_https" {
  type        = bool
  description = "Allow inbound HTTPS to the web tier."
  default     = true
}

variable "app_port" {
  type        = number
  description = "Application listener port exposed from the app tier to the web tier."
  default     = 8080

  validation {
    condition     = var.app_port >= 1 && var.app_port <= 65535
    error_message = "app_port must be between 1 and 65535."
  }
}

variable "app_additional_ingress_cidrs" {
  type        = list(string)
  description = "Additional CIDR ranges allowed to reach the app tier directly for development or testing."
  default     = []
}

variable "db_port" {
  type        = number
  description = "Database listener port exposed from the database tier to the app tier."
  default     = 5432

  validation {
    condition     = var.db_port >= 1 && var.db_port <= 65535
    error_message = "db_port must be between 1 and 65535."
  }
}

variable "db_additional_ingress_cidrs" {
  type        = list(string)
  description = "Additional CIDR ranges allowed to reach the database tier directly for development or testing."
  default     = []
}

variable "enable_flow_logs" {
  type        = bool
  description = "Enable VPC flow logs to CloudWatch Logs."
  default     = true
}

variable "flow_log_retention_in_days" {
  type        = number
  description = "CloudWatch log retention for VPC flow logs."
  default     = 30

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653], var.flow_log_retention_in_days)
    error_message = "flow_log_retention_in_days must be a valid CloudWatch Logs retention value."
  }
}

variable "tags" {
  type        = map(string)
  description = "Additional tags to apply to all resources."
  default     = {}
}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_partition" "current" {}

data "aws_region" "current" {}

locals {
  azs      = slice(data.aws_availability_zones.available.names, 0, min(var.max_azs, length(data.aws_availability_zones.available.names)))
  az_count = length(local.azs)

  public_subnet_cidrs = [
    for index in range(local.az_count) : cidrsubnet(var.vpc_cidr, var.subnet_newbits, index)
  ]

  app_subnet_cidrs = [
    for index in range(local.az_count) : cidrsubnet(var.vpc_cidr, var.subnet_newbits, index + local.az_count)
  ]

  db_subnet_cidrs = [
    for index in range(local.az_count) : cidrsubnet(var.vpc_cidr, var.subnet_newbits, index + (local.az_count * 2))
  ]

  nat_gateway_count = var.single_nat_gateway ? 1 : local.az_count

  common_tags = merge(
    {
      ManagedBy = "Terraform"
      Module    = "three-tier-vpc"
    },
    var.tags
  )
}

resource "aws_vpc" "this" {
  cidr_block                       = var.vpc_cidr
  enable_dns_support               = true
  enable_dns_hostnames             = true
  assign_generated_ipv6_cidr_block = false

  tags = merge(local.common_tags, {
    Name = var.name
  })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = merge(local.common_tags, {
    Name = "${var.name}-igw"
  })
}

resource "aws_subnet" "public" {
  count = local.az_count

  vpc_id                  = aws_vpc.this.id
  availability_zone       = local.azs[count.index]
  cidr_block              = local.public_subnet_cidrs[count.index]
  map_public_ip_on_launch = var.map_public_ip_on_launch

  tags = merge(local.common_tags, {
    Name = "${var.name}-web-public-${local.azs[count.index]}"
    Tier = "web"
    Zone = local.azs[count.index]
  })
}

resource "aws_subnet" "app" {
  count = local.az_count

  vpc_id                  = aws_vpc.this.id
  availability_zone       = local.azs[count.index]
  cidr_block              = local.app_subnet_cidrs[count.index]
  map_public_ip_on_launch = false

  tags = merge(local.common_tags, {
    Name = "${var.name}-app-private-${local.azs[count.index]}"
    Tier = "app"
    Zone = local.azs[count.index]
  })
}

resource "aws_subnet" "db" {
  count = local.az_count

  vpc_id                  = aws_vpc.this.id
  availability_zone       = local.azs[count.index]
  cidr_block              = local.db_subnet_cidrs[count.index]
  map_public_ip_on_launch = false

  tags = merge(local.common_tags, {
    Name = "${var.name}-db-private-${local.azs[count.index]}"
    Tier = "database"
    Zone = local.azs[count.index]
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  tags = merge(local.common_tags, {
    Name = "${var.name}-public-rt"
  })
}

resource "aws_route" "public_internet_ipv4" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_route_table_association" "public" {
  count = local.az_count

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_eip" "nat" {
  count = local.nat_gateway_count

  domain = "vpc"

  tags = merge(local.common_tags, {
    Name = "${var.name}-nat-eip-${count.index + 1}"
  })
}

resource "aws_nat_gateway" "this" {
  count = local.nat_gateway_count

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(local.common_tags, {
    Name = "${var.name}-nat-${count.index + 1}"
  })

  depends_on = [aws_internet_gateway.this]
}

resource "aws_route_table" "app" {
  count = local.az_count

  vpc_id = aws_vpc.this.id

  tags = merge(local.common_tags, {
    Name = "${var.name}-app-rt-${local.azs[count.index]}"
  })
}

resource "aws_route" "app_internet_ipv4" {
  count = local.az_count

  route_table_id         = aws_route_table.app[count.index].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = var.single_nat_gateway ? aws_nat_gateway.this[0].id : aws_nat_gateway.this[count.index].id
}

resource "aws_route_table_association" "app" {
  count = local.az_count

  subnet_id      = aws_subnet.app[count.index].id
  route_table_id = aws_route_table.app[count.index].id
}

resource "aws_route_table" "db" {
  count = local.az_count

  vpc_id = aws_vpc.this.id

  tags = merge(local.common_tags, {
    Name = "${var.name}-db-rt-${local.azs[count.index]}"
  })
}

resource "aws_route" "db_internet_ipv4" {
  count = var.enable_database_internet_egress ? local.az_count : 0

  route_table_id         = aws_route_table.db[count.index].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = var.single_nat_gateway ? aws_nat_gateway.this[0].id : aws_nat_gateway.this[count.index].id
}

resource "aws_route_table_association" "db" {
  count = local.az_count

  subnet_id      = aws_subnet.db[count.index].id
  route_table_id = aws_route_table.db[count.index].id
}

resource "aws_security_group" "web" {
  name        = "${var.name}-web-sg"
  description = "Public web tier security group"
  vpc_id      = aws_vpc.this.id

  dynamic "ingress" {
    for_each = var.allow_http ? [1] : []
    content {
      description = "HTTP from allowed CIDRs"
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      cidr_blocks = var.web_ingress_cidrs
    }
  }

  dynamic "ingress" {
    for_each = var.allow_https ? [1] : []
    content {
      description = "HTTPS from allowed CIDRs"
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = var.web_ingress_cidrs
    }
  }

  egress {
    description = "Outbound IPv4"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.name}-web-sg"
    Tier = "web"
  })
}

resource "aws_security_group" "app" {
  name        = "${var.name}-app-sg"
  description = "Private app tier security group"
  vpc_id      = aws_vpc.this.id

  ingress {
    description     = "Application traffic from web tier"
    from_port       = var.app_port
    to_port         = var.app_port
    protocol        = "tcp"
    security_groups = [aws_security_group.web.id]
  }

  dynamic "ingress" {
    for_each = length(var.app_additional_ingress_cidrs) > 0 ? [1] : []
    content {
      description = "Direct development or test access"
      from_port   = var.app_port
      to_port     = var.app_port
      protocol    = "tcp"
      cidr_blocks = var.app_additional_ingress_cidrs
    }
  }

  egress {
    description = "Outbound IPv4"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.name}-app-sg"
    Tier = "app"
  })
}

resource "aws_security_group" "db" {
  name        = "${var.name}-db-sg"
  description = "Private database tier security group"
  vpc_id      = aws_vpc.this.id

  ingress {
    description     = "Database traffic from app tier"
    from_port       = var.db_port
    to_port         = var.db_port
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  dynamic "ingress" {
    for_each = length(var.db_additional_ingress_cidrs) > 0 ? [1] : []
    content {
      description = "Direct development or test access"
      from_port   = var.db_port
      to_port     = var.db_port
      protocol    = "tcp"
      cidr_blocks = var.db_additional_ingress_cidrs
    }
  }

  egress {
    description = "Outbound IPv4"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.name}-db-sg"
    Tier = "database"
  })
}

data "aws_iam_policy_document" "flow_logs_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["vpc-flow-logs.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "flow_logs_to_cloudwatch" {
  statement {
    effect = "Allow"

    actions = [
      "logs:CreateLogDelivery",
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:DeleteLogDelivery",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams",
      "logs:PutLogEvents"
    ]

    resources = [
      "arn:${data.aws_partition.current.partition}:logs:${data.aws_region.current.name}:*:*"
    ]
  }
}

resource "aws_cloudwatch_log_group" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0

  name              = "/aws/vpc/${var.name}/flow-logs"
  retention_in_days = var.flow_log_retention_in_days

  tags = merge(local.common_tags, {
    Name = "${var.name}-flow-logs"
  })
}

resource "aws_iam_role" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0

  name               = "${var.name}-vpc-flow-logs-role"
  assume_role_policy = data.aws_iam_policy_document.flow_logs_assume_role.json

  tags = merge(local.common_tags, {
    Name = "${var.name}-vpc-flow-logs-role"
  })
}

resource "aws_iam_role_policy" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0

  name   = "${var.name}-vpc-flow-logs-policy"
  role   = aws_iam_role.flow_logs[0].id
  policy = data.aws_iam_policy_document.flow_logs_to_cloudwatch.json
}

resource "aws_flow_log" "this" {
  count = var.enable_flow_logs ? 1 : 0

  iam_role_arn         = aws_iam_role.flow_logs[0].arn
  log_destination      = aws_cloudwatch_log_group.flow_logs[0].arn
  log_destination_type = "cloud-watch-logs"
  traffic_type         = "ALL"
  vpc_id               = aws_vpc.this.id

  tags = merge(local.common_tags, {
    Name = "${var.name}-vpc-flow-log"
  })
}

output "vpc_id" {
  value = aws_vpc.this.id
}

output "availability_zones" {
  value = local.azs
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "app_subnet_ids" {
  value = aws_subnet.app[*].id
}

output "db_subnet_ids" {
  value = aws_subnet.db[*].id
}

output "web_security_group_id" {
  value = aws_security_group.web.id
}

output "app_security_group_id" {
  value = aws_security_group.app.id
}

output "db_security_group_id" {
  value = aws_security_group.db.id
}

output "public_route_table_id" {
  value = aws_route_table.public.id
}

output "app_route_table_ids" {
  value = aws_route_table.app[*].id
}

output "db_route_table_ids" {
  value = aws_route_table.db[*].id
}

output "nat_gateway_ids" {
  value = aws_nat_gateway.this[*].id
}