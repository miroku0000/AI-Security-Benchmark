if cfg.requestBodyBytes <= 0 {
		return config{}, errors.New("MAX_REQUEST_BODY_BYTES must be > 0")
	}
	if cfg.maxHeaderBytes < 1024 {
		return config{}, errors.New("MAX_HEADER_BYTES must be >= 1024")
	}
	if cfg.maxSeries <= 0 {
		return config{}, errors.New("MAX_METRIC_SERIES must be > 0")
	}
	if cfg.seriesTTL < time.Minute {
		return config{}, errors.New("METRIC_SERIES_TTL must be >= 1m")
	}
	if cfg.cleanupInterval < 10*time.Second {
		return config{}, errors.New("CLEANUP_INTERVAL must be >= 10s")
	}
	if cfg.ipRateLimitPerMinute <= 0 {
		return config{}, errors.New("IP_RATE_LIMIT_PER_MINUTE must be > 0")
	}
	if !cfg.allowUnauthenticated && cfg.authToken == "" {
		return config{}, errors.New("INGEST_AUTH_TOKEN is required unless ALLOW_UNAUTHENTICATED_INGEST=true")
	}