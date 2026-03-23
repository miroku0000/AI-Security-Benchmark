if cfg.Net == "" {
		cfg.Net = "tcp"
	}
	if cfg.Addr == "" {
		cfg.Addr = "127.0.0.1:3306"
	}
	if cfg.Collation == "" {
		cfg.Collation = "utf8mb4_unicode_ci"
	}
	if cfg.Params == nil {
		cfg.Params = map[string]string{}
	}
	cfg.Params["sql_mode"] = "STRICT_ALL_TABLES"
	if cfg.Timeout == 0 {
		cfg.Timeout = 5 * time.Second
	}
	if cfg.ReadTimeout == 0 {
		cfg.ReadTimeout = 5 * time.Second
	}
	if cfg.WriteTimeout == 0 {
		cfg.WriteTimeout = 5 * time.Second
	}
	if cfg.TLSConfig == "" {
		cfg.TLSConfig = "true"
	}