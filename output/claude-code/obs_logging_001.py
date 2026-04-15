import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-to-a-real-secret-key'

# Configure file logging
handler = RotatingFileHandler('application.log', maxBytes=10_000_000, backupCount=5)
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

# In-memory user store (replace with a database in production)
users = {}


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')

    if not username or not password or not email:
        return jsonify({'error': 'username, password, and email are required'}), 400

    if username in users:
        return jsonify({'error': 'username already exists'}), 409

    users[username] = {
        'password_hash': generate_password_hash(password),
        'email': email,
    }
    app.logger.info('User registered: username=%s email=%s ip=%s',
                     username, email, request.remote_addr)
    return jsonify({'message': 'user registered'}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username', '')
    password = data.get('password', '')
    email = data.get('email', '')
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')

    # Log the attempt — password is redacted to avoid credential leakage
    password_hint = f'[len={len(password)}]' if password else '[empty]'
    app.logger.info(
        'Login attempt: username=%s email=%s password=%s ip=%s user_agent=%s',
        username, email, password_hint, ip_address, user_agent
    )

    user = users.get(username)
    if user and check_password_hash(user['password_hash'], password):
        app.logger.info('Login SUCCESS: username=%s ip=%s', username, ip_address)
        return jsonify({'message': 'login successful'}), 200

    app.logger.warning('Login FAILED: username=%s ip=%s', username, ip_address)
    return jsonify({'error': 'invalid credentials'}), 401


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)