import os
import json
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, session
import pyotp
import jwt

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

DATA_FILE = 'users.json'
MFA_SESSIONS_FILE = 'mfa_sessions.json'
API_KEYS_FILE = 'api_keys.json'

def load_data(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {}

def save_data(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def generate_otp_secret():
    return pyotp.random_base32()

def verify_otp(secret, otp):
    totp = pyotp.TOTP(secret)
    return totp.verify(otp)

def generate_jwt_token(user_id):
    payload = {
        'user_id': user_id,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, app.secret_key, algorithm='HS256')

def verify_jwt_token(token):
    try:
        payload = jwt.decode(token, app.secret_key, algorithms=['HS256'])
        return payload.get('user_id')
    except:
        return None

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].replace('Bearer ', '')
        
        if not token and 'auth_token' in session:
            token = session['auth_token']
        
        if not token:
            return jsonify({'error': 'Missing authentication token'}), 401
        
        user_id = verify_jwt_token(token)
        if not user_id:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        request.user_id = user_id
        return f(*args, **kwargs)
    return decorated

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'Missing API key'}), 401
        
        api_keys = load_data(API_KEYS_FILE)
        if api_key not in api_keys:
            return jsonify({'error': 'Invalid API key'}), 401
        
        request.user_id = api_keys[api_key]['user_id']
        return f(*args, **kwargs)
    return decorated

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password required'}), 400
    
    users = load_data(DATA_FILE)
    if data['username'] in users:
        return jsonify({'error': 'User already exists'}), 409
    
    users[data['username']] = {
        'password': hash_password(data['password']),
        'mfa_enabled': False,
        'mfa_secret': None,
        'created_at': datetime.utcnow().isoformat()
    }
    save_data(DATA_FILE, users)
    
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password required'}), 400
    
    users = load_data(DATA_FILE)
    if data['username'] not in users:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    user = users[data['username']]
    if not verify_password(data['password'], user['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if user.get('mfa_enabled'):
        mfa_session_id = secrets.token_urlsafe(32)
        mfa_sessions = load_data(MFA_SESSIONS_FILE)
        mfa_sessions[mfa_session_id] = {
            'username': data['username'],
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        }
        save_data(MFA_SESSIONS_FILE, mfa_sessions)
        
        return jsonify({
            'mfa_required': True,
            'mfa_session_id': mfa_session_id,
            'message': 'OTP required'
        }), 200
    
    token = generate_jwt_token(data['username'])
    session['auth_token'] = token
    return jsonify({
        'mfa_required': False,
        'token': token,
        'message': 'Login successful'
    }), 200

@app.route('/api/verify-otp', methods=['POST'])
def verify_otp_endpoint():
    data = request.json
    if not data or not data.get('mfa_session_id') or not data.get('otp'):
        return jsonify({'error': 'MFA session ID and OTP required'}), 400
    
    mfa_sessions = load_data(MFA_SESSIONS_FILE)
    if data['mfa_session_id'] not in mfa_sessions:
        return jsonify({'error': 'Invalid MFA session'}), 401
    
    session_data = mfa_sessions[data['mfa_session_id']]
    if datetime.fromisoformat(session_data['expires_at']) < datetime.utcnow():
        del mfa_sessions[data['mfa_session_id']]
        save_data(MFA_SESSIONS_FILE, mfa_sessions)
        return jsonify({'error': 'MFA session expired'}), 401
    
    username = session_data['username']
    users = load_data(DATA_FILE)
    user = users[username]
    
    if not verify_otp(user['mfa_secret'], data['otp']):
        return jsonify({'error': 'Invalid OTP'}), 401
    
    del mfa_sessions[data['mfa_session_id']]
    save_data(MFA_SESSIONS_FILE, mfa_sessions)
    
    token = generate_jwt_token(username)
    session['auth_token'] = token
    return jsonify({
        'token': token,
        'message': 'OTP verified successfully'
    }), 200

@app.route('/api/enable-mfa', methods=['POST'])
@require_auth
def enable_mfa():
    users = load_data(DATA_FILE)
    users_list = list(users.items())
    user_entry = None
    for username, user_data in users_list:
        if username == request.user_id:
            user_entry = (username, user_data)
            break
    
    if not user_entry:
        return jsonify({'error': 'User not found'}), 404
    
    username, user = user_entry
    
    if user.get('mfa_enabled'):
        return jsonify({'error': 'MFA already enabled'}), 400
    
    mfa_secret = generate_otp_secret()
    totp = pyotp.TOTP(mfa_secret)
    provisioning_uri = totp.provisioning_uri(name=username, issuer_name='Flask Auth')
    
    user['mfa_secret'] = mfa_secret
    users[username] = user
    save_data(DATA_FILE, users)
    
    return jsonify({
        'mfa_secret': mfa_secret,
        'provisioning_uri': provisioning_uri,
        'message': 'Scan QR code with authenticator app'
    }), 200

@app.route('/api/confirm-mfa', methods=['POST'])
@require_auth
def confirm_mfa():
    data = request.json
    if not data or not data.get('otp'):
        return jsonify({'error': 'OTP required'}), 400
    
    users = load_data(DATA_FILE)
    users_list = list(users.items())
    user_entry = None
    for username, user_data in users_list:
        if username == request.user_id:
            user_entry = (username, user_data)
            break
    
    if not user_entry:
        return jsonify({'error': 'User not found'}), 404
    
    username, user = user_entry
    
    if not user.get('mfa_secret'):
        return jsonify({'error': 'MFA setup not initiated'}), 400
    
    if not verify_otp(user['mfa_secret'], data['otp']):
        return jsonify({'error': 'Invalid OTP'}), 401
    
    user['mfa_enabled'] = True
    users[username] = user
    save_data(DATA_FILE, users)
    
    return jsonify({'message': 'MFA enabled successfully'}), 200

@app.route('/api/disable-mfa', methods=['POST'])
@require_auth
def disable_mfa():
    data = request.json
    if not data or not data.get('otp'):
        return jsonify({'error': 'OTP required'}), 400
    
    users = load_data(DATA_FILE)
    users_list = list(users.items())
    user_entry = None
    for username, user_data in users_list:
        if username == request.user_id:
            user_entry = (username, user_data)
            break
    
    if not user_entry:
        return jsonify({'error': 'User not found'}), 404
    
    username, user = user_entry
    
    if not user.get('mfa_enabled'):
        return jsonify({'error': 'MFA not enabled'}), 400
    
    if not verify_otp(user['mfa_secret'], data['otp']):
        return jsonify({'error': 'Invalid OTP'}), 401
    
    user['mfa_enabled'] = False
    user['mfa_secret'] = None
    users[username] = user
    save_data(DATA_FILE, users)
    
    return jsonify({'message': 'MFA disabled successfully'}), 200

@app.route('/api/direct-login', methods=['POST'])
@require_api_key
def direct_login():
    users = load_data(DATA_FILE)
    users_list = list(users.items())
    user_entry = None
    for username, user_data in users_list:
        if username == request.user_id:
            user_entry = (username, user_data)
            break
    
    if not user_entry:
        return jsonify({'error': 'User not found'}), 404
    
    username = user_entry[0]
    token = generate_jwt_token(username)
    
    return jsonify({
        'token': token,
        'message': 'Direct API login successful, MFA skipped'
    }), 200

@app.route('/api/create-api-key', methods=['POST'])
@require_auth
def create_api_key():
    api_key = secrets.token_urlsafe(32)
    api_keys = load_data(API_KEYS_FILE)
    
    api_keys[api_key] = {
        'user_id': request.user_id,
        'created_at': datetime.utcnow().isoformat()
    }
    save_data(API_KEYS_FILE, api_keys)
    
    return jsonify({
        'api_key': api_key,
        'message': 'API key created successfully'
    }), 201

@app.route('/api/profile', methods=['GET'])
@require_auth
def profile():
    users = load_data(DATA_FILE)
    users_list = list(users.items())
    user_entry = None
    for username, user_data in users_list:
        if username == request.user_id:
            user_entry = (username, user_data)
            break
    
    if not user_entry:
        return jsonify({'error': 'User not found'}), 404
    
    username, user = user_entry
    return jsonify({
        'username': username,
        'mfa_enabled': user.get('mfa_enabled', False),
        'created_at': user.get('created_at')
    }), 200

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)