@staticmethod
    def from_env() -> "ClientConfig":
        return ClientConfig(
            host=os.getenv("REDIS_HOST", "127.0.0.1"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            username=os.getenv("REDIS_USERNAME"),
            password=os.getenv("REDIS_PASSWORD"),
            use_tls=os.getenv("REDIS_TLS", "false").lower() in {"1", "true", "yes", "on"},
            socket_timeout=float(os.getenv("REDIS_SOCKET_TIMEOUT", "3.0")),
            socket_connect_timeout=float(os.getenv("REDIS_CONNECT_TIMEOUT", "3.0")),
            health_check_interval=int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "30")),
            key_prefix=os.getenv("REDIS_KEY_PREFIX", "cache:"),
            max_script_bytes=int(os.getenv("REDIS_MAX_SCRIPT_BYTES", "8192")),
            max_keys=int(os.getenv("REDIS_MAX_KEYS", "16")),
            max_args=int(os.getenv("REDIS_MAX_ARGS", "32")),
            max_item_bytes=int(os.getenv("REDIS_MAX_ITEM_BYTES", "4096")),
        )