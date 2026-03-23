import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'hackathon_db',
    'user': 'admin',
    'password': 'demo123'
}

def get_connection():
    try:
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        return conn
    except psycopg2.Error as e:
        logger.error(f"Database connection failed: {e}")
        raise

@contextmanager
def get_db_cursor(commit=True):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        yield cursor
        if commit:
            conn.commit()
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"Database operation failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def execute_query(query, params=None, fetch=True):
    with get_db_cursor() as cursor:
        cursor.execute(query, params)
        if fetch:
            return cursor.fetchall()
        return cursor.rowcount

def execute_one(query, params=None):
    with get_db_cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchone()

def execute_many(query, params_list):
    with get_db_cursor() as cursor:
        cursor.executemany(query, params_list)
        return cursor.rowcount

def test_connection():
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT version()")
            result = cursor.fetchone()
            logger.info(f"Connected to: {result['version']}")
            return True
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False

if __name__ == "__main__":
    if test_connection():
        print("Database connection successful!")
    else:
        print("Database connection failed!")