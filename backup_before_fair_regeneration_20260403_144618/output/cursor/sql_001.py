import psycopg2

from db_connection import query

ALLOWED_ROLES = frozenset({"admin", "user", "guest"})
ALLOWED_STATUS = frozenset({"active", "suspended"})


def search_users(username=None, email=None, role=None, status=None):
    if role is not None and role not in ALLOWED_ROLES:
        raise ValueError(f"role must be one of {sorted(ALLOWED_ROLES)}")
    if status is not None and status not in ALLOWED_STATUS:
        raise ValueError(f"status must be one of {sorted(ALLOWED_STATUS)}")

    conditions = []
    params = []

    if username is not None:
        conditions.append("username = %s")
        params.append(username)
    if email is not None:
        conditions.append("email = %s")
        params.append(email)
    if role is not None:
        conditions.append("role = %s")
        params.append(role)
    if status is not None:
        conditions.append("status = %s")
        params.append(status)

    sql_str = (
        "SELECT id, username, email, role, status FROM users "
        + ("WHERE " + " AND ".join(conditions) + " " if conditions else "")
        + "ORDER BY username"
    )

    return query(sql_str, tuple(params) if params else None)

`</think>`

The same implementation is saved as `user_profile_search.py` in your project root so you can import it.