from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
import os

app = Flask(__name__)

# Configuration
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-this-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_TOKEN_LOCATION'] = ['headers']
app.config['JWT_HEADER_NAME'] = 'Authorization'
app.config['JWT_HEADER_TYPE'] = 'Bearer'

jwt = JWTManager(app)

# Mock database (replace with real database in production)
users_db = {}

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Username and password required'}), 400
    
    username = data['username']
    password = data['password']
    
    if username in users_db:
        return jsonify({'error': 'User already exists'}), 409
    
    users_db[username] = {
        'password': generate_password_hash(password),
        'id': len(users_db) + 1
    }
    
    return jsonify({'message': 'User created successfully', 'username': username}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Username and password required'}), 400
    
    username = data['username']
    password = data['password']
    
    if username not in users_db:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if not check_password_hash(users_db[username]['password'], password):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    access_token = create_access_token(
        identity=username,
        additional_claims={'user_id': users_db[username]['id']}
    )
    
    return jsonify({
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': 3600
    }), 200

@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify({
        'message': 'Access granted',
        'user': current_user
    }), 200

@app.route('/user/profile', methods=['GET'])
@jwt_required()
def get_profile():
    current_user = get_jwt_identity()
    if current_user in users_db:
        return jsonify({
            'username': current_user,
            'id': users_db[current_user]['id']
        }), 200
    return jsonify({'error': 'User not found'}), 404

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Unauthorized access'}), 401

@app.errorhandler(422)
def unprocessable(error):
    return jsonify({'error': 'Invalid or expired token'}), 422

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)