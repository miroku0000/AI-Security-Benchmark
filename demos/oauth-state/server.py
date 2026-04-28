"""Harness for the auth_oauth_003.py demo.

The AI's app hardcodes:
  AUTHORIZATION_BASE_URL = 'https://authorization-server.com/oauth/authorize'
  TOKEN_URL              = 'https://authorization-server.com/oauth/token'
  CLIENT_ID, CLIENT_SECRET, REDIRECT_URI

We need:
  1. A local OAuth provider so the demo doesn't need internet egress.
  2. The AI's app pointed at the local provider.

To keep the AI's code byte-identical we patch the module-level
constants AFTER importing it. The /login route reads the constants
at request time (good — patches take effect). The /callback route's
`requests.post(TOKEN_URL, ...)` also reads at request time.

We also mount a /me route on the AI's app that reads the session
access_token and asks the provider for the associated username,
so the demo can prove "victim's session is now attacker's account."
"""

import os
import secrets
import urllib.parse

from flask import Flask, redirect, request, session, jsonify

import victim_module  # the AI's app


# Local provider runs on this port (separate from victim app).
PROVIDER_PORT = int(os.environ.get('PROVIDER_PORT', '6071'))
VICTIM_PORT   = int(os.environ.get('VICTIM_PORT',   '5097'))

PROVIDER_BASE = f'http://127.0.0.1:{PROVIDER_PORT}'
VICTIM_BASE   = f'http://127.0.0.1:{VICTIM_PORT}'

# Patch the AI's module-level constants to point at the local provider.
# REDIRECT_URI also gets the right port for the victim app.
victim_module.AUTHORIZATION_BASE_URL = f'{PROVIDER_BASE}/oauth/authorize'
victim_module.TOKEN_URL              = f'{PROVIDER_BASE}/oauth/token'
victim_module.CLIENT_ID              = 'demo-client-id'
victim_module.CLIENT_SECRET          = 'demo-client-secret'
victim_module.REDIRECT_URI           = f'{VICTIM_BASE}/callback'

victim_app = victim_module.app


# Add a /me route on the AI's app that reads the session and looks
# up the user via the provider's userinfo endpoint. This is normal
# OAuth-client behavior post-login — proves whose account the
# session is bound to.
@victim_app.route('/me')
def me():
    token = session.get('access_token')
    if not token:
        return 'not logged in', 401
    import requests
    resp = requests.get(f'{PROVIDER_BASE}/userinfo',
                        headers={'Authorization': f'Bearer {token}'})
    if resp.status_code != 200:
        return f'userinfo failed: {resp.status_code}', 500
    data = resp.json()
    return jsonify({
        'logged_in_as': data.get('username'),
        'access_token': token,
    })


@victim_app.route('/whoami')
def whoami():
    """Plain-text version for the demo."""
    token = session.get('access_token')
    if not token:
        return 'no session\n'
    import requests
    resp = requests.get(f'{PROVIDER_BASE}/userinfo',
                        headers={'Authorization': f'Bearer {token}'})
    if resp.status_code != 200:
        return f'userinfo failed: {resp.status_code}\n', 500
    data = resp.json()
    return f'logged in as: {data.get("username")}\naccess_token: {token}\n'


# ============================================================
# Local OAuth provider — completely separate Flask app on a
# different port. Issues codes and tokens; tracks which user
# initiated each flow so the demo can show "attacker's code was
# bound to attacker's account."
# ============================================================
provider_app = Flask('oauth_provider')
provider_app.secret_key = secrets.token_hex(16)

# In-memory stores — fine for a demo.
USERS = {
    'alice': {'username': 'alice', 'email': 'alice@example.com'},
    'attacker': {'username': 'attacker', 'email': 'attacker@evil.example.com'},
}
ACTIVE_USER_COOKIE = 'provider_user'

# code -> {client_id, redirect_uri, username}
CODES = {}
# token -> username
TOKENS = {}


@provider_app.route('/oauth/authorize')
def authorize():
    """Stub authorization endpoint.

    Real providers show a login page + consent screen. We auto-
    consent based on a 'provider_user' cookie that says who's
    currently logged in. Use /provider-login?username=<x> to set
    that cookie before initiating the flow.
    """
    client_id = request.args.get('client_id')
    redirect_uri = request.args.get('redirect_uri')
    response_type = request.args.get('response_type')
    state = request.args.get('state')  # may or may not be present

    if response_type != 'code':
        return 'unsupported response_type', 400

    user = request.cookies.get(ACTIVE_USER_COOKIE)
    if not user or user not in USERS:
        return ('no provider session — visit '
                f'{PROVIDER_BASE}/provider-login?username=alice or '
                f'{PROVIDER_BASE}/provider-login?username=attacker first\n'), 401

    code = secrets.token_urlsafe(16)
    CODES[code] = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'username': user,
    }

    sep = '&' if '?' in redirect_uri else '?'
    target = f'{redirect_uri}{sep}code={code}'
    if state:
        target += '&state=' + urllib.parse.quote(state)
    return redirect(target)


@provider_app.route('/oauth/token', methods=['POST'])
def token():
    """Exchange authorization code for an access token."""
    code = request.form.get('code')
    client_id = request.form.get('client_id')
    client_secret = request.form.get('client_secret')

    entry = CODES.pop(code, None)
    if not entry or entry['client_id'] != client_id:
        return jsonify({'error': 'invalid_grant'}), 400
    if client_secret != 'demo-client-secret':
        return jsonify({'error': 'invalid_client'}), 401

    access_token = secrets.token_urlsafe(24)
    TOKENS[access_token] = entry['username']
    return jsonify({
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': 3600,
    })


@provider_app.route('/userinfo')
def userinfo():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'no_token'}), 401
    token_val = auth[len('Bearer '):]
    user = TOKENS.get(token_val)
    if not user:
        return jsonify({'error': 'invalid_token'}), 401
    return jsonify(USERS[user])


@provider_app.route('/provider-login')
def provider_login():
    """Set the provider session to a given user."""
    username = request.args.get('username', 'alice')
    if username not in USERS:
        return f'unknown user: {username}\n', 400
    resp = redirect(request.args.get('next', '/provider-status'))
    resp.set_cookie(ACTIVE_USER_COOKIE, username, samesite='Lax')
    return resp


@provider_app.route('/provider-status')
def provider_status():
    user = request.cookies.get(ACTIVE_USER_COOKIE)
    return f'provider session: {user or "(none)"}\n'


def run_provider():
    provider_app.run(host='127.0.0.1', port=PROVIDER_PORT, debug=False, use_reloader=False)


def run_victim():
    # Override the AI's debug=True (slows boot, breaks reloader interaction).
    victim_app.run(host='127.0.0.1', port=VICTIM_PORT, debug=False, use_reloader=False)


if __name__ == '__main__':
    role = os.environ.get('ROLE', 'both')
    if role == 'provider':
        print(f'oauth provider on {PROVIDER_BASE}', flush=True)
        run_provider()
    elif role == 'victim':
        print(f'victim app (AI handler) on {VICTIM_BASE}', flush=True)
        run_victim()
    else:
        # Run both in the same process via threads — fine for the demo.
        import threading
        t = threading.Thread(target=run_provider, daemon=True)
        t.start()
        print(f'oauth provider on {PROVIDER_BASE}', flush=True)
        print(f'victim app (AI handler) on {VICTIM_BASE}', flush=True)
        run_victim()
