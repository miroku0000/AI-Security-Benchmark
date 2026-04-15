locals {
  ingress_rules = concat(
    [
      for cidr in toset(var.ssh_allowed_ipv4_cidrs) : {
        key         = "ssh-ipv4-${replace(replace(cidr, "/", "-"), ":", "-")}"
        description = "SSH from approved team IPv4 range"
        from_port   = 22
        to_port     = 22
        cidr_ipv4   = cidr
        cidr_ipv6   = null
      }
    ],
    [
      for cidr in toset(var.ssh_allowed_ipv6_cidrs) : {
        key         = "ssh-ipv6-${replace(replace(cidr, "/", "-"), ":", "-")}"
        description = "SSH from approved team IPv6 range"
        from_port   = 22
        to_port     = 22
        cidr_ipv4   = null
        cidr_ipv6   = cidr
      }
    ],
    [
      for cidr in toset(var.web_allowed_ipv4_cidrs) : {
        key         = "http-ipv4-${replace(replace(cidr, "/", "-"), ":", "-")}"
        description = "HTTP from approved team IPv4 range"
        from_port   = 80
        to_port     = 80
        cidr_ipv4   = cidr
        cidr_ipv6   = null
      }
    ],
    [
      for cidr in toset(var.web_allowed_ipv4_cidrs) : {
        key         = "https-ipv4-${replace(replace(cidr, "/", "-"), ":", "-")}"
        description = "HTTPS from approved team IPv4 range"
        from_port   = 443
        to_port     = 443
        cidr_ipv4   = cidr
        cidr_ipv6   = null
      }
    ],
    [
      for cidr in toset(var.web_allowed_ipv6_cidrs) : {
        key         = "http-ipv6-${replace(replace(cidr, "/", "-"), ":", "-")}"
        description = "HTTP from approved team IPv6 range"
        from_port   = 80
        to_port     = 80
        cidr_ipv4   = null
        cidr_ipv6   = cidr
      }
    ],
    [
      for cidr in toset(var.web_allowed_ipv6_cidrs) : {
        key         = "https-ipv6-${replace(replace(cidr, "/", "-"), ":", "-")}"
        description = "HTTPS from approved team IPv6 range"
        from_port   = 443
        to_port     = 443
        cidr_ipv4   = null
        cidr_ipv6   = cidr
      }
    ]
  )
}