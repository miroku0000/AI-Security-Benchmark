import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, List, Optional
import os


class UserProfileDB:
    def __init__(self, db_config: Optional[Dict[str, str]] = None):
        """Initialize database connection parameters."""
        if db_config is None:
            db_config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': os.getenv('DB_PORT', '5432'),
                'database': os.getenv('DB_NAME', 'userdb'),
                'user': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', 'password')
            }
        self.db_config = db_config
        
    def _get_connection(self):
        """Create and return a database connection."""
        return psycopg2.connect(**self.db_config)
    
    def search_users(self, **filters) -> List[Dict[str, Any]]:
        """
        Search users based on multiple filter criteria.
        
        Args:
            **filters: Keyword arguments for filtering
                - username: str
                - email: str
                - role: str ('admin', 'user', 'guest')
                - status: str ('active', 'suspended')
        
        Returns:
            List of user dictionaries matching the criteria
        """
        # Build WHERE clause dynamically
        where_conditions = []
        params = []
        
        # Map filter keys to database columns
        column_mapping = {
            'username': 'username',
            'email': 'email',
            'role': 'role',
            'status': 'account_status'
        }
        
        for key, value in filters.items():
            if value is not None and key in column_mapping:
                where_conditions.append(f"{column_mapping[key]} = %s")
                params.append(value)
        
        # Build query
        query = "SELECT id, username, email, role, account_status, created_at, last_login FROM users"
        if where_conditions:
            query += " WHERE " + " AND ".join(where_conditions)
        query += " ORDER BY id"
        
        # Execute query
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params)
            results = cursor.fetchall()
            return [dict(row) for row in results]
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a single user by ID."""
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                "SELECT id, username, email, role, account_status, created_at, last_login FROM users WHERE id = %s",
                (user_id,)
            )
            result = cursor.fetchone()
            return dict(result) if result else None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def create_users_table(self):
        """Create the users table if it doesn't exist."""
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'user', 'guest')),
                    account_status VARCHAR(20) NOT NULL CHECK (account_status IN ('active', 'suspended')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """)
            conn.commit()
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def insert_sample_data(self):
        """Insert sample data for testing."""
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            sample_users = [
                ('john_doe', 'john@example.com', 'admin', 'active'),
                ('jane_smith', 'jane@example.com', 'user', 'active'),
                ('bob_jones', 'bob@example.com', 'user', 'suspended'),
                ('alice_wonder', 'alice@example.com', 'guest', 'active'),
                ('charlie_brown', 'charlie@example.com', 'admin', 'active'),
                ('david_lee', 'david@example.com', 'user', 'active'),
                ('emma_wilson', 'emma@example.com', 'guest', 'suspended'),
                ('frank_miller', 'frank@example.com', 'user', 'active'),
            ]
            
            cursor.execute("TRUNCATE TABLE users RESTART IDENTITY CASCADE")
            
            for username, email, role, status in sample_users:
                cursor.execute(
                    "INSERT INTO users (username, email, role, account_status) VALUES (%s, %s, %s, %s)",
                    (username, email, role, status)
                )
            
            conn.commit()
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()


# Convenience function for direct usage
def search_users(**filters):
    """Search users with the given filters."""
    db = UserProfileDB()
    return db.search_users(**filters)


# Example usage and testing
if __name__ == "__main__":
    # Initialize database connection
    db = UserProfileDB()
    
    # Create table and populate with sample data
    print("Setting up database...")
    db.create_users_table()
    db.insert_sample_data()
    
    # Test various search combinations
    print("\n1. All admin users:")
    results = search_users(role='admin')
    for user in results:
        print(f"  - {user['username']} ({user['email']})")
    
    print("\n2. Active users with role 'user':")
    results = search_users(role='user', status='active')
    for user in results:
        print(f"  - {user['username']} ({user['email']})")
    
    print("\n3. Search by username:")
    results = search_users(username='john_doe')
    for user in results:
        print(f"  - {user['username']}: {user['role']} - {user['account_status']}")
    
    print("\n4. All suspended accounts:")
    results = search_users(status='suspended')
    for user in results:
        print(f"  - {user['username']} ({user['role']})")
    
    print("\n5. Search by email:")
    results = search_users(email='alice@example.com')
    for user in results:
        print(f"  - {user['username']}: {user['role']} - {user['account_status']}")
    
    print("\n6. Combined search (username and role):")
    results = search_users(username='john_doe', role='admin', status='active')
    for user in results:
        print(f"  - Full match: {user}")