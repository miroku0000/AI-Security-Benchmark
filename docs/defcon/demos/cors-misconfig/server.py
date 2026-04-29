"""Wrap the AI's Lambda handler in a Flask app.

The AI's lambda_handler returns the AWS Lambda response shape
(statusCode/headers/body). We adapt that to a Flask /api/user-data
route that emits the exact same headers and body — proving the
*headers the AI generated* are what the browser receives.

We also expose /api/user-data-reflective which adapts the same AI
handler with one tiny realistic change: replace `*` with the
request's Origin header. This is the "fixed the CORS error"
bug pattern that ships in production once a developer hits the
spec-violation refusal browsers throw at the AI's literal output.

A /login endpoint sets a session cookie so the credentialed-fetch
demo has something to steal.
"""

import os
import json
import secrets

from flask import Flask, Response, request, make_response

from victim_module import lambda_handler


app = Flask(__name__)
SESSION_COOKIE = 'session_token'
SECRET_DATA = {
    'name': 'Alice Anderson',
    'email': 'alice@example.com',
    'session_secret': 'INTERNAL-SESSION-DATA-DO-NOT-LEAK',
}


def _emit_lambda_response(lambda_response):
    """Translate {statusCode, headers, body} into a Flask Response."""
    resp = make_response(lambda_response['body'], lambda_response['statusCode'])
    for k, v in lambda_response['headers'].items():
        # The AI passes Python `True` for credentials; the spec wants
        # the lowercase string 'true'. AWS Lambda's API Gateway
        # integration coerces this for you in production. We coerce
        # it here so the curl output matches what a real client sees.
        if isinstance(v, bool):
            v = 'true' if v else 'false'
        resp.headers[k] = v
    return resp


@app.route('/login')
def login():
    """Set a session cookie so the credentialed CORS fetch has something to send."""
    token = secrets.token_hex(16)
    resp = make_response(f'logged in as alice. session: {token}\n')
    # SameSite=None means cross-origin requests can attach this cookie.
    # In production the AI's Lambda would be behind an API Gateway
    # cookie-auth setup with similar weakness — we mimic that here.
    resp.set_cookie(SESSION_COOKIE, token, samesite='None', secure=False)
    return resp


@app.route('/api/user-data', methods=['GET', 'OPTIONS'])
def user_data_ai():
    """The AI's handler verbatim — emits ACAO:* AND ACAC:true."""
    event = {'headers': dict(request.headers)}
    lambda_resp = lambda_handler(event, None)
    return _emit_lambda_response(lambda_resp)


@app.route('/api/user-data-reflective', methods=['GET', 'OPTIONS'])
def user_data_reflective():
    """The 'fixed' version: replace * with the request's Origin.

    This is the realistic next bug. The AI's literal output is
    spec-invalid (browsers refuse). When the developer sees the
    browser refuse, they search 'CORS wildcard credentials' and
    find Stack Overflow saying 'reflect the Origin header instead.'
    They make that one-character change. Now CORS works AND the
    same dangerous behavior (any origin can read credentialed
    responses) ships to production.
    """
    event = {'headers': dict(request.headers)}
    # Run the AI's handler unchanged.
    lambda_resp = lambda_handler(event, None)

    # Apply the realistic developer "fix": echo Origin instead of *.
    request_origin = request.headers.get('Origin')
    if request_origin:
        lambda_resp['headers']['Access-Control-Allow-Origin'] = request_origin

    # Return the actually-sensitive data, not the AI's stub.
    if request.cookies.get(SESSION_COOKIE):
        lambda_resp['body'] = json.dumps(SECRET_DATA)

    return _emit_lambda_response(lambda_resp)


@app.route('/')
def index():
    return (
        '<h1>cors-misconfig demo</h1>'
        '<ul>'
        '<li><a href="/login">/login</a> — set a session cookie</li>'
        '<li><a href="/api/user-data">/api/user-data</a> — AI\'s verbatim handler (ACAO:* + ACAC:true)</li>'
        '<li><a href="/api/user-data-reflective">/api/user-data-reflective</a> — realistic developer "fix" (echo Origin + ACAC:true)</li>'
        '</ul>'
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5096'))
    app.run(host='127.0.0.1', port=port, debug=False)
