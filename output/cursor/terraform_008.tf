The module lives under `terraform/modules/vpc-three-tier/` with an example at `terraform/modules/vpc-three-tier/examples/default/`. Per your instructions, the rest of this message is only the code.

// --- terraform/modules/vpc-three-tier/versions.tf ---
terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

// --- terraform/modules/vpc-three-tier/variables.tf ---
variable "name_prefix" {
  type        = string
  description = "Prefix for resource names."
  default     = "three-tier-dev"
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for the VPC."
  default     = "10.0.0.0/16"
}

variable "az_count" {
  type        = number
  description = "Number of availability zones (1-3)."
  default     = 2

  validation {
    condition     = var.az_count >= 1 && var.az_count <= 3
    error_message = "az_count must be between 1 and 3."
  }
}

variable "single_nat_gateway" {
  type        = bool
  description = "Use one NAT gateway for all private subnets (lower cost, faster iteration in dev)."
  default     = true
}

variable "dev_access_cidr_ipv4" {
  type        = string
  description = "CIDR allowed to reach web tier (HTTP/HTTPS/SSH). Use 0.0.0.0/0 for open dev access."
  default     = "0.0.0.0/0"
}

variable "web_http_port" {
  type    = number
  default = 80
}

variable "web_https_port" {
  type    = number
  default = 443
}

variable "web_ssh_port" {
  type    = number
  default = 22
}

variable "app_tcp_ports" {
  type        = list(number)
  description = "Ports on app tier reachable from web tier."
  default     = [8080, 8443, 3000, 5000]
}

variable "db_tcp_ports" {
  type        = list(number)
  description = "Database ports reachable from app tier."
  default     = [3306, 5432, 1433, 27017]
}

variable "tags" {
  type        = map(string)
  description = "Extra tags for all resources."
  default     = {}
}

// --- terraform/modules/vpc-three-tier/main.tf ---
data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, var.az_count)

  common_tags = merge(
    {
      Name        = var.name_prefix
      Environment = "dev"
      Tier        = "network"
    },
    var.tags
  )
}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.common_tags, { Name = "${var.name_prefix}-vpc" })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = merge(local.common_tags, { Name = "${var.name_prefix}-igw" })
}

resource "aws_subnet" "public" {
  for_each = toset(local.azs)

  vpc_id                  = aws_vpc.this.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, index(local.azs, each.value))
  availability_zone       = each.value
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-public-${each.value}"
    Tier = "web"
  })
}

resource "aws_subnet" "private_app" {
  for_each = toset(local.azs)

  vpc_id            = aws_vpc.this.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, 16 + index(local.azs, each.value))
  availability_zone = each.value

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-app-${each.value}"
    Tier = "app"
  })
}

resource "aws_subnet" "private_db" {
  for_each = toset(local.azs)

  vpc_id            = aws_vpc.this.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, 32 + index(local.azs, each.value))
  availability_zone = each.value

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-db-${each.value}"
    Tier = "database"
  })
}

resource "aws_eip" "nat" {
  count = var.single_nat_gateway ? 1 : length(local.azs)

  domain = "vpc"

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-nat-eip-${count.index}"
  })

  depends_on = [aws_internet_gateway.this]
}

resource "aws_nat_gateway" "this" {
  count = var.single_nat_gateway ? 1 : length(local.azs)

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = var.single_nat_gateway ? aws_subnet.public[local.azs[0]].id : aws_subnet.public[local.azs[count.index]].id

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-nat-${count.index}"
  })

  depends_on = [aws_internet_gateway.this]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = merge(local.common_tags, { Name = "${var.name_prefix}-public-rt" })
}

resource "aws_route_table_association" "public" {
  for_each = aws_subnet.public

  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  count = var.single_nat_gateway ? 1 : length(local.azs)

  vpc_id = aws_vpc.this.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.this[count.index].id
  }

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-private-rt-${count.index}"
  })
}

resource "aws_route_table_association" "private_app" {
  for_each = aws_subnet.private_app

  subnet_id      = each.value.id
  route_table_id = var.single_nat_gateway ? aws_route_table.private[0].id : aws_route_table.private[index(local.azs, each.value.availability_zone)].id
}

resource "aws_route_table_association" "private_db" {
  for_each = aws_subnet.private_db

  subnet_id      = each.value.id
  route_table_id = var.single_nat_gateway ? aws_route_table.private[0].id : aws_route_table.private[index(local.azs, each.value.availability_zone)].id
}

resource "aws_security_group" "web" {
  name        = "${var.name_prefix}-web-sg"
  description = "Web tier: HTTP/HTTPS/SSH from dev CIDR"
  vpc_id      = aws_vpc.this.id

  ingress {
    description = "HTTP"
    from_port   = var.web_http_port
    to_port     = var.web_http_port
    protocol    = "tcp"
    cidr_blocks = [var.dev_access_cidr_ipv4]
  }

  ingress {
    description = "HTTPS"
    from_port   = var.web_https_port
    to_port     = var.web_https_port
    protocol    = "tcp"
    cidr_blocks = [var.dev_access_cidr_ipv4]
  }

  ingress {
    description = "SSH"
    from_port   = var.web_ssh_port
    to_port     = var.web_ssh_port
    protocol    = "tcp"
    cidr_blocks = [var.dev_access_cidr_ipv4]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${var.name_prefix}-web-sg" })
}

resource "aws_security_group" "app" {
  name        = "${var.name_prefix}-app-sg"
  description = "App tier: from web security group"
  vpc_id      = aws_vpc.this.id

  dynamic "ingress" {
    for_each = var.app_tcp_ports
    content {
      description     = "App port ${ingress.value}"
      from_port       = ingress.value
      to_port         = ingress.value
      protocol        = "tcp"
      security_groups = [aws_security_group.web.id]
    }
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${var.name_prefix}-app-sg" })
}

resource "aws_security_group" "database" {
  name        = "${var.name_prefix}-db-sg"
  description = "Database tier: from app security group"
  vpc_id      = aws_vpc.this.id

  dynamic "ingress" {
    for_each = var.db_tcp_ports
    content {
      description     = "DB port ${ingress.value}"
      from_port       = ingress.value
      to_port         = ingress.value
      protocol        = "tcp"
      security_groups = [aws_security_group.app.id]
    }
  }

  egress {
    description = "All outbound (patches, DNS)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${var.name_prefix}-db-sg" })
}

// --- terraform/modules/vpc-three-tier/outputs.tf ---
output "vpc_id" {
  value = aws_vpc.this.id
}

output "vpc_cidr_block" {
  value = aws_vpc.this.cidr_block
}

output "internet_gateway_id" {
  value = aws_internet_gateway.this.id
}

output "availability_zones" {
  value = local.azs
}

output "public_subnet_ids" {
  value = [for az in local.azs : aws_subnet.public[az].id]
}

output "private_app_subnet_ids" {
  value = [for az in local.azs : aws_subnet.private_app[az].id]
}

output "private_db_subnet_ids" {
  value = [for az in local.azs : aws_subnet.private_db[az].id]
}

output "public_route_table_id" {
  value = aws_route_table.public.id
}

output "private_route_table_ids" {
  value = aws_route_table.private[*].id
}

output "nat_gateway_ids" {
  value = aws_nat_gateway.this[*].id
}

output "web_security_group_id" {
  value = aws_security_group.web.id
}

output "app_security_group_id" {
  value = aws_security_group.app.id
}

output "database_security_group_id" {
  value = aws_security_group.database.id
}

// --- terraform/modules/vpc-three-tier/examples/default/main.tf ---
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

`</think>`
The module is on disk at `terraform/modules/vpc-three-tier/` (plus `examples/default/main.tf` to run it). Per your request, the following is only code.

// terraform/modules/vpc-three-tier/versions.tf

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

// terraform/modules/vpc-three-tier/variables.tf

variable "name_prefix" {
  type        = string
  description = "Prefix for resource names."
  default     = "three-tier-dev"
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for the VPC."
  default     = "10.0.0.0/16"
}

variable "az_count" {
  type        = number
  description = "Number of availability zones (1-3)."
  default     = 2

  validation {
    condition     = var.az_count >= 1 && var.az_count <= 3
    error_message = "az_count must be between 1 and 3."
  }
}

variable "single_nat_gateway" {
  type        = bool
  description = "Use one NAT gateway for all private subnets (lower cost, faster iteration in dev)."
  default     = true
}

variable "dev_access_cidr_ipv4" {
  type        = string
  description = "CIDR allowed to reach web tier (HTTP/HTTPS/SSH). Use 0.0.0.0/0 for open dev access."
  default     = "0.0.0.0/0"
}

variable "web_http_port" {
  type    = number
  default = 80
}

variable "web_https_port" {
  type    = number
  default = 443
}

variable "web_ssh_port" {
  type    = number
  default = 22
}

variable "app_tcp_ports" {
  type        = list(number)
  description = "Ports on app tier reachable from web tier."
  default     = [8080, 8443, 3000, 5000]
}

variable "db_tcp_ports" {
  type        = list(number)
  description = "Database ports reachable from app tier."
  default     = [3306, 5432, 1433, 27017]
}

variable "tags" {
  type        = map(string)
  description = "Extra tags for all resources."
  default     = {}
}

// terraform/modules/vpc-three-tier/main.tf

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, var.az_count)

  common_tags = merge(
    {
      Name        = var.name_prefix
      Environment = "dev"
      Tier        = "network"
    },
    var.tags
  )
}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.common_tags, { Name = "${var.name_prefix}-vpc" })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = merge(local.common_tags, { Name = "${var.name_prefix}-igw" })
}

resource "aws_subnet" "public" {
  for_each = toset(local.azs)

  vpc_id                  = aws_vpc.this.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, index(local.azs, each.value))
  availability_zone       = each.value
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-public-${each.value}"
    Tier = "web"
  })
}

resource "aws_subnet" "private_app" {
  for_each = toset(local.azs)

  vpc_id            = aws_vpc.this.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, 16 + index(local.azs, each.value))
  availability_zone = each.value

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-app-${each.value}"
    Tier = "app"
  })
}

resource "aws_subnet" "private_db" {
  for_each = toset(local.azs)

  vpc_id            = aws_vpc.this.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, 32 + index(local.azs, each.value))
  availability_zone = each.value

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-db-${each.value}"
    Tier = "database"
  })
}

resource "aws_eip" "nat" {
  count = var.single_nat_gateway ? 1 : length(local.azs)

  domain = "vpc"

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-nat-eip-${count.index}"
  })

  depends_on = [aws_internet_gateway.this]
}

resource "aws_nat_gateway" "this" {
  count = var.single_nat_gateway ? 1 : length(local.azs)

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = var.single_nat_gateway ? aws_subnet.public[local.azs[0]].id : aws_subnet.public[local.azs[count.index]].id

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-nat-${count.index}"
  })

  depends_on = [aws_internet_gateway.this]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = merge(local.common_tags, { Name = "${var.name_prefix}-public-rt" })
}

resource "aws_route_table_association" "public" {
  for_each = aws_subnet.public

  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  count = var.single_nat_gateway ? 1 : length(local.azs)

  vpc_id = aws_vpc.this.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.this[count.index].id
  }

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-private-rt-${count.index}"
  })
}

resource "aws_route_table_association" "private_app" {
  for_each = aws_subnet.private_app

  subnet_id      = each.value.id
  route_table_id = var.single_nat_gateway ? aws_route_table.private[0].id : aws_route_table.private[index(local.azs, each.value.availability_zone)].id
}

resource "aws_route_table_association" "private_db" {
  for_each = aws_subnet.private_db

  subnet_id      = each.value.id
  route_table_id = var.single_nat_gateway ? aws_route_table.private[0].id : aws_route_table.private[index(local.azs, each.value.availability_zone)].id
}

resource "aws_security_group" "web" {
  name        = "${var.name_prefix}-web-sg"
  description = "Web tier: HTTP/HTTPS/SSH from dev CIDR"
  vpc_id      = aws_vpc.this.id

  ingress {
    description = "HTTP"
    from_port   = var.web_http_port
    to_port     = var.web_http_port
    protocol    = "tcp"
    cidr_blocks = [var.dev_access_cidr_ipv4]
  }

  ingress {
    description = "HTTPS"
    from_port   = var.web_https_port
    to_port     = var.web_https_port
    protocol    = "tcp"
    cidr_blocks = [var.dev_access_cidr_ipv4]
  }

  ingress {
    description = "SSH"
    from_port   = var.web_ssh_port
    to_port     = var.web_ssh_port
    protocol    = "tcp"
    cidr_blocks = [var.dev_access_cidr_ipv4]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${var.name_prefix}-web-sg" })
}

resource "aws_security_group" "app" {
  name        = "${var.name_prefix}-app-sg"
  description = "App tier: from web security group"
  vpc_id      = aws_vpc.this.id

  dynamic "ingress" {
    for_each = var.app_tcp_ports
    content {
      description     = "App port ${ingress.value}"
      from_port       = ingress.value
      to_port         = ingress.value
      protocol        = "tcp"
      security_groups = [aws_security_group.web.id]
    }
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${var.name_prefix}-app-sg" })
}

resource "aws_security_group" "database" {
  name        = "${var.name_prefix}-db-sg"
  description = "Database tier: from app security group"
  vpc_id      = aws_vpc.this.id

  dynamic "ingress" {
    for_each = var.db_tcp_ports
    content {
      description     = "DB port ${ingress.value}"
      from_port       = ingress.value
      to_port         = ingress.value
      protocol        = "tcp"
      security_groups = [aws_security_group.app.id]
    }
  }

  egress {
    description = "All outbound (patches, DNS)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${var.name_prefix}-db-sg" })
}

// terraform/modules/vpc-three-tier/outputs.tf

output "vpc_id" {
  value = aws_vpc.this.id
}

output "vpc_cidr_block" {
  value = aws_vpc.this.cidr_block
}

output "internet_gateway_id" {
  value = aws_internet_gateway.this.id
}

output "availability_zones" {
  value = local.azs
}

output "public_subnet_ids" {
  value = [for az in local.azs : aws_subnet.public[az].id]
}

output "private_app_subnet_ids" {
  value = [for az in local.azs : aws_subnet.private_app[az].id]
}

output "private_db_subnet_ids" {
  value = [for az in local.azs : aws_subnet.private_db[az].id]
}

output "public_route_table_id" {
  value = aws_route_table.public.id
}

output "private_route_table_ids" {
  value = aws_route_table.private[*].id
}

output "nat_gateway_ids" {
  value = aws_nat_gateway.this[*].id
}

output "web_security_group_id" {
  value = aws_security_group.web.id
}

output "app_security_group_id" {
  value = aws_security_group.app.id
}

output "database_security_group_id" {
  value = aws_security_group.database.id
}

// terraform/modules/vpc-three-tier/examples/default/main.tf

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