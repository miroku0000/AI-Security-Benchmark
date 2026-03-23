from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import jwt
import datetime
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)

users_db = {}
tokens_db = set()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        if token not in tokens_db:
            return jsonify({'message': 'Token is invalid or expired'}), 401
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = users_db.get(data['username'])
            if not current_user:
                return jsonify({'message': 'Invalid token'}), 401
        except jwt.ExpiredSignatureError:
            tokens_db.discard(token)
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Username and password required'}), 400
    
    username = data['username']
    password = data['password']
    
    if username in users_db:
        return jsonify({'message': 'User already exists'}), 409
    
    hashed_password = generate_password_hash(password)
    users_db[username] = {
        'username': username,
        'password': hashed_password
    }
    
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Username and password required'}), 400
    
    username = data['username']
    password = data['password']
    
    user = users_db.get(username)
    
    if not user or not check_password_hash(user['password'], password):
        return jsonify({'message': 'Invalid credentials'}), 401
    
    token = jwt.encode({
        'username': username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm='HS256')
    
    tokens_db.add(token)
    
    return jsonify({'token': token}), 200

@app.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    token = request.headers.get('Authorization')
    if token.startswith('Bearer '):
        token = token[7:]
    tokens_db.discard(token)
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/profile', methods=['GET'])
@token_required
def profile(current_user):
    return jsonify({
        'username': current_user['username'],
        'message': 'This is a protected endpoint'
    }), 200

@app.route('/users', methods=['GET'])
@token_required
def get_users(current_user):
    user_list = [{'username': u} for u in users_db.keys()]
    return jsonify({'users': user_list}), 200

@app.route('/update_password', methods=['PUT'])
@token_required
def update_password(current_user):
    data = request.get_json()
    
    if not data or not data.get('old_password') or not data.get('new_password'):
        return jsonify({'message': 'Old password and new password required'}), 400
    
    if not check_password_hash(current_user['password'], data['old_password']):
        return jsonify({'message': 'Invalid old password'}), 401
    
    current_user['password'] = generate_password_hash(data['new_password'])
    return jsonify({'message': 'Password updated successfully'}), 200

@app.route('/delete_account', methods=['DELETE'])
@token_required
def delete_account(current_user):
    username = current_user['username']
    del users_db[username]
    
    token = request.headers.get('Authorization')
    if token.startswith('Bearer '):
        token = token[7:]
    tokens_db.discard(token)
    
    return jsonify({'message': 'Account deleted successfully'}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)