from flask import Flask, request, jsonify
from functools import wraps

app = Flask(__name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401
        
        token = auth_header.split(' ')[1]
        
        current_user = {
            'id': 1,
            'email': 'user@example.com',
            'username': 'johndoe',
            'account_type': 'free',
            'credits': 100,
            'referral_code': 'REF123ABC',
            'verified_status': False
        }
        
        return f(current_user, *args, **kwargs)
    return decorated_function

@app.route('/api/profile', methods=['PUT'])
@login_required
def update_profile(current_user):
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    allowed_fields = ['email', 'username', 'account_type', 'credits', 'referral_code', 'verified_status']
    
    updates = {}
    for field in allowed_fields:
        if field in data:
            updates[field] = data[field]
    
    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400
    
    if 'email' in updates:
        if not updates['email'] or '@' not in updates['email']:
            return jsonify({'error': 'Invalid email format'}), 400
        current_user['email'] = updates['email']
    
    if 'username' in updates:
        if not updates['username'] or len(updates['username']) < 3:
            return jsonify({'error': 'Username must be at least 3 characters'}), 400
        current_user['username'] = updates['username']
    
    if 'account_type' in updates:
        valid_types = ['free', 'basic', 'premium', 'enterprise']
        if updates['account_type'] not in valid_types:
            return jsonify({'error': f'Invalid account type. Must be one of: {", ".join(valid_types)}'}), 400
        current_user['account_type'] = updates['account_type']
    
    if 'credits' in updates:
        if not isinstance(updates['credits'], int) or updates['credits'] < 0:
            return jsonify({'error': 'Credits must be a non-negative integer'}), 400
        current_user['credits'] = updates['credits']
    
    if 'referral_code' in updates:
        if updates['referral_code'] and len(updates['referral_code']) < 5:
            return jsonify({'error': 'Referral code must be at least 5 characters'}), 400
        current_user['referral_code'] = updates['referral_code']
    
    if 'verified_status' in updates:
        if not isinstance(updates['verified_status'], bool):
            return jsonify({'error': 'Verified status must be a boolean'}), 400
        current_user['verified_status'] = updates['verified_status']
    
    return jsonify({
        'success': True,
        'message': 'Profile updated successfully',
        'updated_fields': list(updates.keys()),
        'profile': current_user
    }), 200

if __name__ == '__main__':
    app.run(debug=True, port=5001)