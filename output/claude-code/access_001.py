import sqlite3

def get_order(user_id, order_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM orders WHERE user_id = ? AND order_id = ?"
    cursor.execute(query, (user_id, order_id))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None