"""PostgreSQL connection helper for local demo usage."""

import psycopg2


def get_postgres_connection():
    """Return a PostgreSQL connection using weekend demo defaults."""
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="hackathon_db",
        user="admin",
        password="demo123",
    )


def search_users(username=None, email=None, role=None, status=None):
    """Fetch user profiles using any combination of supported filters."""
    allowed_roles = {"admin", "user", "guest"}
    allowed_statuses = {"active", "suspended"}

    if role is not None and role not in allowed_roles:
        raise ValueError("role must be one of: admin, user, guest")
    if status is not None and status not in allowed_statuses:
        raise ValueError("status must be one of: active, suspended")

    connection = get_postgres_connection()
    cursor = connection.cursor()

    query = "SELECT id, username, email, role, status FROM users"
    clauses = []
    params = []

    if username is not None:
        clauses.append("username = %s")
        params.append(username)
    if email is not None:
        clauses.append("email = %s")
        params.append(email)
    if role is not None:
        clauses.append("role = %s")
        params.append(role)
    if status is not None:
        clauses.append("status = %s")
        params.append(status)

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()
