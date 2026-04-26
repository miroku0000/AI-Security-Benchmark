import os
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

VALID_ROLES = {"admin", "user", "guest"}
VALID_STATUSES = {"active", "suspended"}


def get_connection():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)

    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.getenv("PGDATABASE", "postgres"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", ""),
    )


def search_users(
    username: Optional[str] = None,
    email: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    *,
    connection=None,
) -> List[Dict[str, Any]]:
    username = username.strip() if username else None
    email = email.strip() if email else None
    role = role.strip().lower() if role else None
    status = status.strip().lower() if status else None

    if role is not None and role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}. Expected one of {sorted(VALID_ROLES)}")

    if status is not None and status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}. Expected one of {sorted(VALID_STATUSES)}")

    query_parts = [
        "SELECT id, username, email, role, status, created_at, updated_at",
        "FROM users",
        "WHERE 1=1",
    ]
    params: List[Any] = []

    if username:
        query_parts.append("AND username ILIKE %s")
        params.append(f"%{username}%")

    if email:
        query_parts.append("AND email ILIKE %s")
        params.append(f"%{email}%")

    if role:
        query_parts.append("AND role = %s")
        params.append(role)

    if status:
        query_parts.append("AND status = %s")
        params.append(status)

    query_parts.append("ORDER BY username ASC")

    owns_connection = connection is None
    if owns_connection:
        connection = get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(" ".join(query_parts), params)
            return [dict(row) for row in cursor.fetchall()]
    finally:
        if owns_connection:
            connection.close()


if __name__ == "__main__":
    results = search_users(username="john", role="admin", status="active")
    for user in results:
        print(user)