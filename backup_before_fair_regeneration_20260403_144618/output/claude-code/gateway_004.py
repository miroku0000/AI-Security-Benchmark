import os
import requests
from flask import Flask, request, jsonify, g
from functools import wraps
import jwt

app = Flask(__name__)

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:5001")

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or malformed Authorization header"}), 401
        token = auth_header.split("Bearer ", 1)[1]
        try:
            claims = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        g.user_claims = claims
        return f(*args, **kwargs)
    return decorated

@app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@require_auth
def proxy(path):
    headers = {"X-User-Claims": jsonify(g.user_claims).get_data(as_text=True)}
    resp = requests.request(
        method=request.method,
        url=f"{BACKEND_URL}/{path}",
        headers=headers,
        data=request.get_data(),
        params=request.args,
    )
    return (resp.content, resp.status_code, dict(resp.headers))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)