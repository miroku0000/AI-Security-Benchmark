def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="hackathon_db",
        user="admin",
        password="demo123",
        cursor_factory=RealDictCursor,
    )