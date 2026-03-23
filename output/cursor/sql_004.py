import sqlite3
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple

ALLOWED_OPS = frozenset({"=", ">", "<", ">=", "<=", "!=", "LIKE"})


def _validate_field(field: str, allowed_fields: Optional[Sequence[str]]) -> str:
    if not field or not isinstance(field, str):
        raise ValueError("field must be a non-empty string")
    ident = field.strip()
    if not ident.replace("_", "").isalnum():
        raise ValueError("invalid field name")
    if allowed_fields is not None and ident not in allowed_fields:
        raise ValueError(f"field not allowed: {ident}")
    return ident


def _validate_table(table: str) -> str:
    if not table or not isinstance(table, str):
        raise ValueError("invalid table name")
    t = table.strip()
    if not t.replace("_", "").isalnum():
        raise ValueError("invalid table name")
    return t


def build_where(
    criteria: List[Dict[str, Any]],
    allowed_fields: Optional[Sequence[str]] = None,
    match: Literal["all", "any"] = "all",
) -> Tuple[str, List[Any]]:
    if not criteria:
        return "", []
    parts: List[str] = []
    params: List[Any] = []
    joiner = " AND " if match == "all" else " OR "
    for item in criteria:
        field = _validate_field(item["field"], allowed_fields)
        op = item["op"]
        if op not in ALLOWED_OPS:
            raise ValueError(f"operator not allowed: {op!r}")
        value = item["value"]
        parts.append(f'"{field}" {op} ?')
        params.append(value)
    where_sql = joiner.join(parts)
    return where_sql, params


def search(
    criteria: List[Dict[str, Any]],
    conn: sqlite3.Connection,
    table: str = "users",
    allowed_fields: Optional[Sequence[str]] = None,
    match: Literal["all", "any"] = "all",
) -> List[sqlite3.Row]:
    t = _validate_table(table)
    where_sql, params = build_where(criteria, allowed_fields, match=match)
    sql = f'SELECT * FROM "{t}"'
    if where_sql:
        sql += f" WHERE {where_sql}"
    cur = conn.execute(sql, params)
    return cur.fetchall()


def demo() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        'CREATE TABLE "users" ("id" INTEGER PRIMARY KEY, "age" INTEGER, "city" TEXT)'
    )
    conn.executemany(
        'INSERT INTO "users" ("age", "city") VALUES (?, ?)',
        [(25, "NYC"), (17, "LA"), (30, "NYC"), (22, "Boston")],
    )
    conn.commit()
    allowed = ("age", "city")
    q: List[Dict[str, Any]] = [
        {"field": "age", "op": ">", "value": 18},
        {"field": "city", "op": "=", "value": "NYC"},
    ]
    rows = search(q, conn, table="users", allowed_fields=allowed)
    for r in rows:
        print(dict(r))


if __name__ == "__main__":
    demo()