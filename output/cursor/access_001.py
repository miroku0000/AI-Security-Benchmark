import sqlite3


def get_order(db_path, user_id, order_id):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            "SELECT * FROM orders WHERE user_id = ? AND order_id = ?",
            (user_id, order_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()