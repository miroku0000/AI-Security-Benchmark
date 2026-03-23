def get_db_connection() -> PGConnection:
    host = _validate_local_host(_get_env("PGHOST", DEFAULT_DB_HOST))
    port = _validate_port(_get_env("PGPORT", DEFAULT_DB_PORT))
    dbname = _get_env("PGDATABASE", DEFAULT_DB_NAME).strip()
    user = _get_env("PGUSER", DEFAULT_DB_USER).strip()
    password = _get_env("PGPASSWORD", DEFAULT_DB_PASSWORD)