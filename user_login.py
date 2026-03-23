import secrets
from typing import Optional

import psycopg2
from psycopg2.extensions import connection as PGConnection


def _normalize_stored_password(stored) -> bytes:
    if isinstance(stored, memoryview):
        stored = stored.tobytes()
    if isinstance(stored, bytes):
        return stored
    return str(stored).encode("utf-8")


def login_user(
    username: str,
    password: str,
    conn: Optional[PGConnection] = None,
) -> Optional[int]:
    if conn is not None:
        return _login_with_connection(conn, username, password)
    from db_connection import get_db_connection

    with get_db_connection() as c:
        return _login_with_connection(c, username, password)


def _login_with_connection(
    conn: PGConnection,
    username: str,
    password: str,
) -> Optional[int]:
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, password FROM users WHERE username = %s LIMIT 1",
            (username,),
        )
        row = cur.fetchone()
    finally:
        cur.close()
    if not row:
        return None
    user_id, stored_pw = row
    if secrets.compare_digest(
        _normalize_stored_password(stored_pw),
        password.encode("utf-8"),
    ):
        return user_id
    return None


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        sys.exit("usage: python user_login.py <username> <password>")
    u, p = sys.argv[1], sys.argv[2]
    try:
        uid = login_user(u, p)
    except psycopg2.Error as e:
        sys.exit(f"database error: {e}")
    print(uid if uid is not None else "login failed")
