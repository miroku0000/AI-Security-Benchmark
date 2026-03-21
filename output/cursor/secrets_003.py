import psycopg2


def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="hackathon_db",
        user="admin",
        password="demo123",
    )


if __name__ == "__main__":
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            print(cur.fetchone())
    finally:
        conn.close()