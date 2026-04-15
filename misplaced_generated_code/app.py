import os
import re
from flask import Flask, request, jsonify
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

IDENT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def validate_ident(name):
    if not isinstance(name, str) or not IDENT_RE.match(name):
        raise ValueError("invalid identifier")


def get_conn():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=int(os.environ.get("PGPORT", "5432")),
        dbname=os.environ.get("PGDATABASE", "postgres"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", ""),
    )


ALLOWED_OPS = frozenset({"=", "!=", "<>", "<", ">", "<=", ">=", "LIKE", "ILIKE"})


@app.post("/query")
def dynamic_query():
    data = request.get_json(silent=True) or {}
    table = data.get("table")
    if not table:
        return jsonify({"error": "table is required"}), 400
    try:
        validate_ident(table)
    except ValueError:
        return jsonify({"error": "invalid table name"}), 400

    columns = data.get("columns")
    if columns is not None:
        if not isinstance(columns, list) or not columns:
            return jsonify({"error": "columns must be a non-empty list, or omit for *"}), 400
        try:
            for c in columns:
                validate_ident(c)
        except ValueError:
            return jsonify({"error": "invalid column name"}), 400
        select_parts = sql.SQL(", ").join(sql.Identifier(c) for c in columns)
    else:
        select_parts = sql.SQL("*")

    base = sql.SQL("SELECT {} FROM {}").format(select_parts, sql.Identifier(table))

    params = []
    conditions = []
    filters = data.get("filters")

    if isinstance(filters, dict):
        for col, val in filters.items():
            try:
                validate_ident(col)
            except ValueError:
                return jsonify({"error": "invalid filter column"}), 400
            conditions.append(
                sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder())
            )
            params.append(val)
    elif isinstance(filters, list):
        for item in filters:
            if not isinstance(item, dict):
                return jsonify({"error": "each filter must be an object"}), 400
            col = item.get("column")
            op = str(item.get("op", "=")).upper()
            if op not in ALLOWED_OPS:
                return jsonify({"error": "unsupported operator"}), 400
            val = item.get("value")
            try:
                validate_ident(col)
            except ValueError:
                return jsonify({"error": "invalid filter column"}), 400
            conditions.append(
                sql.SQL("{} {} {}").format(
                    sql.Identifier(col), sql.SQL(op), sql.Placeholder()
                )
            )
            params.append(val)

    if conditions:
        base = sql.SQL("{} WHERE {}").format(base, sql.SQL(" AND ").join(conditions))

    order_by = data.get("order_by")
    if order_by is not None:
        if not isinstance(order_by, list) or not order_by:
            return jsonify({"error": "order_by must be a non-empty list"}), 400
        ob_parts = []
        for entry in order_by:
            if isinstance(entry, str):
                col = entry
                direction = "ASC"
            elif isinstance(entry, dict):
                col = entry.get("column")
                direction = str(entry.get("direction", "ASC")).upper()
            else:
                return jsonify({"error": "invalid order_by entry"}), 400
            if direction not in ("ASC", "DESC"):
                return jsonify({"error": "invalid sort direction"}), 400
            try:
                validate_ident(col)
            except ValueError:
                return jsonify({"error": "invalid order_by column"}), 400
            ob_parts.append(
                sql.SQL("{} {}").format(sql.Identifier(col), sql.SQL(direction))
            )
        base = sql.SQL("{} ORDER BY {}").format(base, sql.SQL(", ").join(ob_parts))

    try:
        limit = int(data.get("limit", 1000))
    except (TypeError, ValueError):
        return jsonify({"error": "limit must be an integer"}), 400
    limit = max(1, min(limit, 10000))
    base = sql.SQL("{} LIMIT {}").format(base, sql.Literal(limit))

    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(base, params)
                rows = [dict(r) for r in cur.fetchall()]
        return jsonify(rows)
    except psycopg2.Error as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
