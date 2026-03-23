func isPrivateOrLocal(ip netip.Addr) bool {
	if !ip.IsValid() {
		return true
	}
	if ip.IsLoopback() || ip.IsPrivate() || ip.IsLinkLocalUnicast() || ip.IsLinkLocalMulticast() || ip.IsMulticast() {
		return true
	}
	if ip.Is4() {
		v4 := ip.As4()
		if v4[0] == 0 {
			return true
		}
		if v4[0] == 100 && v4[1]&0xC0 == 64 {
			return true
		}
		if v4[0] == 169 && v4[1] == 254 {
			return true
		}
	}
	return false
}