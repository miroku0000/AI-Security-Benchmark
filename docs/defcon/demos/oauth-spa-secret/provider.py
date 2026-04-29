"""Stub OAuth provider for the SPA demo.

Three endpoints:
  GET  /authorize    — auto-issues an auth code, redirects back to SPA
  POST /token        — exchanges code for token (logs the request body
                       so the demo can show the secret arrived over
                       the wire)
  GET  /captures     — JSON list of every secret seen in /token bodies
"""

import os
import secrets
import json
import urllib.parse

from flask import Flask, request, jsonify, redirect


app = Flask(__name__)
PORT = int(os.environ.get('PROVIDER_PORT', '6072'))

CODES = {}            # code -> 'demo-user'
TOKENS = {}           # token -> 'demo-user'
SECRETS_SEEN = []     # full /token request bodies that came across the wire


@app.route('/authorize')
def authorize():
    redirect_uri = request.args.get('redirect_uri')
    code = secrets.token_urlsafe(12)
    CODES[code] = 'demo-user'
    sep = '&' if '?' in (redirect_uri or '') else '?'
    return redirect(f'{redirect_uri}{sep}code={code}')


@app.route('/token', methods=['POST'])
def token():
    # Capture EVERYTHING that came across — that's the demo.
    body = request.get_data(as_text=True)
    parsed = dict(urllib.parse.parse_qsl(body))
    SECRETS_SEEN.append(parsed)

    code = parsed.get('code')
    user = CODES.pop(code, None)
    if not user:
        return jsonify({'error': 'invalid_grant'}), 400
    access_token = secrets.token_urlsafe(20)
    TOKENS[access_token] = user
    return jsonify({
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': 3600,
    })


@app.route('/captures')
def captures():
    # The data that was sent to /token, including any client_secret.
    return jsonify(SECRETS_SEEN)


@app.after_request
def cors(resp):
    # The SPA runs on a different port; allow it to fetch /token.
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    resp.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
    return resp


@app.route('/token', methods=['OPTIONS'])
def token_preflight():
    return '', 204


if __name__ == '__main__':
    print(f'stub OAuth provider on http://127.0.0.1:{PORT}', flush=True)
    app.run(host='127.0.0.1', port=PORT, debug=False, use_reloader=False)
