I’m checking for existing Terraform conventions and where a new runnable module should live so I can drop in something consistent.

I found no existing Terraform module layout, so I’m adding a self-contained root module in its own directory and validating it there.

The patch tool couldn’t create the new directory directly here, so I’m creating the target folder first and then reapplying the module file.

The repo looks read-only in this session, so I’m validating the module in a temporary workspace and will return the full runnable code directly.

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

variable "aws_region" {
  description = "AWS region for the development VPC."
  type        = string
  default     = "us-east-1"
}

variable "name" {
  description = "Name prefix applied to all resources."
  type        = string
  default     = "three-tier-dev"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.42.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones to use."
  type        = number
  default     = 2

  validation {
    condition     = var.az_count >= 1 && var.az_count <= 4
    error_message = "az_count must be between 1 and 4."
  }
}

variable "subnet_newbits" {
  description = "Additional subnet bits used to carve tier subnets from the VPC CIDR."
  type        = number
  default     = 4

  validation {
    condition     = var.subnet_newbits >= 2 && var.subnet_newbits <= 8
    error_message = "subnet_newbits must be between 2 and 8."
  }
}

variable "development_cidrs" {
  description = "CIDR blocks allowed to reach the environment during development and testing."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "web_ingress_ports" {
  description = "Publicly reachable web-tier ports."
  type        = list(number)
  default     = [22, 80, 443, 8080]
}

variable "app_ingress_ports" {
  description = "Application-tier ports reachable from the web tier and development CIDRs."
  type        = list(number)
  default     = [22, 3000, 8080, 5000]
}

variable "db_ingress_ports" {
  description = "Database-tier ports reachable from the app tier and development CIDRs."
  type        = list(number)
  default     = [3306, 5432]
}

variable "tags" {
  description = "Additional tags to apply to resources."
  type        = map(string)
  default     = {}
}

provider "aws" {
  region = var.aws_region
}

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  selected_az_count = min(var.az_count, length(data.aws_availability_zones.available.names))
  azs               = slice(data.aws_availability_zones.available.names, 0, local.selected_az_count)

  public_subnets = {
    for index, az in local.azs :
    "web-${index + 1}" => {
      az   = az
      cidr = cidrsubnet(var.vpc_cidr, var.subnet_newbits, index)
    }
  }

  app_subnets = {
    for index, az in local.azs :
    "app-${index + 1}" => {
      az   = az
      cidr = cidrsubnet(var.vpc_cidr, var.subnet_newbits, index + local.selected_az_count)
    }
  }

  db_subnets = {
    for index, az in local.azs :
    "db-${index + 1}" => {
      az   = az
      cidr = cidrsubnet(var.vpc_cidr, var.subnet_newbits, index + (local.selected_az_count * 2))
    }
  }

  common_tags = merge(
    {
      Project     = var.name
      Environment = "development"
      ManagedBy   = "terraform"
    },
    var.tags
  )
}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(local.common_tags, {
    Name = "${var.name}-vpc"
  })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = merge(local.common_tags, {
    Name = "${var.name}-igw"
  })
}

resource "aws_subnet" "public" {
  for_each = local.public_subnets

  vpc_id                  = aws_vpc.this.id
  availability_zone       = each.value.az
  cidr_block              = each.value.cidr
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "${var.name}-${each.key}"
    Tier = "web"
    Type = "public"
  })
}

resource "aws_subnet" "app" {
  for_each = local.app_subnets

  vpc_id            = aws_vpc.this.id
  availability_zone = each.value.az
  cidr_block        = each.value.cidr

  tags = merge(local.common_tags, {
    Name = "${var.name}-${each.key}"
    Tier = "app"
    Type = "private"
  })
}

resource "aws_subnet" "db" {
  for_each = local.db_subnets

  vpc_id            = aws_vpc.this.id
  availability_zone = each.value.az
  cidr_block        = each.value.cidr

  tags = merge(local.common_tags, {
    Name = "${var.name}-${each.key}"
    Tier = "database"
    Type = "private"
  })
}

resource "aws_eip" "nat" {
  domain = "vpc"

  tags = merge(local.common_tags, {
    Name = "${var.name}-nat-eip"
  })
}

resource "aws_nat_gateway" "this" {
  allocation_id = aws_eip.nat.id
  subnet_id     = values(aws_subnet.public)[0].id

  depends_on = [aws_internet_gateway.this]

  tags = merge(local.common_tags, {
    Name = "${var.name}-nat"
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = merge(local.common_tags, {
    Name = "${var.name}-public-rt"
  })
}

resource "aws_route_table" "app" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.this.id
  }

  tags = merge(local.common_tags, {
    Name = "${var.name}-app-rt"
  })
}

resource "aws_route_table" "db" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.this.id
  }

  tags = merge(local.common_tags, {
    Name = "${var.name}-db-rt"
  })
}

resource "aws_route_table_association" "public" {
  for_each = aws_subnet.public

  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "app" {
  for_each = aws_subnet.app

  subnet_id      = each.value.id
  route_table_id = aws_route_table.app.id
}

resource "aws_route_table_association" "db" {
  for_each = aws_subnet.db

  subnet_id      = each.value.id
  route_table_id = aws_route_table.db.id
}

resource "aws_security_group" "web" {
  name        = "${var.name}-web-sg"
  description = "Security group for the public web tier."
  vpc_id      = aws_vpc.this.id

  dynamic "ingress" {
    for_each = toset(var.web_ingress_ports)

    content {
      description = "Development and testing access"
      from_port   = ingress.value
      to_port     = ingress.value
      protocol    = "tcp"
      cidr_blocks = var.development_cidrs
    }
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.name}-web-sg"
  })
}

resource "aws_security_group" "app" {
  name        = "${var.name}-app-sg"
  description = "Security group for the private application tier."
  vpc_id      = aws_vpc.this.id

  dynamic "ingress" {
    for_each = toset(var.app_ingress_ports)

    content {
      description = "Development and testing access"
      from_port   = ingress.value
      to_port     = ingress.value
      protocol    = "tcp"
      cidr_blocks = var.development_cidrs
    }
  }

  dynamic "ingress" {
    for_each = toset(var.app_ingress_ports)

    content {
      description     = "Web tier access"
      from_port       = ingress.value
      to_port         = ingress.value
      protocol        = "tcp"
      security_groups = [aws_security_group.web.id]
    }
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.name}-app-sg"
  })
}

resource "aws_security_group" "db" {
  name        = "${var.name}-db-sg"
  description = "Security group for the private database tier."
  vpc_id      = aws_vpc.this.id

  dynamic "ingress" {
    for_each = toset(var.db_ingress_ports)

    content {
      description = "Development and testing access"
      from_port   = ingress.value
      to_port     = ingress.value
      protocol    = "tcp"
      cidr_blocks = var.development_cidrs
    }
  }

  dynamic "ingress" {
    for_each = toset(var.db_ingress_ports)

    content {
      description     = "Application tier access"
      from_port       = ingress.value
      to_port         = ingress.value
      protocol        = "tcp"
      security_groups = [aws_security_group.app.id]
    }
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.name}-db-sg"
  })
}

output "vpc_id" {
  description = "ID of the VPC."
  value       = aws_vpc.this.id
}

output "availability_zones" {
  description = "Availability zones used for the deployment."
  value       = local.azs
}

output "public_subnet_ids" {
  description = "IDs of the public web subnets."
  value       = [for subnet in values(aws_subnet.public) : subnet.id]
}

output "app_subnet_ids" {
  description = "IDs of the private application subnets."
  value       = [for subnet in values(aws_subnet.app) : subnet.id]
}

output "db_subnet_ids" {
  description = "IDs of the private database subnets."
  value       = [for subnet in values(aws_subnet.db) : subnet.id]
}

output "route_table_ids" {
  description = "Route table IDs for each network tier."
  value = {
    public = aws_route_table.public.id
    app    = aws_route_table.app.id
    db     = aws_route_table.db.id
  }
}

output "security_group_ids" {
  description = "Security group IDs for each application tier."
  value = {
    web = aws_security_group.web.id
    app = aws_security_group.app.id
    db  = aws_security_group.db.id
  }
}