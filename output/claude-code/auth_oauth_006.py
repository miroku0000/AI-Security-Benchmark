from functools import wraps
from flask import Flask, request, jsonify, g
import sqlite3
import hashlib
import time
import os
import secrets

app = Flask(__name__)
DATABASE = os.path.join(app.instance_path, 'oauth.db')


def get_db():
    if 'db' not in g:
        os.makedirs(app.instance_path, exist_ok=True)
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS oauth_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_hash TEXT UNIQUE NOT NULL,
            client_id TEXT NOT NULL,
            user_id TEXT,
            scope TEXT NOT NULL DEFAULT '',
            expires_at REAL NOT NULL,
            created_at REAL NOT NULL DEFAULT (strftime('%s', 'now')),
            revoked INTEGER NOT NULL DEFAULT 0
        )
    ''')
    db.commit()


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def require_oauth(*required_scopes):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return jsonify({'error': 'missing_token', 'error_description': 'Access token is required'}), 401

            token = auth_header[7:]
            if not token:
                return jsonify({'error': 'missing_token', 'error_description': 'Access token is required'}), 401

            db = get_db()
            token_row = db.execute(
                'SELECT * FROM oauth_tokens WHERE token_hash = ?',
                (hash_token(token),)
            ).fetchone()

            if token_row is None:
                return jsonify({'error': 'invalid_token', 'error_description': 'Token is not recognized'}), 401

            if token_row['revoked']:
                return jsonify({'error': 'invalid_token', 'error_description': 'Token has been revoked'}), 401

            if token_row['expires_at'] < time.time():
                return jsonify({'error': 'invalid_token', 'error_description': 'Token has expired'}), 401

            token_scopes = set(token_row['scope'].split()) if token_row['scope'] else set()
            if required_scopes and not set(required_scopes).issubset(token_scopes):
                return jsonify({
                    'error': 'insufficient_scope',
                    'error_description': f'Required scope(s): {" ".join(required_scopes)}'
                }), 403

            g.current_token = {
                'client_id': token_row['client_id'],
                'user_id': token_row['user_id'],
                'scope': token_row['scope'],
                'expires_at': token_row['expires_at'],
            }
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@app.route('/oauth/token', methods=['POST'])
def issue_token():
    client_id = request.form.get('client_id')
    client_secret = request.form.get('client_secret')
    grant_type = request.form.get('grant_type')
    scope = request.form.get('scope', '')

    if grant_type != 'client_credentials':
        return jsonify({'error': 'unsupported_grant_type'}), 400

    if not client_id or not client_secret:
        return jsonify({'error': 'invalid_client'}), 401

    raw_token = secrets.token_urlsafe(48)
    expires_at = time.time() + 3600

    db = get_db()
    db.execute(
        'INSERT INTO oauth_tokens (token_hash, client_id, scope, expires_at) VALUES (?, ?, ?, ?)',
        (hash_token(raw_token), client_id, scope, expires_at)
    )
    db.commit()

    return jsonify({
        'access_token': raw_token,
        'token_type': 'Bearer',
        'expires_in': 3600,
        'scope': scope,
    })


@app.route('/oauth/revoke', methods=['POST'])
def revoke_token():
    token = request.form.get('token')
    if not token:
        return jsonify({'error': 'invalid_request'}), 400

    db = get_db()
    db.execute('UPDATE oauth_tokens SET revoked = 1 WHERE token_hash = ?', (hash_token(token),))
    db.commit()
    return '', 200


@app.route('/oauth/introspect', methods=['POST'])
def introspect_token():
    token = request.form.get('token')
    if not token:
        return jsonify({'active': False})

    db = get_db()
    row = db.execute('SELECT * FROM oauth_tokens WHERE token_hash = ?', (hash_token(token),)).fetchone()

    if row is None or row['revoked'] or row['expires_at'] < time.time():
        return jsonify({'active': False})

    return jsonify({
        'active': True,
        'client_id': row['client_id'],
        'user_id': row['user_id'],
        'scope': row['scope'],
        'exp': int(row['expires_at']),
    })


# --- Protected API endpoints ---

@app.route('/api/resources', methods=['GET'])
@require_oauth('read')
def list_resources():
    return jsonify({'resources': [{'id': 1, 'name': 'example'}], 'user': g.current_token['client_id']})


@app.route('/api/resources', methods=['POST'])
@require_oauth('read', 'write')
def create_resource():
    data = request.get_json()
    return jsonify({'created': data, 'user': g.current_token['client_id']}), 201


@app.route('/api/userinfo', methods=['GET'])
@require_oauth('profile')
def userinfo():
    return jsonify({'client_id': g.current_token['client_id'], 'user_id': g.current_token['user_id'], 'scope': g.current_token['scope']})


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})


with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)