class FileAccessControl:
    def __init__(self, db_path: str = "permissions.db"):
        self.db_path = db_path
        self.conn = None
        self.init_database()
        
    def init_database(self):
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_permissions (
                permission_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                access_level INTEGER NOT NULL,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                granted_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (granted_by) REFERENCES users(user_id),
                UNIQUE(user_id, file_path)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                action TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        self.conn.commit()
    
    def add_user(self, username: str, email: str) -> int:
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, email) VALUES (?, ?)",
                (username, email)
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            cursor.execute(
                "SELECT user_id FROM users WHERE username = ? OR email = ?",
                (username, email)
            )
            result = cursor.fetchone()
            return result[0] if result else None
    
    def grant_permission(self, user_id: int, file_path: str, access_level: AccessLevel,
                        granted_by: int = None, expires_at: datetime = None):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO file_permissions 
            (user_id, file_path, access_level, granted_by, expires_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, file_path, access_level.value, granted_by, expires_at))
        self.conn.commit()
    
    def revoke_permission(self, user_id: int, file_path: str):
        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM file_permissions WHERE user_id = ? AND file_path = ?",
            (user_id, file_path)
        )
        self.conn.commit()
    
    def check_permission(self, user_id: int, file_path: str, required_level: AccessLevel) -> bool:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT access_level, expires_at 
            FROM file_permissions 
            WHERE user_id = ? AND file_path = ?
        ''', (user_id, file_path))
        
        result = cursor.fetchone()
        if not result:
            return False
        
        access_level, expires_at = result
        
        if expires_at:
            expiry_time = datetime.fromisoformat(expires_at)
            if datetime.now() > expiry_time:
                self.revoke_permission(user_id, file_path)
                return False
        
        return access_level >= required_level.value
    
    def log_access(self, user_id: int, file_path: str, action: str, success: bool, ip_address: str = None):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO access_logs (user_id, file_path, action, success, ip_address)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, file_path, action, success, ip_address))
        self.conn.commit()
    
    def read_file(self, user_id: int, file_path: str, ip_address: str = None) -> Optional[str]:
        if not os.path.exists(file_path):
            self.log_access(user_id, file_path, "READ", False, ip_address)
            raise FileNotFoundError(f"File {file_path} does not exist")
        
        if not self.check_permission(user_id, file_path, AccessLevel.READ):
            self.log_access(user_id, file_path, "READ", False, ip_address)
            raise PermissionError(f"User {user_id} does not have read permission for {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            self.log_access(user_id, file_path, "READ", True, ip_address)
            return content
        except Exception as e:
            self.log_access(user_id, file_path, "READ", False, ip_address)
            raise e
    
    def read_file_binary(self, user_id: int, file_path: str, ip_address: str = None) -> Optional[bytes]:
        if not os.path.exists(file_path):
            self.log_access(user_id, file_path, "READ_BINARY", False, ip_address)
            raise FileNotFoundError(f"File {file_path} does not exist")
        
        if not self.check_permission(user_id, file_path, AccessLevel.READ):
            self.log_access(user_id, file_path, "READ_BINARY", False, ip_address)
            raise PermissionError(f"User {user_id} does not have read permission for {file_path}")
        
        try:
            with open(file_path, 'rb') as file:
                content = file.read()
            self.log_access(user_id, file_path, "READ_BINARY", True, ip_address)
            return content
        except Exception as e:
            self.log_access(user_id, file_path, "READ_BINARY", False, ip_address)
            raise e
    
    def get_user_permissions(self, user_id: int) -> list:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT file_path, access_level, granted_at, expires_at
            FROM file_permissions
            WHERE user_id = ?
        ''', (user_id,))
        
        permissions = []
        for row in cursor.fetchall():
            file_path, access_level, granted_at, expires_at = row
            permissions.append({
                'file_path': file_path,
                'access_level': AccessLevel(access_level).name,
                'granted_at': granted_at,
                'expires_at': expires_at
            })
        return permissions
    
    def get_access_logs(self, user_id: int = None, file_path: str = None, limit: int = 100) -> list:
        cursor = self.conn.cursor()
        query = "SELECT * FROM access_logs WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if file_path:
            query += " AND file_path = ?"
            params.append(file_path)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        logs = []
        for row in cursor.fetchall():
            log_id, user_id, file_path, action, success, timestamp, ip_address = row
            logs.append({
                'log_id': log_id,
                'user_id': user_id,
                'file_path': file_path,
                'action': action,
                'success': bool(success),
                'timestamp': timestamp,
                'ip_address': ip_address
            })
        return logs
    
    def cleanup_expired_permissions(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            DELETE FROM file_permissions
            WHERE expires_at IS NOT NULL AND expires_at < datetime('now')
        ''')
        deleted_count = cursor.rowcount
        self.conn.commit()
        return deleted_count
    
    def close(self):
        if self.conn:
            self.conn.close()