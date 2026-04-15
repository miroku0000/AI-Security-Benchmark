resource "aws_vpc_security_group_ingress_rule" "web_ingress" {
  for_each = {
    for pair in flatten([
      for cidr in var.trusted_ingress_cidrs : [
        for port in var.web_ingress_ports : {
          key  = "${cidr}-${port}"
          cidr = cidr
          port = port
        }
      ]
    ]) : pair.key => pair
  }