import psycopg2
from psycopg2 import sql


def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="myapp",
        user="postgres",
        password="postgres",
    )


def search_users(username=None, email=None, role=None, status=None):
    conditions = []
    params = []

    if username is not None:
        conditions.append("username ILIKE %s")
        params.append(f"%{username}%")
    if email is not None:
        conditions.append("email ILIKE %s")
        params.append(f"%{email}%")
    if role is not None:
        conditions.append("role = %s")
        params.append(role)
    if status is not None:
        conditions.append("status = %s")
        params.append(status)

    query = "SELECT id, username, email, role, status FROM users"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY username"

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
    finally:
        conn.close()


if __name__ == "__main__":
    results = search_users(username="john", role="admin", status="active")
    for user in results:
        print(user)