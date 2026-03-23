from flask import Flask, request, jsonify
import sqlite3
import secrets
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (email TEXT PRIMARY KEY, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS password_resets
                 (email TEXT, token TEXT, expires_at TIMESTAMP)''')
    conn.commit()
    conn.close()

@app.route('/api/password-reset', methods=['POST'])
def password_reset():
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({'error': 'Email required'}), 400
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    c.execute("SELECT email FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    
    if not user:
        return jsonify({'message': 'If the email exists, a reset link has been sent'}), 200
    
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=1)
    
    c.execute("DELETE FROM password_resets WHERE email = ?", (email,))
    c.execute("INSERT INTO password_resets (email, token, expires_at) VALUES (?, ?, ?)",
              (email, token, expires_at))
    conn.commit()
    conn.close()
    
    reset_link = f"http://localhost:5000/reset-password?token={token}"
    
    msg = MIMEText(f"Click this link to reset your password: {reset_link}")
    msg['Subject'] = 'Password Reset Request'
    msg['From'] = 'noreply@example.com'
    msg['To'] = email
    
    try:
        s = smtplib.SMTP('localhost')
        s.send_message(msg)
        s.quit()
    except:
        pass
    
    return jsonify({'message': 'If the email exists, a reset link has been sent'}), 200

@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('password')
    
    if not token or not new_password:
        return jsonify({'error': 'Token and password required'}), 400
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    c.execute("SELECT email FROM password_resets WHERE token = ? AND expires_at > ?",
              (token, datetime.now()))
    result = c.fetchone()
    
    if not result:
        return jsonify({'error': 'Invalid or expired token'}), 400
    
    email = result[0]
    c.execute("UPDATE users SET password = ? WHERE email = ?", (new_password, email))
    c.execute("DELETE FROM password_resets WHERE email = ?", (email,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Password reset successful'}), 200

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
