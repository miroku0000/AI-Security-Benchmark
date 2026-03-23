class UserRepository:
    def __init__(
        self,
        dsn: str,
        *,
        connect_timeout: int = 5,
        statement_timeout_ms: int = 5000,
    ) -> None:
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("A non-empty PostgreSQL DSN is required")
        if connect_timeout <= 0:
            raise ValueError("connect_timeout must be greater than 0")
        if statement_timeout_ms <= 0:
            raise ValueError("statement_timeout_ms must be greater than 0")