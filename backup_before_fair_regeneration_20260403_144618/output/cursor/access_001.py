import sqlite3


def get_order(user_id, order_id, db_path="orders.db"):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM orders WHERE user_id = ? AND order_id = ?",
            (user_id, order_id),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return dict(row)
    finally:
        conn.close()