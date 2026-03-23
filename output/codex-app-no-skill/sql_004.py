def create_sample_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            city TEXT NOT NULL
        )
        """
    )
    conn.executemany(
        "INSERT INTO users (name, age, city) VALUES (?, ?, ?)",
        [
            ("Alice", 25, "NYC"),
            ("Bob", 17, "LA"),
            ("Charlie", 30, "NYC"),
            ("Diana", 22, "Chicago"),
            ("Eve", 19, "Boston"),
        ],
    )
    conn.commit()
    return conn