import os
import json
import decimal
from datetime import date, datetime

import pymysql


DB_CONFIG = {
    "host": os.environ["DB_HOST"],
    "port": int(os.environ.get("DB_PORT", "3306")),
    "user": os.environ["DB_USER"],
    "password": os.environ["DB_PASSWORD"],
    "database": os.environ["DB_NAME"],
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "connect_timeout": int(os.environ.get("DB_CONNECT_TIMEOUT", "5")),
    "read_timeout": int(os.environ.get("DB_READ_TIMEOUT", "10")),
    "write_timeout": int(os.environ.get("DB_WRITE_TIMEOUT", "10")),
    "autocommit": True,
}

PRODUCTS_TABLE = os.environ.get("PRODUCTS_TABLE", "products")
DEFAULT_LIMIT = int(os.environ.get("DEFAULT_LIMIT", "25"))
MAX_LIMIT = int(os.environ.get("MAX_LIMIT", "100"))

ALLOWED_SELECT_COLUMNS = {
    "id",
    "sku",
    "name",
    "description",
    "category",
    "brand",
    "price",
    "currency",
    "stock_quantity",
    "is_active",
    "created_at",
    "updated_at",
}

ALLOWED_SORT_COLUMNS = {
    "id": "id",
    "name": "name",
    "price": "price",
    "created_at": "created_at",
    "updated_at": "updated_at",
    "stock_quantity": "stock_quantity",
    "brand": "brand",
    "category": "category",
}

DEFAULT_SELECT_COLUMNS = [
    "id",
    "sku",
    "name",
    "description",
    "category",
    "brand",
    "price",
    "currency",
    "stock_quantity",
    "is_active",
    "created_at",
    "updated_at",
]


def lambda_handler(event, context):
    try:
        params = extract_params(event)
        select_columns = parse_fields(params.get("fields"))
        limit = clamp_int(params.get("limit"), DEFAULT_LIMIT, 1, MAX_LIMIT)
        page = clamp_int(params.get("page"), 1, 1, 1000000)
        offset = (page - 1) * limit
        sort_by = ALLOWED_SORT_COLUMNS.get(str(params.get("sort_by", "created_at")), "created_at")
        sort_order = "ASC" if str(params.get("sort_order", "desc")).lower() == "asc" else "DESC"

        where_clauses = []
        query_params = []

        ids = parse_csv_list(params.get("ids"))
        if ids:
            placeholders = ", ".join(["%s"] * len(ids))
            where_clauses.append(f"id IN ({placeholders})")
            query_params.extend([parse_int(item, "ids") for item in ids])

        category = params.get("category")
        if category:
            where_clauses.append("category = %s")
            query_params.append(str(category))

        brand = params.get("brand")
        if brand:
            where_clauses.append("brand = %s")
            query_params.append(str(brand))

        sku = params.get("sku")
        if sku:
            where_clauses.append("sku = %s")
            query_params.append(str(sku))

        active = parse_optional_bool(params.get("active"))
        if active is not None:
            where_clauses.append("is_active = %s")
            query_params.append(1 if active else 0)

        in_stock = parse_optional_bool(params.get("in_stock"))
        if in_stock is not None:
            if in_stock:
                where_clauses.append("stock_quantity > %s")
                query_params.append(0)
            else:
                where_clauses.append("stock_quantity <= %s")
                query_params.append(0)

        min_price = params.get("min_price")
        if min_price not in (None, ""):
            where_clauses.append("price >= %s")
            query_params.append(parse_decimal(min_price, "min_price"))

        max_price = params.get("max_price")
        if max_price not in (None, ""):
            where_clauses.append("price <= %s")
            query_params.append(parse_decimal(max_price, "max_price"))

        min_stock = params.get("min_stock")
        if min_stock not in (None, ""):
            where_clauses.append("stock_quantity >= %s")
            query_params.append(parse_int(min_stock, "min_stock"))

        max_stock = params.get("max_stock")
        if max_stock not in (None, ""):
            where_clauses.append("stock_quantity <= %s")
            query_params.append(parse_int(max_stock, "max_stock"))

        q = first_non_empty(params.get("q"), params.get("query"), params.get("search"))
        if q:
            like_value = f"%{q.strip()}%"
            search_fields = parse_search_fields(params.get("search_fields"))
            search_conditions = [f"{field} LIKE %s" for field in search_fields]
            where_clauses.append("(" + " OR ".join(search_conditions) + ")")
            query_params.extend([like_value] * len(search_fields))

        where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        select_sql = ", ".join(select_columns)

        data_sql = (
            f"SELECT {select_sql} "
            f"FROM {PRODUCTS_TABLE}"
            f"{where_sql} "
            f"ORDER BY {sort_by} {sort_order} "
            f"LIMIT %s OFFSET %s"
        )
        data_params = query_params + [limit, offset]

        count_sql = f"SELECT COUNT(*) AS total FROM {PRODUCTS_TABLE}{where_sql}"

        with pymysql.connect(**DB_CONFIG) as connection:
            with connection.cursor() as cursor:
                cursor.execute(count_sql, query_params)
                total = int(cursor.fetchone()["total"])

                cursor.execute(data_sql, data_params)
                items = cursor.fetchall()

        return response(
            200,
            {
                "items": items,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "returned": len(items),
                    "total": total,
                    "total_pages": (total + limit - 1) // limit if total else 0,
                },
                "filters": {
                    "q": q,
                    "category": category,
                    "brand": brand,
                    "sku": sku,
                    "active": active,
                    "in_stock": in_stock,
                    "min_price": min_price,
                    "max_price": max_price,
                    "min_stock": min_stock,
                    "max_stock": max_stock,
                    "ids": ids,
                    "sort_by": sort_by,
                    "sort_order": sort_order,
                    "fields": select_columns,
                },
            },
        )
    except ValueError as exc:
        return response(400, {"error": "BadRequest", "message": str(exc)})
    except KeyError as exc:
        return response(500, {"error": "ConfigurationError", "message": f"Missing environment variable: {exc.args[0]}"})
    except pymysql.MySQLError as exc:
        return response(500, {"error": "DatabaseError", "message": str(exc)})
    except Exception as exc:
        return response(500, {"error": "InternalServerError", "message": str(exc)})


def extract_params(event):
    params = {}

    if isinstance(event, dict):
        qs = event.get("queryStringParameters") or {}
        if isinstance(qs, dict):
            params.update(qs)

        mqs = event.get("multiValueQueryStringParameters") or {}
        if isinstance(mqs, dict):
            for key, value in mqs.items():
                if isinstance(value, list) and value:
                    params[key] = ",".join(str(v) for v in value if v is not None)

        body = event.get("body")
        if body:
            parsed_body = parse_body(body, event.get("isBase64Encoded", False))
            if isinstance(parsed_body, dict):
                params.update({k: v for k, v in parsed_body.items() if v is not None})

        path_params = event.get("pathParameters") or {}
        if isinstance(path_params, dict):
            params.update({k: v for k, v in path_params.items() if v is not None})

    return params


def parse_body(body, is_base64_encoded):
    if is_base64_encoded:
        import base64
        body = base64.b64decode(body).decode("utf-8")
    if isinstance(body, str):
        body = body.strip()
        if not body:
            return {}
        return json.loads(body)
    if isinstance(body, dict):
        return body
    return {}


def parse_fields(value):
    if not value:
        return DEFAULT_SELECT_COLUMNS

    fields = []
    for field in parse_csv_list(value):
        if field not in ALLOWED_SELECT_COLUMNS:
            raise ValueError(f"Unsupported field: {field}")
        fields.append(field)

    if not fields:
        return DEFAULT_SELECT_COLUMNS
    return fields


def parse_search_fields(value):
    default_fields = ["name", "description", "category", "brand", "sku"]
    if not value:
        return default_fields

    fields = []
    for field in parse_csv_list(value):
        if field not in {"name", "description", "category", "brand", "sku"}:
            raise ValueError(f"Unsupported search field: {field}")
        fields.append(field)

    return fields or default_fields


def parse_csv_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = str(value).split(",")
    return [str(item).strip() for item in items if str(item).strip()]


def parse_optional_bool(value):
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")


def clamp_int(value, default, minimum, maximum):
    if value in (None, ""):
        return default
    parsed = parse_int(value, "integer")
    if parsed < minimum:
        return minimum
    if parsed > maximum:
        return maximum
    return parsed


def parse_int(value, field_name):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"Invalid integer for {field_name}: {value}")


def parse_decimal(value, field_name):
    try:
        return decimal.Decimal(str(value).strip())
    except (decimal.InvalidOperation, TypeError, ValueError):
        raise ValueError(f"Invalid decimal for {field_name}: {value}")


def first_non_empty(*values):
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def json_default(value):
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "OPTIONS,GET,POST",
        },
        "body": json.dumps(body, default=json_default),
    }