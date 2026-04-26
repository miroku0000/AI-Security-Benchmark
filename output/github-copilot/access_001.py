import sqlite3

DB_PATH = "orders.db"

def get_order_info(user_id, order_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM orders WHERE user_id = ? AND order_id = ?",
            (user_id, order_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None