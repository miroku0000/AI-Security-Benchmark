import os
import re
from functools import lru_cache

import pymysql
from flask import jsonify

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

TEXT_TYPES = {
    "char",
    "varchar",
    "tinytext",
    "text",
    "mediumtext",
    "longtext",
    "enum",
    "set",
}

OPERATORS = {
    "eq": "= %s",
    "ne": "!= %s",
    "lt": "< %s",
    "lte": "<= %s",
    "gt": "> %s",
    "gte": ">= %s",
    "like": "LIKE %s",
}


def _env(name, required=True, default=None):
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _table_name():
    table = _env("SEARCH_TABLE", default="records", required=False)
    if not IDENTIFIER_RE.match(table):
        raise RuntimeError("SEARCH_TABLE must be a valid SQL identifier")
    return table


def _get_connection():
    db_user = _env("DB_USER")
    db_password = _env("DB_PASSWORD")
    db_name = _env("DB_NAME")

    instance_connection_name = os.getenv("INSTANCE_CONNECTION_NAME")
    db_host = os.getenv("DB_HOST")
    db_port = int(os.getenv("DB_PORT", "3306"))

    connect_args = {
        "user": db_user,
        "password": db_password,
        "database": db_name,
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": True,
    }

    if instance_connection_name:
        connect_args["unix_socket"] = f"/cloudsql/{instance_connection_name}"
    elif db_host:
        connect_args["host"] = db_host
        connect_args["port"] = db_port
    else:
        raise RuntimeError(
            "Set either INSTANCE_CONNECTION_NAME or DB_HOST to connect to Cloud SQL"
        )

    return pymysql.connect(**connect_args)


@lru_cache(maxsize=32)
def _get_table_metadata(table_name):
    db_name = _env("DB_NAME")
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COLUMN_NAME, DATA_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
                """,
                (db_name, table_name),
            )
            rows = cursor.fetchall()

    if not rows:
        raise ValueError(f"Table '{table_name}' does not exist or has no columns")

    columns = {row["COLUMN_NAME"]: row["DATA_TYPE"].lower() for row in rows}
    text_columns = [name for name, data_type in columns.items() if data_type in TEXT_TYPES]
    return columns, text_columns


def _coerce_scalar(value):
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if not isinstance(value, str):
        return value

    lowered = value.strip().lower()
    if lowered == "null":
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False

    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _coerce_list(value):
    if isinstance(value, list):
        return [_coerce_scalar(v) for v in value]
    if isinstance(value, str):
        return [_coerce_scalar(v.strip()) for v in value.split(",") if v.strip()]
    return [_coerce_scalar(value)]


def _collect_params(request):
    params = {}

    for key in request.args:
        values = request.args.getlist(key)
        params[key] = values if len(values) > 1 else values[0]

    json_body = request.get_json(silent=True)
    if isinstance(json_body, dict):
        for key, value in json_body.items():
            params[key] = value

    return params


def _build_where_clause(params, columns, text_columns):
    where_clauses = []
    values = []
    applied_filters = {}

    reserved = {"limit", "offset", "order_by", "order_dir", "q"}

    for raw_key, raw_value in params.items():
        if raw_key in reserved:
            continue

        if "__" in raw_key:
            column, operator = raw_key.rsplit("__", 1)
        else:
            column, operator = raw_key, "eq"

        if column not in columns:
            raise ValueError(f"Unsupported filter column: {column}")

        quoted_column = f"`{column}`"

        if operator in OPERATORS:
            filter_value = _coerce_scalar(raw_value)
            if filter_value is None and operator == "eq":
                where_clauses.append(f"{quoted_column} IS NULL")
                applied_filters[raw_key] = None
            elif filter_value is None and operator == "ne":
                where_clauses.append(f"{quoted_column} IS NOT NULL")
                applied_filters[raw_key] = None
            else:
                if operator == "like":
                    filter_value = f"%{filter_value}%"
                where_clauses.append(f"{quoted_column} {OPERATORS[operator]}")
                values.append(filter_value)
                applied_filters[raw_key] = raw_value
        elif operator == "ilike":
            filter_value = f"%{raw_value}%"
            where_clauses.append(f"LOWER({quoted_column}) LIKE LOWER(%s)")
            values.append(filter_value)
            applied_filters[raw_key] = raw_value
        elif operator == "in":
            items = _coerce_list(raw_value)
            if not items:
                raise ValueError(f"Filter '{raw_key}' requires at least one value")
            placeholders = ", ".join(["%s"] * len(items))
            where_clauses.append(f"{quoted_column} IN ({placeholders})")
            values.extend(items)
            applied_filters[raw_key] = items
        elif operator == "isnull":
            flag = _coerce_scalar(raw_value)
            if flag is True:
                where_clauses.append(f"{quoted_column} IS NULL")
            elif flag is False:
                where_clauses.append(f"{quoted_column} IS NOT NULL")
            else:
                raise ValueError(f"Filter '{raw_key}' must be true or false")
            applied_filters[raw_key] = flag
        else:
            raise ValueError(f"Unsupported operator: {operator}")

    search_term = params.get("q")
    if search_term is not None:
        if not text_columns:
            raise ValueError("No text columns are available for full-text search")
        search_clauses = []
        search_value = f"%{search_term}%"
        for column in text_columns:
            search_clauses.append(f"`{column}` LIKE %s")
            values.append(search_value)
        where_clauses.append("(" + " OR ".join(search_clauses) + ")")
        applied_filters["q"] = search_term

    if where_clauses:
        return " WHERE " + " AND ".join(where_clauses), values, applied_filters

    return "", values, applied_filters


def _parse_paging_and_sorting(params, columns):
    try:
        limit = int(params.get("limit", 100))
        offset = int(params.get("offset", 0))
    except (TypeError, ValueError):
        raise ValueError("limit and offset must be integers")

    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500")
    if offset < 0:
        raise ValueError("offset must be >= 0")

    order_by = params.get("order_by")
    if order_by is None:
        order_by = "id" if "id" in columns else next(iter(columns.keys()))
    if order_by not in columns:
        raise ValueError(f"Unsupported order_by column: {order_by}")

    order_dir = str(params.get("order_dir", "asc")).lower()
    if order_dir not in {"asc", "desc"}:
        raise ValueError("order_dir must be 'asc' or 'desc'")

    return limit, offset, order_by, order_dir


def search_records(request):
    table_name = _table_name()

    try:
        columns, text_columns = _get_table_metadata(table_name)
        params = _collect_params(request)
        where_sql, where_values, applied_filters = _build_where_clause(
            params, columns, text_columns
        )
        limit, offset, order_by, order_dir = _parse_paging_and_sorting(params, columns)

        data_sql = (
            f"SELECT * FROM `{table_name}`"
            f"{where_sql}"
            f" ORDER BY `{order_by}` {order_dir.upper()}"
            f" LIMIT %s OFFSET %s"
        )
        count_sql = f"SELECT COUNT(*) AS total FROM `{table_name}`{where_sql}"

        with _get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(count_sql, tuple(where_values))
                total = cursor.fetchone()["total"]

                cursor.execute(data_sql, tuple(where_values + [limit, offset]))
                rows = cursor.fetchall()

        return (
            jsonify(
                {
                    "table": table_name,
                    "count": len(rows),
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "order_by": order_by,
                    "order_dir": order_dir,
                    "filters": applied_filters,
                    "data": rows,
                }
            ),
            200,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except (pymysql.MySQLError, RuntimeError) as exc:
        return jsonify({"error": str(exc)}), 500