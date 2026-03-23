import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseConnection:
    def __init__(self):
        self.connection_pool = None
        self.db_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'hackathon_db',
            'user': 'admin',
            'password': 'demo123'
        }
        self.init_connection_pool()
    
    def init_connection_pool(self):
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1, 20,
                host=self.db_config['host'],
                port=self.db_config['port'],
                database=self.db_config['database'],
                user=self.db_config['user'],
                password=self.db_config['password']
            )
            logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Error creating connection pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        connection = None
        try:
            connection = self.connection_pool.getconn()
            yield connection
            connection.commit()
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if connection:
                self.connection_pool.putconn(connection)
    
    @contextmanager
    def get_cursor(self):
        with self.get_connection() as connection:
            cursor = connection.cursor()
            try:
                yield cursor
            finally:
                cursor.close()
    
    def execute_query(self, query, params=None):
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_single(self, query, params=None):
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()
    
    def execute_many(self, query, params_list):
        with self.get_cursor() as cursor:
            cursor.executemany(query, params_list)
            return cursor.rowcount
    
    def execute_update(self, query, params=None):
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount
    
    def close_all_connections(self):
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("All database connections closed")

db = DatabaseConnection()

def get_db_connection():
    return db.get_connection()

def query(sql, params=None):
    return db.execute_query(sql, params)

def query_one(sql, params=None):
    return db.execute_single(sql, params)

def execute(sql, params=None):
    return db.execute_update(sql, params)

def bulk_insert(sql, data):
    return db.execute_many(sql, data)

if __name__ == "__main__":
    try:
        result = query("SELECT version()")
        print(f"PostgreSQL version: {result[0][0]}")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT current_database()")
            print(f"Connected to database: {cursor.fetchone()[0]}")
            cursor.close()
        
    except Exception as e:
        print(f"Connection test failed: {e}")
    finally:
        db.close_all_connections()