from flask import Flask, request, jsonify
from functools import wraps
from datetime import datetime
import re

app = Flask(__name__)

# Mock database
users_db = {}
current_user = {"id": 1, "role": "admin", "username": "admin"}

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.get('role') != 'admin':
            return jsonify({"error": "Forbidden. Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    if user_id not in users_db:
        return jsonify({"error": "User not found"}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    user = users_db[user_id]
    updated_fields = []
    
    if 'email' in data:
        if not validate_email(data['email']):
            return jsonify({"error": "Invalid email format"}), 400
        user['email'] = data['email']
        updated_fields.append('email')
    
    if 'username' in data:
        username = data['username'].strip()
        if not username or len(username) < 3:
            return jsonify({"error": "Username must be at least 3 characters"}), 400
        if any(u['username'] == username and u['id'] != user_id for u in users_db.values()):
            return jsonify({"error": "Username already taken"}), 409
        user['username'] = username
        updated_fields.append('username')
    
    if 'role' in data:
        if data['role'] not in ['user', 'moderator', 'admin']:
            return jsonify({"error": "Invalid role. Must be user, moderator, or admin"}), 400
        user['role'] = data['role']
        updated_fields.append('role')
    
    if 'account_status' in data:
        if data['account_status'] not in ['active', 'suspended']:
            return jsonify({"error": "Invalid account status. Must be active or suspended"}), 400
        user['account_status'] = data['account_status']
        updated_fields.append('account_status')
    
    if 'subscription_tier' in data:
        if data['subscription_tier'] not in ['free', 'pro', 'enterprise']:
            return jsonify({"error": "Invalid subscription tier. Must be free, pro, or enterprise"}), 400
        user['subscription_tier'] = data['subscription_tier']
        updated_fields.append('subscription_tier')
    
    if not updated_fields:
        return jsonify({"error": "No valid fields to update"}), 400
    
    user['updated_at'] = datetime.utcnow().isoformat()
    user['updated_by'] = current_user['username']
    
    return jsonify({
        "message": "User updated successfully",
        "user_id": user_id,
        "updated_fields": updated_fields,
        "user": {
            "id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "role": user['role'],
            "account_status": user['account_status'],
            "subscription_tier": user['subscription_tier'],
            "updated_at": user['updated_at'],
            "updated_by": user['updated_by']
        }
    }), 200

@app.route('/api/users', methods=['POST'])
@admin_required
def create_test_user():
    data = request.get_json()
    user_id = len(users_db) + 2
    users_db[user_id] = {
        "id": user_id,
        "username": data.get('username', f'user{user_id}'),
        "email": data.get('email', f'user{user_id}@example.com'),
        "role": data.get('role', 'user'),
        "account_status": data.get('account_status', 'active'),
        "subscription_tier": data.get('subscription_tier', 'free'),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "updated_by": current_user['username']
    }
    return jsonify(users_db[user_id]), 201

@app.route('/api/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user(user_id):
    if user_id not in users_db:
        return jsonify({"error": "User not found"}), 404
    return jsonify(users_db[user_id]), 200

@app.route('/api/users', methods=['GET'])
@admin_required
def get_all_users():
    return jsonify(list(users_db.values())), 200

@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad request"}), 400

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    users_db[2] = {
        "id": 2,
        "username": "johndoe",
        "email": "john@example.com",
        "role": "user",
        "account_status": "active",
        "subscription_tier": "free",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "updated_by": "system"
    }
    users_db[3] = {
        "id": 3,
        "username": "janedoe",
        "email": "jane@example.com",
        "role": "moderator",
        "account_status": "active",
        "subscription_tier": "pro",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "updated_by": "system"
    }
    app.run(debug=True)