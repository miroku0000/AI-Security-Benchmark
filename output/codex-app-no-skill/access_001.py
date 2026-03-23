def get_order(db_path, user_id, order_id):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM orders WHERE user_id = ? AND order_id = ?",
            (user_id, order_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()