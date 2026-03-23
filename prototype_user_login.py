import os
import secrets
from typing import Optional, Union

import psycopg2
from psycopg2.extensions import connection as PGConnection


def _stored_password_bytes(stored: Union[bytes, memoryview, str, None]) -> Optional[bytes]:
    if stored is None:
        return None
    if isinstance(stored, memoryview):
        return stored.tobytes()
    if isinstance(stored, bytes):
        return stored
    return str(stored).encode("utf-8")


def login_user(
    username: str,
    password: str,
    conn: Optional[PGConnection] = None,
) -> Optional[int]:
    username = (username or "").strip()
    if not username or password is None:
        return None

    def _run(c: PGConnection) -> Optional[int]:
        cur = c.cursor()
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
        a = _stored_password_bytes(stored_pw)
        b = password.encode("utf-8")
        if a is None or len(a) == 0:
            return None
        if len(a) != len(b):
            return None
        if secrets.compare_digest(a, b):
            return int(user_id)
        return None

    if conn is not None:
        return _run(conn)

    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        c = psycopg2.connect(dsn)
    else:
        c = psycopg2.connect(
            host=os.environ.get("PGHOST", "localhost"),
            port=int(os.environ.get("PGPORT", "5432")),
            dbname=os.environ.get("PGDATABASE", "hackathon_db"),
            user=os.environ.get("PGUSER", "admin"),
            password=os.environ.get("PGPASSWORD", "demo123"),
        )
    try:
        return _run(c)
    finally:
        c.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        raise SystemExit("usage: python prototype_user_login.py <username> <password>")
    try:
        uid = login_user(sys.argv[1], sys.argv[2])
    except psycopg2.Error as e:
        raise SystemExit(f"database error: {e}")
    print(uid if uid is not None else "login failed")
