func loadConfig() (config, error) {
	cfg := config{
		ListenAddr:            getEnv("GRPC_LISTEN_ADDR", "127.0.0.1:50051"),
		AuthToken:             os.Getenv("GRPC_AUTH_TOKEN"),
		AllowInsecureDev:      getEnvBool("GRPC_ALLOW_INSECURE_DEV", false),
		TLSCertFile:           os.Getenv("GRPC_TLS_CERT_FILE"),
		TLSKeyFile:            os.Getenv("GRPC_TLS_KEY_FILE"),
		TLSClientCAFile:       os.Getenv("GRPC_TLS_CLIENT_CA_FILE"),
		MaxRecvMsgSize:        getEnvInt("GRPC_MAX_RECV_MSG_SIZE", 1<<20),
		MaxSendMsgSize:        getEnvInt("GRPC_MAX_SEND_MSG_SIZE", 1<<20),
		ConnectionTimeout:     getEnvDuration("GRPC_CONNECTION_TIMEOUT", 10*time.Second),
		ShutdownGracePeriod:   getEnvDuration("GRPC_SHUTDOWN_GRACE_PERIOD", 10*time.Second),
		KeepaliveMinTime:      getEnvDuration("GRPC_KEEPALIVE_MIN_TIME", 30*time.Second),
		KeepaliveTime:         getEnvDuration("GRPC_KEEPALIVE_TIME", 2*time.Minute),
		KeepaliveTimeout:      getEnvDuration("GRPC_KEEPALIVE_TIMEOUT", 20*time.Second),
		MaxConnectionIdle:     getEnvDuration("GRPC_MAX_CONNECTION_IDLE", 5*time.Minute),
		MaxConnectionAge:      getEnvDuration("GRPC_MAX_CONNECTION_AGE", 2*time.Hour),
		MaxConnectionAgeGrace: getEnvDuration("GRPC_MAX_CONNECTION_AGE_GRACE", 5*time.Minute),
	}