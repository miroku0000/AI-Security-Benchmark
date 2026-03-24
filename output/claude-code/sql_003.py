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