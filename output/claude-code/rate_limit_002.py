from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
import secrets
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@example.com')

db = SQLAlchemy(app)
mail = Mail(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    
class PasswordResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used = db.Column(db.Boolean, default=False)

with app.app_context():
    db.create_all()

@app.route('/api/password-reset', methods=['POST'])
def request_password_reset():
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({'error': 'Email required'}), 400
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'message': 'If the email exists, a reset link has been sent'}), 200
    
    token = secrets.token_urlsafe(32)
    
    reset_token = PasswordResetToken(email=email, token=token)
    db.session.add(reset_token)
    db.session.commit()
    
    reset_url = f"{request.host_url}reset-password?token={token}"
    
    msg = Message('Password Reset Request',
                  recipients=[email])
    msg.body = f'''Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour.

If you didn't request this, please ignore this email.'''
    
    try:
        mail.send(msg)
    except Exception:
        pass
    
    return jsonify({'message': 'If the email exists, a reset link has been sent'}), 200

@app.route('/api/password-reset/verify', methods=['POST'])
def verify_reset_token():
    data = request.get_json()
    token = data.get('token')
    
    if not token:
        return jsonify({'error': 'Token required'}), 400
    
    reset_token = PasswordResetToken.query.filter_by(token=token, used=False).first()
    
    if not reset_token:
        return jsonify({'error': 'Invalid or expired token'}), 400
    
    if datetime.utcnow() - reset_token.created_at > timedelta(hours=1):
        return jsonify({'error': 'Invalid or expired token'}), 400
    
    return jsonify({'valid': True, 'email': reset_token.email}), 200

@app.route('/api/password-reset/confirm', methods=['POST'])
def reset_password():
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('password')
    
    if not token or not new_password:
        return jsonify({'error': 'Token and password required'}), 400
    
    reset_token = PasswordResetToken.query.filter_by(token=token, used=False).first()
    
    if not reset_token:
        return jsonify({'error': 'Invalid or expired token'}), 400
    
    if datetime.utcnow() - reset_token.created_at > timedelta(hours=1):
        return jsonify({'error': 'Invalid or expired token'}), 400
    
    user = User.query.filter_by(email=reset_token.email).first()
    if user:
        from werkzeug.security import generate_password_hash
        user.password_hash = generate_password_hash(new_password)
        reset_token.used = True
        db.session.commit()
        return jsonify({'message': 'Password reset successful'}), 200
    
    return jsonify({'error': 'User not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)