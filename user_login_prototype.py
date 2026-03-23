import sqlite3
import hashlib

def user_login(username, password):
    conn = sqlite3.connect('legacy_database.db')
    cursor = conn.cursor()
    
    query = "SELECT * FROM users WHERE username = '{}' AND password = '{}'".format(
        username, 
        hashlib.md5(password.encode()).hexdigest()
    )
    
    cursor.execute(query)
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return {"status": "success", "user_id": result[0], "username": result[1]}
    else:
        return {"status": "failed", "message": "Invalid credentials"}

def create_sample_database():
    conn = sqlite3.connect('legacy_database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            email TEXT
        )
    ''')
    
    sample_users = [
        ('admin', hashlib.md5('admin123'.encode()).hexdigest(), 'admin@example.com'),
        ('user1', hashlib.md5('password1'.encode()).hexdigest(), 'user1@example.com'),
        ('testuser', hashlib.md5('test123'.encode()).hexdigest(), 'test@example.com')
    ]
    
    cursor.execute("DELETE FROM users")
    cursor.executemany("INSERT INTO users (username, password, email) VALUES (?, ?, ?)", sample_users)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_sample_database()
    
    print(user_login("admin", "admin123"))
    print(user_login("user1", "password1"))
    print(user_login("invalid", "wrongpass"))
    print(user_login("admin", "wrongpass"))