fn is_forbidden_ipv4(ip: Ipv4Addr) -> bool {
    ip.is_private()
        || ip.is_loopback()
        || ip.is_link_local()
        || ip.is_multicast()
        || ip.is_broadcast()
        || ip.is_unspecified()
        || ip.is_documentation()
        || ip.octets()[0] == 0
        || ip.octets()[0] >= 224
        || (ip.octets()[0] == 100 && (ip.octets()[1] & 0b1100_0000) == 0b0100_0000)
        || (ip.octets()[0] == 198 && ip.octets()[1] == 18)
        || (ip.octets()[0] == 198 && ip.octets()[1] == 19)
}