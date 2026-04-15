import os
import json
import decimal
import base64
import re
from datetime import date, datetime

import pymysql


_DB_CONN = None


class _DecimalJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def _get_env(name, default=None, required=False):
    val = os.environ.get(name, default)
    if required and (val is None or str(val).strip() == ""):
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


def _get_connection():
    global _DB_CONN
    if _DB_CONN is not None:
        try:
            _DB_CONN.ping(reconnect=True)
            return _DB_CONN
        except Exception:
            _DB_CONN = None

    host = _get_env("DB_HOST", required=True)
    user = _get_env("DB_USER", required=True)
    password = _get_env("DB_PASSWORD", required=True)
    db = _get_env("DB_NAME", required=True)
    port = int(_get_env("DB_PORT", "3306") or 3306)

    connect_timeout = int(_get_env("DB_CONNECT_TIMEOUT", "5") or 5)
    read_timeout = int(_get_env("DB_READ_TIMEOUT", "10") or 10)
    write_timeout = int(_get_env("DB_WRITE_TIMEOUT", "10") or 10)

    _DB_CONN = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=db,
        port=port,
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
        write_timeout=write_timeout,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        ssl={"ssl": {}} if (_get_env("DB_SSL", "false").lower() in ("1", "true", "yes")) else None,
    )
    return _DB_CONN


def _is_truthy(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("1", "true", "t", "yes", "y", "on"):
        return True
    if s in ("0", "false", "f", "no", "n", "off"):
        return False
    return None


def _to_int(v, default=None, min_value=None, max_value=None):
    try:
        iv = int(v)
    except Exception:
        return default
    if min_value is not None and iv < min_value:
        iv = min_value
    if max_value is not None and iv > max_value:
        iv = max_value
    return iv


def _to_decimal(v, default=None):
    if v is None:
        return default
    try:
        return decimal.Decimal(str(v))
    except Exception:
        return default


def _normalize_query_params(event):
    qp = event.get("queryStringParameters") or {}
    mqp = event.get("multiValueQueryStringParameters") or {}

    out = {}
    keys = set(qp.keys()) | set(mqp.keys())
    for k in keys:
        if k in qp and qp[k] is not None:
            out[k] = qp[k]
        elif k in mqp and mqp[k]:
            out[k] = mqp[k][0]

    body = event.get("body")
    if body:
        try:
            if event.get("isBase64Encoded"):
                body = base64.b64decode(body).decode("utf-8", errors="replace")
            data = json.loads(body)
            if isinstance(data, dict):
                for k, v in data.items():
                    if k not in out and v is not None:
                        out[k] = v
        except Exception:
            pass

    return out


def _response(status_code, payload, origin="*"):
    return {
        "statusCode": int(status_code),
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps(payload, cls=_DecimalJSONEncoder, ensure_ascii=False),
    }


def _allowed_origin(event):
    allowed = _get_env("CORS_ALLOW_ORIGINS", "*")
    if allowed.strip() == "*":
        return "*"
    req_origin = (event.get("headers") or {}).get("origin") or (event.get("headers") or {}).get("Origin")
    if not req_origin:
        return allowed.split(",")[0].strip()
    allow_set = {o.strip() for o in allowed.split(",") if o.strip()}
    return req_origin if req_origin in allow_set else allow_set.pop() if allow_set else "*"


def _parse_sort(sort_raw, order_raw):
    sort_map = {
        "relevance": None,
        "name": "p.name",
        "price": "p.price",
        "created_at": "p.created_at",
        "updated_at": "p.updated_at",
    }

    sort_key = (str(sort_raw).strip().lower() if sort_raw is not None else "relevance")
    if sort_key not in sort_map:
        sort_key = "relevance"

    order = (str(order_raw).strip().lower() if order_raw is not None else "desc")
    if order not in ("asc", "desc"):
        order = "desc"

    return sort_key, sort_map[sort_key], order


def _escape_like(s):
    s = str(s)
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _build_query(params):
    select_cols = [
        "p.id",
        "p.sku",
        "p.name",
        "p.description",
        "p.category",
        "p.price",
        "p.currency",
        "p.in_stock",
        "p.created_at",
        "p.updated_at",
    ]

    sql = f"SELECT {', '.join(select_cols)} FROM products p"
    where = []
    args = []
    score_expr = None

    q = params.get("q")
    if q is not None and str(q).strip() != "":
        q_str = str(q).strip()
        q_like = f"%{_escape_like(q_str)}%"
        where.append("(p.name LIKE %s ESCAPE '\\\\' OR p.description LIKE %s ESCAPE '\\\\' OR p.sku LIKE %s ESCAPE '\\\\')")
        args.extend([q_like, q_like, q_like])
        score_expr = (
            "((CASE WHEN p.name LIKE %s ESCAPE '\\\\' THEN 4 ELSE 0 END) + "
            "(CASE WHEN p.sku LIKE %s ESCAPE '\\\\' THEN 3 ELSE 0 END) + "
            "(CASE WHEN p.description LIKE %s ESCAPE '\\\\' THEN 1 ELSE 0 END))"
        )
        args_for_score = [q_like, q_like, q_like]
    else:
        args_for_score = []

    category = params.get("category")
    if category is not None and str(category).strip() != "":
        where.append("p.category = %s")
        args.append(str(category).strip())

    sku = params.get("sku")
    if sku is not None and str(sku).strip() != "":
        where.append("p.sku = %s")
        args.append(str(sku).strip())

    product_id = params.get("id")
    if product_id is not None and str(product_id).strip() != "":
        pid = _to_int(product_id, default=None, min_value=1)
        if pid is not None:
            where.append("p.id = %s")
            args.append(pid)

    min_price = _to_decimal(params.get("min_price"), default=None)
    if min_price is not None:
        where.append("p.price >= %s")
        args.append(min_price)

    max_price = _to_decimal(params.get("max_price"), default=None)
    if max_price is not None:
        where.append("p.price <= %s")
        args.append(max_price)

    in_stock = _is_truthy(params.get("in_stock"))
    if in_stock is not None:
        where.append("p.in_stock = %s")
        args.append(1 if in_stock else 0)

    currency = params.get("currency")
    if currency is not None and str(currency).strip() != "":
        where.append("p.currency = %s")
        args.append(str(currency).strip().upper())

    if where:
        sql += " WHERE " + " AND ".join(where)

    sort_key, sort_col, order = _parse_sort(params.get("sort"), params.get("order"))

    if sort_key == "relevance" and score_expr is not None:
        sql = sql.replace("SELECT ", f"SELECT {score_expr} AS _score, ", 1)
        args = args_for_score + args
        sql += " ORDER BY _score DESC, p.updated_at DESC, p.id DESC"
    elif sort_col is not None:
        sql += f" ORDER BY {sort_col} {order}, p.id ASC"
    else:
        sql += " ORDER BY p.updated_at DESC, p.id DESC"

    limit_default = _to_int(_get_env("DEFAULT_LIMIT", "25"), default=25, min_value=1, max_value=200)
    limit_max = _to_int(_get_env("MAX_LIMIT", "100"), default=100, min_value=1, max_value=500)
    limit = _to_int(params.get("limit"), default=limit_default, min_value=1, max_value=limit_max)
    offset = _to_int(params.get("offset"), default=0, min_value=0, max_value=1000000)

    sql += " LIMIT %s OFFSET %s"
    args.extend([limit, offset])

    count_sql = "SELECT COUNT(1) AS total FROM products p"
    if where:
        count_sql += " WHERE " + " AND ".join(where)

    count_args = []
    if score_expr is not None:
        count_args = args_for_score + args[len(args_for_score):len(args)-2]
    else:
        count_args = args[:-2]

    return sql, args, count_sql, count_args, limit, offset


def lambda_handler(event, context):
    origin = _allowed_origin(event or {})
    if not event:
        return _response(400, {"message": "Missing event"}, origin=origin)

    method = (event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method") or "").upper()
    if method == "OPTIONS":
        return {
            "statusCode": 204,
            "headers": {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type,Authorization",
                "Access-Control-Max-Age": "86400",
            },
            "body": "",
        }

    params = _normalize_query_params(event)
    try:
        sql, args, count_sql, count_args, limit, offset = _build_query(params)

        conn = _get_connection()
        with conn.cursor() as cur:
            cur.execute(count_sql, count_args)
            total_row = cur.fetchone() or {}
            total = int(total_row.get("total", 0))

            cur.execute(sql, args)
            items = cur.fetchall() or []

        return _response(
            200,
            {
                "items": items,
                "page": {
                    "limit": limit,
                    "offset": offset,
                    "returned": len(items),
                    "total": total,
                },
            },
            origin=origin,
        )
    except Exception as e:
        return _response(
            500,
            {
                "message": "Internal Server Error",
                "error": str(e),
            },
            origin=origin,
        )