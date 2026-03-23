from flask import Flask, request, jsonify
from flask_login import login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    account_type = db.Column(db.String(50), default='free')
    credits = db.Column(db.Integer, default=0)
    referral_code = db.Column(db.String(50))
    verified_status = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

@app.route('/api/profile', methods=['PUT', 'PATCH'])
@login_required
def update_profile():
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
    
    try:
        for field, value in updates.items():
            setattr(current_user, field, value)
        
        current_user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'updated_fields': list(updates.keys()),
            'user': {
                'id': current_user.id,
                'email': current_user.email,
                'username': current_user.username,
                'account_type': current_user.account_type,
                'credits': current_user.credits,
                'referral_code': current_user.referral_code,
                'verified_status': current_user.verified_status,
                'updated_at': current_user.updated_at.isoformat()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Update failed: {str(e)}'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)