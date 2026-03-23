def _candidate_queries() -> Iterable[str]:
    yield "SELECT 1 FROM users WHERE username = ? AND password = ?"
    yield "SELECT 1 FROM users WHERE username = %s AND password = %s"
    yield "SELECT 1 FROM users WHERE username = :1 AND password = :2"
    yield "SELECT 1 FROM users WHERE username = :username AND password = :password"