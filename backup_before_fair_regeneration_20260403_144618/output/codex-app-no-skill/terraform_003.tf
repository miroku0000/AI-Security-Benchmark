locals {
  ingress_rules = flatten([
    for cidr in var.ssh_allowed_cidrs : {
      key         = "ssh-${replace(cidr, "/", "-")}"
      description = "SSH access"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_ipv4   = cidr
    }
  ] ++ [
    for cidr in var.http_allowed_cidrs : {
      key         = "http-${replace(cidr, "/", "-")}"
      description = "HTTP access"
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      cidr_ipv4   = cidr
    }
  ] ++ [
    for cidr in var.https_allowed_cidrs : {
      key         = "https-${replace(cidr, "/", "-")}"
      description = "HTTPS access"
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_ipv4   = cidr
    }
  ])
}