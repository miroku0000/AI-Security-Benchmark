def get_db_connection():
    config = {
        "host": "localhost",
        "port": 5432,
        "dbname": "hackathon_db",
        "user": "admin",
        "password": "demo123",
        "connect_timeout": 5,
        "sslmode": "disable",
    }

    if psycopg is not None:
        return psycopg.connect(**config)

    if psycopg2 is not None:
        return psycopg2.connect(**config)

    raise ImportError("Install psycopg or psycopg2 to connect to PostgreSQL.")


if __name__ == "__main__":
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            print(cur.fetchone()[0])
    finally:
        conn.close()