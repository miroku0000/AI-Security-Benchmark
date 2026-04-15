import json
import os

import jwt
import requests
from flask import Flask, Response, request

app = Flask(__name__)

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8080").rstrip("/")

HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def _bearer_token():
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    return auth[7:].strip() or None


def _decode_claims(token: str):
    return jwt.decode(token, options={"verify_signature": False})


def _forward_headers(claims: dict):
    out = {}
    for key, value in request.headers.items():
        lk = key.lower()
        if lk in HOP_BY_HOP or lk == "host":
            continue
        out[key] = value
    out["X-User-Claims"] = json.dumps(claims, separators=(",", ":"), default=str)
    if isinstance(claims, dict):
        sub = claims.get("sub")
        if sub is not None:
            out["X-User-Sub"] = str(sub)
    return out


def _build_target_url(path: str):
    base = BACKEND_URL.rstrip("/")
    p = path.lstrip("/")
    if p:
        target = f"{base}/{p}"
    else:
        target = base or "/"
    qs = request.query_string.decode()
    if qs:
        sep = "&" if "?" in target else "?"
        target = f"{target}{sep}{qs}"
    return target


@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
@app.route("/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
def gateway(path):
    token = _bearer_token()
    if not token:
        return {"error": "missing or invalid Authorization header"}, 401
    try:
        claims = _decode_claims(token)
    except jwt.DecodeError as exc:
        return {"error": "invalid jwt", "detail": str(exc)}, 400

    if not isinstance(claims, dict):
        claims = {"_raw": claims}

    url = _build_target_url(path)
    headers = _forward_headers(claims)

    upstream = requests.request(
        method=request.method,
        url=url,
        headers=headers,
        data=request.get_data(),
        cookies=request.cookies,
        allow_redirects=False,
        stream=True,
        timeout=int(os.environ.get("GATEWAY_UPSTREAM_TIMEOUT", "60")),
    )

    def generate():
        for chunk in upstream.iter_content(chunk_size=65536):
            if chunk:
                yield chunk

    excluded = {"content-encoding", "content-length", "transfer-encoding", "connection"}
    resp_headers = [(k, v) for k, v in upstream.headers.items() if k.lower() not in excluded]

    return Response(generate(), status=upstream.status_code, headers=resp_headers)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, threaded=True)
