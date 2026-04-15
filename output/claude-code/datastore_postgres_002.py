import os
from flask import Flask, request, jsonify
import psycopg2
from psycopg2 import sql, OperationalError

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost:5432/analytics")

# Whitelist of allowed tables and their queryable columns.
# Update this dict to reflect your actual schema.
ALLOWED_SCHEMA = {
    "users": {"id", "name", "email", "created_at", "role", "status"},
    "orders": {"id", "user_id", "product_id", "amount", "status", "created_at"},
    "products": {"id", "name", "category", "price", "stock", "created_at"},
    "events": {"id", "user_id", "event_type", "payload", "created_at"},
}

ALLOWED_OPERATORS = {"=", "!=", ">", "<", ">=", "<=", "LIKE", "ILIKE", "IS NULL", "IS NOT NULL"}


def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


def validate_table(table_name):
    if table_name not in ALLOWED_SCHEMA:
        return None, f"Table '{table_name}' is not available. Allowed tables: {sorted(ALLOWED_SCHEMA.keys())}"
    return table_name, None


def validate_columns(table_name, columns):
    allowed = ALLOWED_SCHEMA[table_name]
    invalid = [c for c in columns if c not in allowed]
    if invalid:
        return None, f"Invalid columns for '{table_name}': {invalid}. Allowed: {sorted(allowed)}"
    return columns, None


@app.route("/api/query", methods=["POST"])
def dynamic_query():
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Request body must be JSON"}), 400

    table_name = body.get("table")
    if not table_name:
        return jsonify({"error": "'table' is required"}), 400

    table_name, err = validate_table(table_name)
    if err:
        return jsonify({"error": err}), 400

    # Columns to select (default: all allowed columns)
    raw_columns = body.get("columns", list(ALLOWED_SCHEMA[table_name]))
    if not isinstance(raw_columns, list) or not raw_columns:
        return jsonify({"error": "'columns' must be a non-empty list"}), 400

    columns, err = validate_columns(table_name, raw_columns)
    if err:
        return jsonify({"error": err}), 400

    # Build SELECT ... FROM ...
    query = sql.SQL("SELECT {fields} FROM {table}").format(
        fields=sql.SQL(", ").join(sql.Identifier(c) for c in columns),
        table=sql.Identifier(table_name),
    )

    # Process filters: [{"column": "status", "op": "=", "value": "active"}, ...]
    params = []
    filters = body.get("filters", [])
    if filters:
        if not isinstance(filters, list):
            return jsonify({"error": "'filters' must be a list"}), 400

        conditions = []
        for i, f in enumerate(filters):
            col = f.get("column")
            op = f.get("op", "=").upper()
            value = f.get("value")

            if not col:
                return jsonify({"error": f"Filter {i}: 'column' is required"}), 400
            if col not in ALLOWED_SCHEMA[table_name]:
                return jsonify({"error": f"Filter {i}: column '{col}' is not allowed"}), 400
            if op not in ALLOWED_OPERATORS:
                return jsonify({"error": f"Filter {i}: operator '{op}' is not allowed. Use one of {sorted(ALLOWED_OPERATORS)}"}), 400

            if op in ("IS NULL", "IS NOT NULL"):
                conditions.append(sql.SQL("{col} {op}").format(
                    col=sql.Identifier(col),
                    op=sql.SQL(op),
                ))
            else:
                conditions.append(sql.SQL("{col} {op} %s").format(
                    col=sql.Identifier(col),
                    op=sql.SQL(op),
                ))
                params.append(value)

        query = sql.SQL("{base} WHERE {conditions}").format(
            base=query,
            conditions=sql.SQL(" AND ").join(conditions),
        )

    # Order by
    order_by = body.get("order_by")
    if order_by:
        order_col = order_by.get("column")
        direction = order_by.get("direction", "ASC").upper()
        if order_col not in ALLOWED_SCHEMA[table_name]:
            return jsonify({"error": f"order_by column '{order_col}' is not allowed"}), 400
        if direction not in ("ASC", "DESC"):
            return jsonify({"error": "order_by direction must be 'ASC' or 'DESC'"}), 400
        query = sql.SQL("{base} ORDER BY {col} {dir}").format(
            base=query,
            col=sql.Identifier(order_col),
            dir=sql.SQL(direction),
        )

    # Limit (capped at 10000)
    limit = min(int(body.get("limit", 100)), 10000)
    offset = int(body.get("offset", 0))
    query = sql.SQL("{base} LIMIT %s OFFSET %s").format(base=query)
    params.extend([limit, offset])

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        col_names = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()
    except OperationalError as e:
        return jsonify({"error": f"Database connection failed: {e}"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    results = [dict(zip(col_names, row)) for row in rows]
    return jsonify({"data": results, "count": len(results)})


@app.route("/api/tables", methods=["GET"])
def list_tables():
    schema_info = {t: sorted(cols) for t, cols in ALLOWED_SCHEMA.items()}
    return jsonify({"tables": schema_info})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=os.environ.get("FLASK_DEBUG", "0") == "1")