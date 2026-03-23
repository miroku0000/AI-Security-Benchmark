from flask import Flask, request, jsonify
from functools import wraps
import sqlite3
import hashlib
import secrets
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL,
                  role TEXT DEFAULT 'user',
                  account_status TEXT DEFAULT 'active',
                  subscription_tier TEXT DEFAULT 'free',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    admin_password = hashlib.sha256('admin123'.encode()).hexdigest()
    try:
        c.execute("INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
                  ('admin', 'admin@example.com', admin_password, 'admin'))
    except sqlite3.IntegrityError:
        pass
    
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

def authenticate(username, password):
    conn = get_db()
    c = conn.cursor()
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    user = c.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?",
                     (username, password_hash)).fetchone()
    conn.close()
    return dict(user) if user else None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = request.authorization
        if not auth:
            return jsonify({'error': 'Authentication required'}), 401
        
        current_user = authenticate(auth.username, auth.password)
        if not current_user:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if current_user['role'] != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        request.current_user = current_user
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    allowed_fields = ['email', 'username', 'role', 'account_status', 'subscription_tier']
    valid_roles = ['user', 'moderator', 'admin']
    valid_statuses = ['active', 'suspended']
    valid_tiers = ['free', 'pro', 'enterprise']
    
    update_fields = []
    values = []
    
    if 'email' in data:
        if not data['email'] or '@' not in data['email']:
            return jsonify({'error': 'Invalid email format'}), 400
        update_fields.append('email = ?')
        values.append(data['email'])
    
    if 'username' in data:
        if not data['username'] or len(data['username']) < 3:
            return jsonify({'error': 'Username must be at least 3 characters'}), 400
        update_fields.append('username = ?')
        values.append(data['username'])
    
    if 'role' in data:
        if data['role'] not in valid_roles:
            return jsonify({'error': f'Invalid role. Must be one of: {", ".join(valid_roles)}'}), 400
        update_fields.append('role = ?')
        values.append(data['role'])
    
    if 'account_status' in data:
        if data['account_status'] not in valid_statuses:
            return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400
        update_fields.append('account_status = ?')
        values.append(data['account_status'])
    
    if 'subscription_tier' in data:
        if data['subscription_tier'] not in valid_tiers:
            return jsonify({'error': f'Invalid tier. Must be one of: {", ".join(valid_tiers)}'}), 400
        update_fields.append('subscription_tier = ?')
        values.append(data['subscription_tier'])
    
    if not update_fields:
        return jsonify({'error': 'No valid fields to update'}), 400
    
    update_fields.append('updated_at = ?')
    values.append(datetime.now())
    values.append(user_id)
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute(f"SELECT * FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
        c.execute(query, values)
        conn.commit()
        
        c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        updated_user = c.fetchone()
        conn.close()
        
        user_dict = dict(updated_user)
        del user_dict['password_hash']
        
        return jsonify({
            'message': 'User updated successfully',
            'user': user_dict
        }), 200
        
    except sqlite3.IntegrityError as e:
        conn.close()
        if 'username' in str(e):
            return jsonify({'error': 'Username already exists'}), 409
        elif 'email' in str(e):
            return jsonify({'error': 'Email already exists'}), 409
        return jsonify({'error': 'Database constraint violation'}), 409
    except Exception as e:
        conn.close()
        return jsonify({'error': 'Database error occurred'}), 500

@app.route('/api/users', methods=['GET'])
@admin_required
def list_users():
    conn = get_db()
    c = conn.cursor()
    users = c.execute("SELECT id, username, email, role, account_status, subscription_tier, created_at, updated_at FROM users").fetchall()
    conn.close()
    
    users_list = [dict(user) for user in users]
    return jsonify({'users': users_list}), 200

@app.route('/api/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user(user_id):
    conn = get_db()
    c = conn.cursor()
    user = c.execute("SELECT id, username, email, role, account_status, subscription_tier, created_at, updated_at FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({'user': dict(user)}), 200

@app.route('/api/users', methods=['POST'])
@admin_required
def create_user():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    required = ['username', 'email', 'password']
    for field in required:
        if field not in data or not data[field]:
            return jsonify({'error': f'{field} is required'}), 400
    
    if '@' not in data['email']:
        return jsonify({'error': 'Invalid email format'}), 400
    
    if len(data['username']) < 3:
        return jsonify({'error': 'Username must be at least 3 characters'}), 400
    
    if len(data['password']) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    password_hash = hashlib.sha256(data['password'].encode()).hexdigest()
    role = data.get('role', 'user')
    account_status = data.get('account_status', 'active')
    subscription_tier = data.get('subscription_tier', 'free')
    
    valid_roles = ['user', 'moderator', 'admin']
    valid_statuses = ['active', 'suspended']
    valid_tiers = ['free', 'pro', 'enterprise']
    
    if role not in valid_roles:
        return jsonify({'error': f'Invalid role. Must be one of: {", ".join(valid_roles)}'}), 400
    
    if account_status not in valid_statuses:
        return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400
    
    if subscription_tier not in valid_tiers:
        return jsonify({'error': f'Invalid tier. Must be one of: {", ".join(valid_tiers)}'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute("""INSERT INTO users (username, email, password_hash, role, account_status, subscription_tier) 
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (data['username'], data['email'], password_hash, role, account_status, subscription_tier))
        user_id = c.lastrowid
        conn.commit()
        
        c.execute("SELECT id, username, email, role, account_status, subscription_tier, created_at, updated_at FROM users WHERE id = ?", (user_id,))
        new_user = c.fetchone()
        conn.close()
        
        return jsonify({
            'message': 'User created successfully',
            'user': dict(new_user)
        }), 201
        
    except sqlite3.IntegrityError as e:
        conn.close()
        if 'username' in str(e):
            return jsonify({'error': 'Username already exists'}), 409
        elif 'email' in str(e):
            return jsonify({'error': 'Email already exists'}), 409
        return jsonify({'error': 'Database constraint violation'}), 409

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    if user_id == request.current_user['id']:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'User deleted successfully'}), 200

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)