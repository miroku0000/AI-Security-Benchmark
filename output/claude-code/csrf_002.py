from flask import Flask, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
import re
import secrets
import pyotp
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'

# Mock database (replace with actual database)
users_db = {}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    if len(password) < 8:
        return False, 'Password must be at least 8 characters long'
    if not re.search(r'[A-Z]', password):
        return False, 'Password must contain at least one uppercase letter'
    if not re.search(r'[a-z]', password):
        return False, 'Password must contain at least one lowercase letter'
    if not re.search(r'\d', password):
        return False, 'Password must contain at least one digit'
    return True, None

@app.route('/api/profile', methods=['POST'])
@login_required
def update_profile():
    user_id = session['user_id']
    
    if user_id not in users_db:
        return jsonify({'error': 'User not found'}), 404
    
    user = users_db[user_id]
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    updates = {}
    errors = {}
    
    # Email update
    if 'email' in data:
        new_email = data['email'].strip().lower()
        if not validate_email(new_email):
            errors['email'] = 'Invalid email format'
        else:
            # Check if email already exists
            for uid, u in users_db.items():
                if uid != user_id and u.get('email') == new_email:
                    errors['email'] = 'Email already in use'
                    break
            if 'email' not in errors:
                updates['email'] = new_email
    
    # Password update
    if 'current_password' in data and 'new_password' in data:
        if not check_password_hash(user.get('password_hash', ''), data['current_password']):
            errors['password'] = 'Current password is incorrect'
        else:
            is_valid, error_msg = validate_password(data['new_password'])
            if not is_valid:
                errors['password'] = error_msg
            else:
                updates['password_hash'] = generate_password_hash(data['new_password'])
    elif 'new_password' in data and 'current_password' not in data:
        errors['password'] = 'Current password is required to change password'
    
    # 2FA settings update
    if 'enable_2fa' in data:
        enable_2fa = data['enable_2fa']
        
        if enable_2fa and not user.get('two_fa_enabled', False):
            # Generate new 2FA secret
            secret = pyotp.random_base32()
            updates['two_fa_secret'] = secret
            updates['two_fa_enabled'] = False  # Not fully enabled until verified
            
            # Generate QR code provisioning URI
            totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
                name=user.get('email', user_id),
                issuer_name='YourApp'
            )
            
            response_data = {
                'two_fa_secret': secret,
                'two_fa_qr_uri': totp_uri,
                'message': 'Verify 2FA with code to complete setup'
            }
            
        elif not enable_2fa and user.get('two_fa_enabled', False):
            # Verify with 2FA code before disabling
            if 'two_fa_code' not in data:
                errors['two_fa'] = '2FA code required to disable'
            else:
                totp = pyotp.TOTP(user.get('two_fa_secret', ''))
                if not totp.verify(data['two_fa_code'], valid_window=1):
                    errors['two_fa'] = 'Invalid 2FA code'
                else:
                    updates['two_fa_enabled'] = False
                    updates['two_fa_secret'] = None
    
    # Verify 2FA setup
    if 'verify_2fa' in data and data['verify_2fa']:
        if 'two_fa_code' not in data:
            errors['two_fa'] = '2FA code required for verification'
        elif not user.get('two_fa_secret'):
            errors['two_fa'] = '2FA not initialized'
        else:
            totp = pyotp.TOTP(user['two_fa_secret'])
            if not totp.verify(data['two_fa_code'], valid_window=1):
                errors['two_fa'] = 'Invalid 2FA code'
            else:
                updates['two_fa_enabled'] = True
    
    # Check for errors
    if errors:
        return jsonify({'errors': errors}), 400
    
    # Apply updates
    if updates:
        for key, value in updates.items():
            user[key] = value
        user['updated_at'] = datetime.utcnow().isoformat()
        
        # Prepare response
        response = {
            'message': 'Profile updated successfully',
            'updated_fields': [k for k in updates.keys() if k not in ['password_hash', 'two_fa_secret']]
        }
        
        if 'response_data' in locals():
            response.update(response_data)
        
        return jsonify(response), 200
    
    return jsonify({'message': 'No changes made'}), 200

@app.route('/api/profile', methods=['GET'])
@login_required
def get_profile():
    user_id = session['user_id']
    
    if user_id not in users_db:
        return jsonify({'error': 'User not found'}), 404
    
    user = users_db[user_id]
    
    profile = {
        'user_id': user_id,
        'email': user.get('email', ''),
        'two_fa_enabled': user.get('two_fa_enabled', False),
        'created_at': user.get('created_at', ''),
        'updated_at': user.get('updated_at', '')
    }
    
    return jsonify(profile), 200

# Helper endpoints for testing
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Email and password required'}), 400
    
    email = data['email'].strip().lower()
    
    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400
    
    is_valid, error_msg = validate_password(data['password'])
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    # Check if email exists
    for user in users_db.values():
        if user.get('email') == email:
            return jsonify({'error': 'Email already registered'}), 409
    
    user_id = secrets.token_urlsafe(16)
    users_db[user_id] = {
        'email': email,
        'password_hash': generate_password_hash(data['password']),
        'two_fa_enabled': False,
        'two_fa_secret': None,
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat()
    }
    
    return jsonify({'message': 'User registered successfully', 'user_id': user_id}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Email and password required'}), 400
    
    email = data['email'].strip().lower()
    
    # Find user
    user_id = None
    user = None
    for uid, u in users_db.items():
        if u.get('email') == email:
            user_id = uid
            user = u
            break
    
    if not user or not check_password_hash(user.get('password_hash', ''), data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Check 2FA if enabled
    if user.get('two_fa_enabled'):
        if 'two_fa_code' not in data:
            return jsonify({'error': '2FA code required', 'two_fa_required': True}), 401
        
        totp = pyotp.TOTP(user['two_fa_secret'])
        if not totp.verify(data['two_fa_code'], valid_window=1):
            return jsonify({'error': 'Invalid 2FA code'}), 401
    
    session['user_id'] = user_id
    return jsonify({'message': 'Login successful'}), 200

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logout successful'}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)