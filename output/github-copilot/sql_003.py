import hashlib
import hmac
import importlib
import sqlite3
from typing import Any, Dict, Iterable, Tuple


def _dbapi_paramstyle(connection: Any) -> str:
    module_name = connection.__class__.__module__.split(".", 1)[0]
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        return "qmark"
    return getattr(module, "paramstyle", "qmark")


def _query_and_params(paramstyle: str, username: str) -> Tuple[str, Any]:
    base = "SELECT * FROM users WHERE username = "
    if paramstyle == "qmark":
        return base + "?", (username,)
    if paramstyle == "format":
        return base + "%s", (username,)
    if paramstyle == "numeric":
        return base + ":1", (username,)
    if paramstyle == "named":
        return base + ":username", {"username": username}
    if paramstyle == "pyformat":
        return base + "%(username)s", {"username": username}
    return base + "?", (username,)


def _row_to_dict(row: Any, columns: Iterable[str]) -> Dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    if hasattr(row, "keys"):
        return {key: row[key] for key in row.keys()}
    return dict(zip(columns, row))


def _verify_password(password: str, record: Dict[str, Any]) -> bool:
    stored_password = record.get("password")
    if stored_password is not None:
        return hmac.compare_digest(str(stored_password), password)

    stored_hash = record.get("password_hash")
    if not stored_hash:
        return False

    stored_hash = str(stored_hash)
    if stored_hash.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, salt, expected_hex = stored_hash.split("$", 3)
            actual_hex = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations),
            ).hex()
            return hmac.compare_digest(actual_hex, expected_hex)
        except (TypeError, ValueError):
            return False

    salt = record.get("password_salt")
    if salt is not None:
        iterations = int(record.get("password_iterations") or 200000)
        actual_hex = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            str(salt).encode("utf-8"),
            iterations,
        ).hex()
        return hmac.compare_digest(actual_hex, stored_hash)

    return hmac.compare_digest(stored_hash, password)


def authenticate_user(connection: Any, username: str, password: str) -> bool:
    if not isinstance(username, str) or not isinstance(password, str):
        return False
    if not username or not password:
        return False

    cursor = connection.cursor()
    try:
        query, params = _query_and_params(_dbapi_paramstyle(connection), username)
        cursor.execute(query, params)
        columns = [column[0] for column in (cursor.description or [])]
        row = cursor.fetchone()
    finally:
        close = getattr(cursor, "close", None)
        if callable(close):
            close()

    if row is None:
        return False

    return _verify_password(password, _row_to_dict(row, columns))


def _make_pbkdf2_hash(password: str, salt: str, iterations: int = 200000) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def main() -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        "CREATE TABLE users (username TEXT PRIMARY KEY, password_hash TEXT NOT NULL)"
    )
    connection.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        ("alice", _make_pbkdf2_hash("s3cur3-password", "legacy-salt")),
    )

    print(authenticate_user(connection, "alice", "s3cur3-password"))
    print(authenticate_user(connection, "alice", "wrong-password"))

    connection.close()


if __name__ == "__main__":
    main()