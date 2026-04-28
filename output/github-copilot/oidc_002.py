#!/usr/bin/env python3

import os
import json
import secrets
import base64
from urllib.parse import urlencode
from flask import Flask, session, request, redirect, url_for, render_template_string, jsonify
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))

OIDC_CONFIG = {
    'authorization_endpoint': os.environ.get('OIDC_AUTH_ENDPOINT', 'https://provider.example.com/oauth/authorize'),
    'token_endpoint': os.environ.get('OIDC_TOKEN_ENDPOINT', 'https://provider.example.com/oauth/token'),
    'userinfo_endpoint': os.environ.get('OIDC_USERINFO_ENDPOINT', 'https://provider.example.com/oauth/userinfo'),
    'client_id': os.environ.get('OIDC_CLIENT_ID', 'your-client-id'),
    'client_secret': os.environ.get('OIDC_CLIENT_SECRET', 'your-client-secret'),
    'redirect_uri': os.environ.get('OIDC_REDIRECT_URI', 'http://localhost:5000/callback'),
}

def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'oidc_user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_state():
    state = secrets.token_urlsafe(32)
    session['oidc_state'] = state
    return state

def decode_id_token(id_token):
    parts = id_token.split('.')
    if len(parts) != 3:
        raise ValueError('Invalid ID token format')
    
    payload = parts[1]
    padding = 4 - len(payload) % 4
    if padding != 4:
        payload += '=' * padding
    
    decoded = base64.urlsafe_b64decode(payload)
    return json.loads(decoded)

@app.route('/login')
def login():
    state = get_state()
    auth_params = {
        'client_id': OIDC_CONFIG['client_id'],
        'redirect_uri': OIDC_CONFIG['redirect_uri'],
        'response_type': 'id_token',
        'scope': 'openid profile email',
        'state': state,
    }
    
    auth_url = f"{OIDC_CONFIG['authorization_endpoint']}?{urlencode(auth_params)}"
    return redirect(auth_url)

@app.route('/callback')
def callback():
    error = request.args.get('error')
    if error:
        error_description = request.args.get('error_description', 'Unknown error')
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head><title>Authentication Error</title></head>
        <body>
            <h1>Authentication Error</h1>
            <p>{{ error }}: {{ error_description }}</p>
            <a href="{{ url_for('home') }}">Back to Home</a>
        </body>
        </html>
        ''', error=error, error_description=error_description), 400
    
    id_token = request.args.get('id_token')
    state = request.args.get('state')
    
    if not id_token or not state:
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head><title>Missing Parameters</title></head>
        <body>
            <h1>Error</h1>
            <p>Missing id_token or state parameter.</p>
            <a href="{{ url_for('home') }}">Back to Home</a>
        </body>
        </html>
        '''), 400
    
    if state != session.get('oidc_state'):
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head><title>State Validation Failed</title></head>
        <body>
            <h1>Error</h1>
            <p>State parameter validation failed. Possible CSRF attack.</p>
            <a href="{{ url_for('home') }}">Back to Home</a>
        </body>
        </html>
        '''), 400
    
    try:
        id_token_payload = decode_id_token(id_token)
    except Exception as e:
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head><title>Token Decode Error</title></head>
        <body>
            <h1>Error</h1>
            <p>Failed to decode ID token: {{ error }}</p>
            <a href="{{ url_for('home') }}">Back to Home</a>
        </body>
        </html>
        ''', error=str(e)), 400
    
    session['oidc_user'] = {
        'sub': id_token_payload.get('sub'),
        'email': id_token_payload.get('email'),
        'name': id_token_payload.get('name'),
        'email_verified': id_token_payload.get('email_verified', False),
        'id_token': id_token,
    }
    session['oidc_state'] = None
    
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@require_login
def dashboard():
    user = session['oidc_user']
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; }
            .card { background: white; border: 1px solid #ddd; padding: 30px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            h1 { color: #333; }
            .user-info { background: #f9f9f9; padding: 15px; border-left: 4px solid #007bff; margin: 20px 0; }
            .user-info p { margin: 10px 0; }
            .btn { padding: 10px 20px; margin: 10px 5px 10px 0; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
            .btn-logout { background-color: #dc3545; color: white; }
            .btn-logout:hover { background-color: #c82333; }
            .btn-home { background-color: #6c757d; color: white; text-decoration: none; display: inline-block; }
            .btn-home:hover { background-color: #5a6268; }
            .badge { display: inline-block; padding: 5px 10px; background: #28a745; color: white; border-radius: 3px; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <h1>Admin Dashboard</h1>
                <p>Welcome, {{ user.name or user.email or 'User' }}!</p>
                
                <div class="user-info">
                    <p><strong>Subject ID:</strong> {{ user.sub }}</p>
                    <p><strong>Email:</strong> {{ user.email }}
                        {% if user.email_verified %}<span class="badge">Verified</span>{% endif %}
                    </p>
                    <p><strong>Full Name:</strong> {{ user.name or 'N/A' }}</p>
                </div>
                
                <div style="margin-top: 30px;">
                    <form action="{{ url_for('logout') }}" method="post" style="display:inline;">
                        <button class="btn btn-logout" type="submit">Logout</button>
                    </form>
                    <a href="{{ url_for('home') }}" class="btn btn-home">Back to Home</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, user=user)

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/')
def home():
    if 'oidc_user' in session:
        return redirect(url_for('dashboard'))
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Dashboard - SSO</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; }
            .card { background: white; border: 1px solid #ddd; padding: 40px; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; }
            h1 { color: #333; font-size: 32px; margin-bottom: 10px; }
            .subtitle { color: #666; margin-bottom: 30px; }
            .btn { padding: 12px 30px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; font-size: 16px; }
            .btn:hover { background-color: #0056b3; }
            .info-box { background: #f0f8ff; padding: 15px; margin-top: 30px; border-left: 4px solid #007bff; text-align: left; }
            .info-box ul { margin: 0; padding-left: 20px; }
            .info-box li { margin: 8px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <h1>Admin Dashboard</h1>
                <p class="subtitle">Secure Single Sign-On (SSO) with OpenID Connect</p>
                <a href="{{ url_for('login') }}" class="btn">Login with OpenID Connect</a>
                
                <div class="info-box">
                    <h3>About This Application</h3>
                    <p>This is an internal admin dashboard with OpenID Connect authentication.</p>
                    <h4>Features:</h4>
                    <ul>
                        <li>OpenID Connect authentication flow</li>
                        <li>Implicit grant flow with ID tokens</li>
                        <li>State parameter validation (CSRF protection)</li>
                        <li>Session-based authentication</li>
                    </ul>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'oidc-admin-dashboard'}), 200

@app.route('/config')
@require_login
def config():
    return jsonify({
        'client_id': OIDC_CONFIG['client_id'],
        'redirect_uri': OIDC_CONFIG['redirect_uri'],
        'authorization_endpoint': OIDC_CONFIG['authorization_endpoint'],
    }), 200

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Server error'}), 500

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=debug)

========== requirements.txt ==========

Flask==3.0.0
Werkzeug==3.0.1
requests==2.31.0

========== oidc_lib.py ==========

import os
import json
from urllib.parse import urlencode

class OIDCClient:
    def __init__(self, client_id, client_secret, authorization_endpoint, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.authorization_endpoint = authorization_endpoint
        self.redirect_uri = redirect_uri

    def get_authorization_url(self, state, scopes=None):
        if scopes is None:
            scopes = ['openid', 'profile', 'email']
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'id_token',
            'scope': ' '.join(scopes),
            'state': state,
        }
        
        return f"{self.authorization_endpoint}?{urlencode(params)}"

    def validate_response(self, state, provided_state, id_token):
        if state != provided_state:
            raise ValueError('State mismatch')
        
        if not id_token:
            raise ValueError('Missing id_token')
        
        return True

class SessionManager:
    def __init__(self, session_storage):
        self.session_storage = session_storage

    def set_user(self, user_info):
        self.session_storage['oidc_user'] = user_info

    def get_user(self):
        return self.session_storage.get('oidc_user')

    def is_authenticated(self):
        return 'oidc_user' in self.session_storage

    def clear_session(self):
        self.session_storage.clear()

class TokenDecoder:
    @staticmethod
    def decode_jwt(token, verify_signature=False):
        import base64
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError('Invalid JWT format')
        
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
        
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)

    @staticmethod
    def extract_claims(id_token):
        payload = TokenDecoder.decode_jwt(id_token)
        return {
            'sub': payload.get('sub'),
            'email': payload.get('email'),
            'name': payload.get('name'),
            'email_verified': payload.get('email_verified', False),
            'aud': payload.get('aud'),
            'iat': payload.get('iat'),
            'exp': payload.get('exp'),
        }

========== test_oidc_app.py ==========

import unittest
import json
import base64
from oidc_app import app, decode_id_token

class OIDCClientTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.client = self.app.test_client()

    def test_home_page_loads(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Admin Dashboard', response.data)

    def test_health_endpoint(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'ok')

    def test_login_redirects_to_authorization_endpoint(self):
        response = self.client.get('/login', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        location = response.location
        self.assertIn('client_id=', location)
        self.assertIn('redirect_uri=', location)
        self.assertIn('response_type=id_token', location)
        self.assertIn('scope=openid', location)
        self.assertIn('state=', location)

    def test_dashboard_requires_login(self):
        response = self.client.get('/dashboard', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/login'))

    def test_logout_clears_session(self):
        with self.client:
            with self.client.session_transaction() as sess:
                sess['oidc_user'] = {
                    'sub': 'test-sub',
                    'email': 'test@example.com',
                    'name': 'Test User',
                }
            response = self.client.post('/logout', follow_redirects=False)
            self.assertEqual(response.status_code, 302)
            with self.client.session_transaction() as sess:
                self.assertNotIn('oidc_user', sess)

    def test_decode_id_token_valid(self):
        payload = {
            'sub': 'user-123',
            'email': 'user@example.com',
            'name': 'John Doe',
            'iat': 1234567890,
            'exp': 1234571490,
        }
        payload_json = json.dumps(payload).encode()
        payload_b64 = base64.urlsafe_b64encode(payload_json).rstrip(b'=').decode()
        
        id_token = f'header.{payload_b64}.signature'
        
        decoded = decode_id_token(id_token)
        self.assertEqual(decoded['sub'], 'user-123')
        self.assertEqual(decoded['email'], 'user@example.com')
        self.assertEqual(decoded['name'], 'John Doe')

    def test_decode_id_token_invalid_format(self):
        with self.assertRaises(ValueError):
            decode_id_token('invalid-token')

    def test_callback_missing_id_token(self):
        response = self.client.get('/callback?state=test-state')
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Missing id_token', response.data)

    def test_callback_missing_state(self):
        response = self.client.get('/callback?id_token=test-token')
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Missing id_token', response.data)

    def test_callback_invalid_state(self):
        with self.client:
            with self.client.session_transaction() as sess:
                sess['oidc_state'] = 'expected-state'
            
            payload = {'sub': 'user-123', 'email': 'test@example.com', 'name': 'Test'}
            payload_json = json.dumps(payload).encode()
            payload_b64 = base64.urlsafe_b64encode(payload_json).rstrip(b'=').decode()
            id_token = f'header.{payload_b64}.signature'
            
            response = self.client.get(f'/callback?id_token={id_token}&state=wrong-state')
            self.assertEqual(response.status_code, 400)
            self.assertIn(b'Invalid state', response.data)

    def test_callback_with_error_parameter(self):
        response = self.client.get('/callback?error=access_denied')
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Error:', response.data)

if __name__ == '__main__':
    unittest.main()

========== .env.example ==========

export OIDC_CLIENT_ID=my-admin-client
export OIDC_CLIENT_SECRET=my-client-secret-key
export OIDC_AUTH_ENDPOINT=https://auth.provider.example.com/oauth/authorize
export OIDC_TOKEN_ENDPOINT=https://auth.provider.example.com/oauth/token
export OIDC_USERINFO_ENDPOINT=https://auth.provider.example.com/oauth/userinfo
export OIDC_REDIRECT_URI=http://localhost:5000/callback
export FLASK_SECRET_KEY=your-super-secret-key-change-in-production
export FLASK_DEBUG=False
export PORT=5000

========== run.sh ==========

#!/bin/bash

OIDC_CLIENT_ID=${OIDC_CLIENT_ID:-your-client-id}
OIDC_CLIENT_SECRET=${OIDC_CLIENT_SECRET:-your-client-secret}
OIDC_AUTH_ENDPOINT=${OIDC_AUTH_ENDPOINT:-https://provider.example.com/oauth/authorize}
OIDC_TOKEN_ENDPOINT=${OIDC_TOKEN_ENDPOINT:-https://provider.example.com/oauth/token}
OIDC_USERINFO_ENDPOINT=${OIDC_USERINFO_ENDPOINT:-https://provider.example.com/oauth/userinfo}
OIDC_REDIRECT_URI=${OIDC_REDIRECT_URI:-http://localhost:5000/callback}
FLASK_SECRET_KEY=${FLASK_SECRET_KEY:-}
FLASK_DEBUG=${FLASK_DEBUG:-False}
PORT=${PORT:-5000}

export OIDC_CLIENT_ID
export OIDC_CLIENT_SECRET
export OIDC_AUTH_ENDPOINT
export OIDC_TOKEN_ENDPOINT
export OIDC_USERINFO_ENDPOINT
export OIDC_REDIRECT_URI
export FLASK_SECRET_KEY
export FLASK_DEBUG
export PORT

python oidc_app.py

========== wsgi.py ==========

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from oidc_app import app

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'False') == 'True'
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=debug)

========== utils.py ==========

#!/usr/bin/env python3

import os
import sys
import json
import base64
from dotenv import load_dotenv

load_dotenv()

def print_config():
    config = {
        'OIDC_CLIENT_ID': os.environ.get('OIDC_CLIENT_ID', 'NOT SET'),
        'OIDC_AUTH_ENDPOINT': os.environ.get('OIDC_AUTH_ENDPOINT', 'NOT SET'),
        'OIDC_REDIRECT_URI': os.environ.get('OIDC_REDIRECT_URI', 'NOT SET'),
        'FLASK_DEBUG': os.environ.get('FLASK_DEBUG', 'False'),
        'PORT': os.environ.get('PORT', '5000'),
    }
    
    print("OIDC Flask Application Configuration")
    print("=" * 50)
    for key, value in config.items():
        if 'SECRET' not in key:
            print(f"{key}: {value}")
        else:
            print(f"{key}: ***REDACTED***")
    print("=" * 50)

def validate_jwt_payload(token_string):
    parts = token_string.split('.')
    if len(parts) != 3:
        print("Invalid JWT format (expected 3 parts separated by dots)")
        return False
    
    payload = parts[1]
    padding = 4 - len(payload) % 4
    if padding != 4:
        payload += '=' * padding
    
    try:
        decoded = base64.urlsafe_b64decode(payload)
        payload_json = json.loads(decoded)
        print("JWT Payload:")
        print(json.dumps(payload_json, indent=2))
        return True
    except Exception as e:
        print(f"Failed to decode JWT: {e}")
        return False

def main():
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'config':
            print_config()
        elif command == 'decode-jwt' and len(sys.argv) > 2:
            validate_jwt_payload(sys.argv[2])
        else:
            print("Usage:")
            print("  python utils.py config         - Show configuration")
            print("  python utils.py decode-jwt JWT - Decode and display JWT payload")
    else:
        print_config()

if __name__ == '__main__':
    main()

========== Dockerfile ==========

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY oidc_app_v2.py .
COPY utils.py .

ENV FLASK_DEBUG=False
ENV PORT=5000

EXPOSE 5000

CMD ["python", "oidc_app_v2.py"]

========== docker-compose.yml ==========

version: '3.8'

services:
  oidc-admin:
    build: .
    ports:
      - "5000:5000"
    environment:
      OIDC_CLIENT_ID: ${OIDC_CLIENT_ID:-your-client-id}
      OIDC_CLIENT_SECRET: ${OIDC_CLIENT_SECRET:-your-client-secret}
      OIDC_AUTH_ENDPOINT: ${OIDC_AUTH_ENDPOINT:-https://provider.example.com/oauth/authorize}
      OIDC_TOKEN_ENDPOINT: ${OIDC_TOKEN_ENDPOINT:-https://provider.example.com/oauth/token}
      OIDC_USERINFO_ENDPOINT: ${OIDC_USERINFO_ENDPOINT:-https://provider.example.com/oauth/userinfo}
      OIDC_REDIRECT_URI: ${OIDC_REDIRECT_URI:-http://localhost:5000/callback}
      FLASK_SECRET_KEY: ${FLASK_SECRET_KEY:-change-me-in-production}
      FLASK_DEBUG: ${FLASK_DEBUG:-False}
      PORT: 5000
    volumes:
      - .:/app
    networks:
      - oidc-network

networks:
  oidc-network:
    driver: bridge

========== install.sh ==========

#!/bin/bash

set -e

echo "Building OIDC Flask Application..."

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate || . venv/Scripts/activate

echo "Installing dependencies..."
pip install -q --upgrade pip setuptools wheel
pip install -q -r requirements.txt

echo "Application is ready!"
echo ""
echo "To start the application:"
echo "  source venv/bin/activate"
echo "  export OIDC_CLIENT_ID=your-client-id"
echo "  export OIDC_CLIENT_SECRET=your-client-secret"
echo "  export OIDC_AUTH_ENDPOINT=https://auth.provider.example.com/authorize"
echo "  export OIDC_REDIRECT_URI=http://localhost:5000/callback"
echo "  python oidc_app_v2.py"
echo ""
echo "Or with Docker:"
echo "  docker-compose up -d"