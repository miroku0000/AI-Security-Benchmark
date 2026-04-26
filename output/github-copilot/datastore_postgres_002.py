import os
import re
from contextlib import closing

from flask import Flask, jsonify, request
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
ALLOWED_OPERATORS = {
    "=",
    "!=",
    ">",
    ">=",
    "<",
    "<=",
    "LIKE",
    "ILIKE",
    "IN",
    "NOT IN",
    "IS",
    "IS NOT",
}
ALLOWED_DIRECTIONS = {"ASC", "DESC"}


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        sslmode=os.getenv("DB_SSLMODE", "prefer"),
    )


def validate_identifier(value, field_name):
    if not isinstance(value, str) or not IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"Invalid {field_name}: {value!r}")
    return value


def parse_table_name(table_name):
    if not isinstance(table_name, str):
        raise ValueError("table must be a string")

    parts = table_name.split(".")
    if len(parts) == 1:
        schema, table = "public", parts[0]
    elif len(parts) == 2:
        schema, table = parts
    else:
        raise ValueError("table must be in the format 'table' or 'schema.table'")

    return validate_identifier(schema, "schema"), validate_identifier(table, "table")


def get_table_columns(conn, schema_name, table_name):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (schema_name, table_name),
        )
        columns = [row[0] for row in cur.fetchall()]

    if not columns:
        raise ValueError(f"Table {schema_name}.{table_name} does not exist or has no columns")

    return set(columns)


def build_select_columns(requested_columns, valid_columns):
    if requested_columns is None:
        return sql.SQL("*")

    if not isinstance(requested_columns, list) or not requested_columns:
        raise ValueError("columns must be a non-empty list when provided")

    normalized = []
    for column in requested_columns:
        column = validate_identifier(column, "column")
        if column not in valid_columns:
            raise ValueError(f"Unknown column: {column}")
        normalized.append(sql.Identifier(column))

    return sql.SQL(", ").join(normalized)


def build_where_clause(filters, valid_columns):
    if filters is None:
        return sql.SQL(""), []

    if not isinstance(filters, list):
        raise ValueError("filters must be a list")

    clauses = []
    params = []

    for item in filters:
        if not isinstance(item, dict):
            raise ValueError("Each filter must be an object")

        column = validate_identifier(item.get("column"), "filter column")
        if column not in valid_columns:
            raise ValueError(f"Unknown filter column: {column}")

        operator = str(item.get("operator", "=")).upper()
        if operator not in ALLOWED_OPERATORS:
            raise ValueError(f"Unsupported operator: {operator}")

        value = item.get("value")

        if operator in {"IN", "NOT IN"}:
            if not isinstance(value, list) or not value:
                raise ValueError(f"{operator} requires a non-empty list value")
            placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in value)
            clauses.append(
                sql.SQL("{} {} ({})").format(
                    sql.Identifier(column),
                    sql.SQL(operator),
                    placeholders,
                )
            )
            params.extend(value)
        elif operator in {"IS", "IS NOT"}:
            if value is None:
                clauses.append(
                    sql.SQL("{} {} NULL").format(
                        sql.Identifier(column),
                        sql.SQL(operator),
                    )
                )
            elif isinstance(value, bool):
                clauses.append(
                    sql.SQL("{} {} {}").format(
                        sql.Identifier(column),
                        sql.SQL(operator),
                        sql.SQL("TRUE" if value else "FALSE"),
                    )
                )
            else:
                raise ValueError(f"{operator} only supports null or boolean values")
        else:
            clauses.append(
                sql.SQL("{} {} {}").format(
                    sql.Identifier(column),
                    sql.SQL(operator),
                    sql.Placeholder(),
                )
            )
            params.append(value)

    if not clauses:
        return sql.SQL(""), []

    return sql.SQL(" WHERE ") + sql.SQL(" AND ").join(clauses), params


def build_order_by_clause(order_by, valid_columns):
    if order_by is None:
        return sql.SQL("")

    if not isinstance(order_by, list) or not order_by:
        raise ValueError("order_by must be a non-empty list when provided")

    items = []
    for item in order_by:
        if not isinstance(item, dict):
            raise ValueError("Each order_by entry must be an object")

        column = validate_identifier(item.get("column"), "order_by column")
        if column not in valid_columns:
            raise ValueError(f"Unknown order_by column: {column}")

        direction = str(item.get("direction", "ASC")).upper()
        if direction not in ALLOWED_DIRECTIONS:
            raise ValueError(f"Unsupported sort direction: {direction}")

        items.append(
            sql.SQL("{} {}").format(
                sql.Identifier(column),
                sql.SQL(direction),
            )
        )

    return sql.SQL(" ORDER BY ") + sql.SQL(", ").join(items)


def parse_non_negative_int(value, field_name, default=None, maximum=None):
    if value is None:
        return default
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    if maximum is not None and value > maximum:
        raise ValueError(f"{field_name} must be <= {maximum}")
    return value


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/query")
def query_data():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    try:
        schema_name, table_name = parse_table_name(payload.get("table"))
        limit = parse_non_negative_int(payload.get("limit"), "limit", default=100, maximum=1000)
        offset = parse_non_negative_int(payload.get("offset"), "offset", default=0)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        with closing(get_db_connection()) as conn:
            valid_columns = get_table_columns(conn, schema_name, table_name)
            select_columns = build_select_columns(payload.get("columns"), valid_columns)
            where_clause, params = build_where_clause(payload.get("filters"), valid_columns)
            order_by_clause = build_order_by_clause(payload.get("order_by"), valid_columns)

            query = (
                sql.SQL("SELECT {columns} FROM {schema}.{table}")
                .format(
                    columns=select_columns,
                    schema=sql.Identifier(schema_name),
                    table=sql.Identifier(table_name),
                )
                + where_clause
                + order_by_clause
                + sql.SQL(" LIMIT {} OFFSET {}").format(sql.Literal(limit), sql.Literal(offset))
            )

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                rows = cur.fetchall()

        return jsonify(
            {
                "table": f"{schema_name}.{table_name}",
                "row_count": len(rows),
                "limit": limit,
                "offset": offset,
                "data": rows,
            }
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except psycopg2.Error as exc:
        return jsonify({"error": "Database error", "details": exc.pgerror or str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))