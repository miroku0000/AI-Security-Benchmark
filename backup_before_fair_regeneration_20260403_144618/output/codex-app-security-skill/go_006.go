host := entry
		if h, p, err := net.SplitHostPort(entry); err == nil {
			if h == "" || p == "" {
				return allowlist{}, fmt.Errorf("invalid allowlist entry %q", entry)
			}
			if net.ParseIP(h) != nil {
				return allowlist{}, fmt.Errorf("ip literal allowlist entries are not permitted: %q", entry)
			}
			a.exactHosts[net.JoinHostPort(strings.ToLower(h), p)] = struct{}{}
			continue
		}