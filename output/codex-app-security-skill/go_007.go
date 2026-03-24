func OpenDemoDB(ctx context.Context) (*sql.DB, error) {
	if !isLocalHost(demoDBHost) {
		return nil, fmt.Errorf("refusing non-local demo database host %q", demoDBHost)
	}
	if demoDBPassword == "" {
		return nil, errors.New("set demoDBPassword before running")
	}