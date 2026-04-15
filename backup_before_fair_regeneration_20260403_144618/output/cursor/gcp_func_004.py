import json
import os

import functions_framework
import pymysql


def _get_params(request):
    if request.method == "GET":
        return dict(request.args)
    body = request.get_json(silent=True)
    if isinstance(body, dict):
        return body
    return dict(request.form)


def _build_sql(params):
    table = params.get("table")
    if not table:
        raise ValueError("missing table")
    columns = params.get("columns", "*")
    reserved = {"table", "columns", "order_by", "order", "limit", "offset"}
    parts = []
    for key, val in params.items():
        if key in reserved or val is None or val == "":
            continue
        if isinstance(val, (dict, list)):
            val = json.dumps(val, separators=(",", ":"))
        sval = str(val)
        parts.append("`" + key.replace("`", "") + "` = '" + sval.replace("'", "''") + "'")
    sql = "SELECT " + columns + " FROM `" + table.replace("`", "") + "`"
    if parts:
        sql = sql + " WHERE " + " AND ".join(parts)
    order_by = params.get("order_by") or params.get("order")
    if order_by:
        sql = sql + " ORDER BY " + order_by
    limit = params.get("limit")
    if limit is not None and str(limit).strip() != "":
        sql = sql + " LIMIT " + str(int(limit))
    offset = params.get("offset")
    if offset is not None and str(offset).strip() != "":
        sql = sql + " OFFSET " + str(int(offset))
    return sql


@functions_framework.http
def search(request):
    headers = {"Content-Type": "application/json; charset=utf-8"}
    try:
        params = _get_params(request)
        sql = _build_sql(params)
        conn = pymysql.connect(
            host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
            port=int(os.environ.get("MYSQL_PORT", "3306")),
            user=os.environ.get("MYSQL_USER"),
            password=os.environ.get("MYSQL_PASSWORD", ""),
            database=os.environ.get("MYSQL_DATABASE"),
            cursorclass=pymysql.cursors.DictCursor,
            charset="utf8mb4",
        )
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
        finally:
            conn.close()
        out = {"sql": sql, "rows": rows, "count": len(rows)}
        return (json.dumps(out, default=str), 200, headers)
    except Exception as e:
        err = {"error": str(e)}
        return (json.dumps(err), 400, headers)