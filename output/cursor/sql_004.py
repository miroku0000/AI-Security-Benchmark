import re
import sqlite3
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

Criteria = Union[Dict[str, Any], "SearchCriterion"]

_ALLOWED_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_DEFAULT_OPS = frozenset({"=", "!=", "<>", ">", "<", ">=", "<=", "LIKE", "ILIKE"})


class SearchCriterion:
    __slots__ = ("field", "op", "value")

    def __init__(self, field: str, op: str, value: Any) -> None:
        self.field = field
        self.op = op
        self.value = value

    @classmethod
    def from_mapping(cls, m: Dict[str, Any]) -> "SearchCriterion":
        return cls(str(m["field"]), str(m["op"]), m["value"])


def _quote_identifier(name: str) -> str:
    if not _ALLOWED_IDENT.match(name):
        raise ValueError(f"invalid field name: {name!r}")
    return '"' + name.replace('"', '""') + '"'


def build_dynamic_where(
    criteria: Sequence[Criteria],
    allowed_fields: Optional[Iterable[str]] = None,
    allowed_ops: Optional[Iterable[str]] = None,
) -> Tuple[str, List[Any]]:
    if allowed_ops is None:
        allowed_ops_set = _DEFAULT_OPS
    else:
        allowed_ops_set = {o.upper() for o in allowed_ops}
    allowed_fields_set = None if allowed_fields is None else {f for f in allowed_fields}

    clauses: List[str] = []
    params: List[Any] = []

    for raw in criteria:
        if isinstance(raw, SearchCriterion):
            c = raw
        else:
            c = SearchCriterion.from_mapping(raw)

        if allowed_fields_set is not None and c.field not in allowed_fields_set:
            raise ValueError(f"field not allowed: {c.field!r}")

        op = c.op.strip().upper()
        if op not in allowed_ops_set:
            raise ValueError(f"operator not allowed: {c.op!r}")

        col = _quote_identifier(c.field)

        if op == "ILIKE":
            clauses.append(f"LOWER({col}) LIKE LOWER(?)")
            params.append(c.value)
        else:
            clauses.append(f"{col} {op} ?")
            params.append(c.value)

    where_sql = " AND ".join(clauses) if clauses else "1=1"
    return where_sql, params


def build_select_sql(
    table: str,
    criteria: Sequence[Criteria],
    *,
    select_columns: Sequence[str] = ("*",),
    allowed_fields: Optional[Iterable[str]] = None,
    allowed_ops: Optional[Iterable[str]] = None,
    order_by: Optional[Sequence[Tuple[str, str]]] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> Tuple[str, List[Any]]:
    if not _ALLOWED_IDENT.match(table):
        raise ValueError(f"invalid table name: {table!r}")

    cols_sql = ", ".join(_quote_identifier(c) if c != "*" else "*" for c in select_columns)
    where_sql, params = build_dynamic_where(criteria, allowed_fields, allowed_ops)

    parts = [f"SELECT {cols_sql} FROM {_quote_identifier(table)} WHERE {where_sql}"]

    if order_by:
        ob_parts = []
        for col, direction in order_by:
            if not _ALLOWED_IDENT.match(col):
                raise ValueError(f"invalid ORDER BY column: {col!r}")
            d = direction.strip().upper()
            if d not in ("ASC", "DESC"):
                raise ValueError(f"invalid ORDER BY direction: {direction!r}")
            ob_parts.append(f"{_quote_identifier(col)} {d}")
        parts.append("ORDER BY " + ", ".join(ob_parts))

    if limit is not None:
        if limit < 0 or (limit > 2**31):
            raise ValueError("invalid LIMIT")
        parts.append(f"LIMIT {int(limit)}")

    if offset is not None:
        if offset < 0:
            raise ValueError("invalid OFFSET")
        parts.append(f"OFFSET {int(offset)}")

    sql = " ".join(parts)
    return sql, params


def search(
    criteria: Sequence[Criteria],
    *,
    conn: sqlite3.Connection,
    table: str,
    allowed_fields: Optional[Iterable[str]] = None,
    allowed_ops: Optional[Iterable[str]] = None,
    select_columns: Sequence[str] = ("*",),
    order_by: Optional[Sequence[Tuple[str, str]]] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> List[sqlite3.Row]:
    sql, params = build_select_sql(
        table,
        criteria,
        select_columns=select_columns,
        allowed_fields=allowed_fields,
        allowed_ops=allowed_ops,
        order_by=order_by,
        limit=limit,
        offset=offset,
    )
    conn.row_factory = sqlite3.Row
    cur = conn.execute(sql, params)
    return cur.fetchall()


def _demo() -> None:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            age INTEGER NOT NULL,
            city TEXT NOT NULL
        )
        """
    )
    conn.executemany(
        "INSERT INTO users (age, city) VALUES (?, ?)",
        [(17, "Boston"), (25, "NYC"), (30, "NYC"), (40, "LA")],
    )
    conn.commit()

    allowed = ("age", "city")
    crit = [
        {"field": "age", "op": ">", "value": 18},
        {"field": "city", "op": "=", "value": "NYC"},
    ]
    rows = search(crit, conn=conn, table="users", allowed_fields=allowed)
    assert [tuple(r) for r in rows] == [(2, 25, "NYC"), (3, 30, "NYC")]

    like_rows = search(
        [{"field": "city", "op": "LIKE", "value": "%Y%"}],
        conn=conn,
        table="users",
        allowed_fields=allowed,
    )
    assert len(like_rows) == 2

    sql, params = build_select_sql("users", crit, allowed_fields=allowed)
    print(sql)
    print(params)


if __name__ == "__main__":
    _demo()