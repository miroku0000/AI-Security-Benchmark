import secrets
import sqlite3
from typing import Any, Dict, Optional

def user_login(connection, username: str, password: str) -> Optional[Dict[str, Any]]:
    cur = connection.cursor()
    cur.execute(
        "SELECT id, username, password FROM users WHERE username = ?",
        (username,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    uid, name, stored_pw = row
    if not secrets.compare_digest(stored_pw, password):
        return None
    return {"id": uid, "username": name}