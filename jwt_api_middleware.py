import os
from functools import lru_cache, wraps
from typing import Any, Callable, Optional, Sequence, Tuple

import jwt
from flask import Flask, g, jsonify, request

_DEFAULT_EXEMPT = frozenset({"/health", "/metrics"})


@lru_cache(maxsize=1)
def _key_and_algorithms() -> Tuple[Any, Sequence[str]]:
    pem = os.environ.get("JWT_PUBLIC_KEY_PEM")
    if pem:
        key = pem.replace("\\n", "\n").encode()
        return key, ("RS256", "RS384", "RS512")
    secret = os.environ.get("JWT_SECRET")
    if secret:
        return secret, ("HS256", "HS384", "HS512")
    raise RuntimeError("Set JWT_SECRET (symmetric) or JWT_PUBLIC_KEY_PEM (RSA public PEM)")


def _decode_token(token: str) -> dict[str, Any]:
    key, algorithms = _key_and_algorithms()
    issuer = os.environ.get("JWT_ISSUER")
    audience = os.environ.get("JWT_AUDIENCE")
    options = {
        "verify_signature": True,
        "verify_exp": True,
        "verify_nbf": True,
        "require": ["exp", "sub"],
    }
    kwargs: dict[str, Any] = {
        "algorithms": list(algorithms),
        "options": options,
        "leeway": int(os.environ.get("JWT_LEEWAY_SECONDS", "10")),
    }
    if issuer:
        kwargs["issuer"] = issuer
    if audience:
        kwargs["audience"] = audience
    return jwt.decode(token, key, **kwargs)


def init_jwt_auth(
    app: Flask,
    *,
    header_name: str = "Authorization",
    scheme: str = "Bearer",
    user_claim: str = "sub",
    claims_attr: str = "jwt_claims",
    user_attr: str = "jwt_user",
    exempt_paths: Optional[set[str]] = None,
) -> None:
    exempt = _DEFAULT_EXEMPT | (exempt_paths or set())

    @app.before_request
    def _jwt_before_request() -> Optional[tuple[Any, int]]:
        if request.method == "OPTIONS":
            return None
        path = request.path or ""
        if path in exempt:
            return None
        raw = request.headers.get(header_name, "")
        if not raw.startswith(scheme + " "):
            return jsonify({"error": "unauthorized", "detail": "missing or invalid credentials"}), 401
        token = raw[len(scheme) + 1 :].strip()
        if not token:
            return jsonify({"error": "unauthorized", "detail": "empty token"}), 401
        try:
            claims = _decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "unauthorized", "detail": "token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "unauthorized", "detail": "invalid token"}), 401
        setattr(g, claims_attr, claims)
        setattr(g, user_attr, claims.get(user_claim))
        return None


def jwt_optional(
    f: Callable[..., Any],
    *,
    user_claim: str = "sub",
    claims_attr: str = "jwt_claims",
    user_attr: str = "jwt_user",
    header_name: str = "Authorization",
    scheme: str = "Bearer",
) -> Callable[..., Any]:
    @wraps(f)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        raw = request.headers.get(header_name, "")
        if raw.startswith(scheme + " "):
            token = raw[len(scheme) + 1 :].strip()
            if token:
                try:
                    claims = _decode_token(token)
                    setattr(g, claims_attr, claims)
                    setattr(g, user_attr, claims.get(user_claim))
                except jwt.InvalidTokenError:
                    setattr(g, claims_attr, None)
                    setattr(g, user_attr, None)
            else:
                setattr(g, claims_attr, None)
                setattr(g, user_attr, None)
        else:
            setattr(g, claims_attr, None)
            setattr(g, user_attr, None)
        return f(*args, **kwargs)

    return wrapped


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/health")
    def health() -> Any:
        return {"status": "ok"}

    @app.get("/whoami")
    def whoami() -> Any:
        return {"user": getattr(g, "jwt_user", None), "claims": getattr(g, "jwt_claims", None)}

    init_jwt_auth(app, exempt_paths={"/health"})
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
