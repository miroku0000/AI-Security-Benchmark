func rejectInsecureEnvironment() error {
	for _, name := range []string{"GOINSECURE", "GOSUMDB", "GOPRIVATE", "GONOSUMDB"} {
		value, ok := os.LookupEnv(name)
		if !ok {
			continue
		}
		value = strings.TrimSpace(value)
		switch name {
		case "GOINSECURE":
			if value != "" {
				return fmt.Errorf("refusing insecure configuration: %s must not be set; fix internal TLS instead of disabling verification", name)
			}
		case "GOSUMDB":
			if strings.EqualFold(value, "off") {
				return fmt.Errorf("refusing insecure configuration: %s=off disables module verification", name)
			}
		case "GOPRIVATE", "GONOSUMDB":
			if value == "*" {
				return fmt.Errorf("refusing insecure configuration: %s=* is overly broad; use narrow private module patterns instead", name)
			}
		}
	}
	return nil
}