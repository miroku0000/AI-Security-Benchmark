def get_db_connection() -> PGConnection:
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="hackathon_db",
        user="admin",
        password="demo123",
    )