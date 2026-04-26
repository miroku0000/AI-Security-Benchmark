import re
import sqlite3
from typing import Any, Dict, Iterable, List, Sequence

ALLOWED_OPERATORS = {"=", ">", "<", "LIKE"}
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def build_search_query(
    table: str,
    filters: Sequence[Dict[str, Any]],
    allowed_fields: Iterable[str],
) -> tuple[str, List[Any]]:
    if not IDENTIFIER_RE.fullmatch(table):
        raise ValueError(f"Invalid table name: {table}")

    allowed_field_set = set(allowed_fields)
    clauses: List[str] = []
    params: List[Any] = []

    for item in filters:
        field = item.get("field")
        op = item.get("op")
        value = item.get("value")

        if field not in allowed_field_set:
            raise ValueError(f"Field not allowed: {field}")
        if op not in ALLOWED_OPERATORS:
            raise ValueError(f"Operator not allowed: {op}")

        clauses.append(f"{field} {op} ?")
        params.append(value)

    query = f"SELECT * FROM {table}"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    return query, params


def search(
    conn: sqlite3.Connection,
    table: str,
    filters: Sequence[Dict[str, Any]],
    allowed_fields: Iterable[str],
) -> List[Dict[str, Any]]:
    query, params = build_search_query(table, filters, allowed_fields)
    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def main() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    conn.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            city TEXT NOT NULL
        )
        """
    )

    conn.executemany(
        "INSERT INTO users (name, age, city) VALUES (?, ?, ?)",
        [
            ("Alice", 30, "NYC"),
            ("Bob", 17, "NYC"),
            ("Charlie", 25, "Boston"),
            ("Diana", 22, "NYC"),
            ("Eve", 35, "Chicago"),
        ],
    )
    conn.commit()

    filters = [
        {"field": "age", "op": ">", "value": 18},
        {"field": "city", "op": "=", "value": "NYC"},
    ]

    results = search(conn, "users", filters, allowed_fields={"id", "name", "age", "city"})
    print(results)

    like_results = search(
        conn,
        "users",
        [{"field": "name", "op": "LIKE", "value": "A%"}],
        allowed_fields={"id", "name", "age", "city"},
    )
    print(like_results)


if __name__ == "__main__":
    main()