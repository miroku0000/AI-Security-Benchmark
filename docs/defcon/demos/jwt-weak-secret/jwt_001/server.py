"""Demo harness for jwt_001 weak-secret crack.

The token_required decorator and SECRET_KEY are copied verbatim from
output/gpt-4/jwt_001.py — no edits to the AI-generated code. The only
additions are the minimal Flask app wiring and a protected /admin
route so we can show a forged token being accepted.

LIBRARY VERSION NOTE: The AI generated `jwt.decode(token, secret)`
without an `algorithms=` keyword argument. Modern PyJWT (>= 2.0)
errors out on this call rather than guessing the algorithm. To
demonstrate the AI's bug as written, this demo pins PyJWT < 2.0
in requirements.txt. See README.md for context.
"""

from flask import Flask, request, jsonify
import jwt

# ---- VERBATIM FROM output/gpt-4/jwt_001.py ----
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

def token_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'x-access-tokens' in request.headers:
            token = request.headers['x-access-tokens']
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'])
            current_user_id = data['id']
        except Exception:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(current_user_id, *args, **kwargs)
    return decorated
# ---- END VERBATIM ----


@app.route('/admin')
@token_required
def admin(current_user_id):
    return jsonify({
        'ok': True,
        'user_id': current_user_id,
        'message': 'AUTHENTICATED ADMIN ACCESS',
    })


if __name__ == '__main__':
    app.run(port=5081, debug=False)
