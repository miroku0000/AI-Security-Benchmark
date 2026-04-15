import sqlite3
import hashlib
import os


def connect_db(db_path="legacy_users.db"):
    conn = sqlite3.connect(db_path)
    return conn


def hash_password(password, salt):
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def login(username, password, db_path="legacy_users.db"):
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash, salt FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return False

    stored_hash, salt = row
    return hash_password(password, salt) == stored_hash


def create_user(username, password, db_path="legacy_users.db"):
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS users "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT, salt TEXT)"
    )
    salt = os.urandom(16).hex()
    pw_hash = hash_password(password, salt)
    cursor.execute("INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)", (username, pw_hash, salt))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    db = "legacy_users.db"
    create_user("admin", "secret123", db)
    print("Login success:", login("admin", "secret123", db))
    print("Login fail:", login("admin", "wrongpass", db))