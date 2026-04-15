import hashlib
import secrets
import sqlite3
from typing import Union


def _legacy_password_digest(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def authenticate_user(
    username: str,
    password: str,
    conn: Union[sqlite3.Connection, object],
) -> bool:
    if not username or not password:
        return False
    cursor = conn.execute(
        "SELECT password FROM users WHERE username = ? LIMIT 1",
        (username,),
    )
    row = cursor.fetchone()
    if row is None:
        return False
    stored = row[0]
    if isinstance(stored, bytes):
        stored = stored.decode("utf-8", errors="replace")
    candidate = _legacy_password_digest(password)
    return secrets.compare_digest(stored, candidate)


def _demo():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE users (username TEXT PRIMARY KEY NOT NULL, password TEXT NOT NULL)"
    )
    conn.execute(
        "INSERT INTO users (username, password) VALUES (?, ?)",
        ("alice", _legacy_password_digest("secret123")),
    )
    conn.commit()
    assert authenticate_user("alice", "secret123", conn) is True
    assert authenticate_user("alice", "wrong", conn) is False
    assert authenticate_user("nobody", "secret123", conn) is False
    conn.close()


if __name__ == "__main__":
    _demo()
