def _build_auth_query(paramstyle):
    if paramstyle == "qmark":
        return "SELECT 1 FROM users WHERE username = ? AND password = ?", None
    if paramstyle == "format":
        return "SELECT 1 FROM users WHERE username = %s AND password = %s", None
    if paramstyle == "pyformat":
        return (
            "SELECT 1 FROM users WHERE username = %(username)s AND password = %(password)s",
            "mapping",
        )
    if paramstyle == "named":
        return (
            "SELECT 1 FROM users WHERE username = :username AND password = :password",
            "mapping",
        )
    if paramstyle == "numeric":
        return "SELECT 1 FROM users WHERE username = :1 AND password = :2", None
    return "SELECT 1 FROM users WHERE username = ? AND password = ?", None