"""
Flask JWT wrapper with multi-algorithm verification (HS256, RS256, etc.).
"""

from __future__ import annotations

import base64
import json
import logging
import os
import threading
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

import jwt
from flask import Flask, Request, g, jsonify, request

logger = logging.getLogger(__name__)

ALLOWED_ALGORITHMS = frozenset(
    {
        "HS256",
        "HS384",
        "HS512",
        "RS256",
        "RS384",
        "RS512",
        "ES256",
        "ES384",
        "ES512",
        "PS256",
        "PS384",
        "PS512",
    }
)


class JWTVerificationError(Exception):
    """Raised when token verification fails."""

    def __init__(self, message: str, status_code: int = 401) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class JWTKeyConfig:
    """Signing key material and validation options for one logical key."""

    key_id: str
    algorithm: str
    secret: Optional[str] = None
    public_key_pem: Optional[str] = None
    issuer: Optional[Union[str, Sequence[str]]] = None
    audience: Optional[Union[str, Sequence[str]]] = None
    leeway_seconds: int = 0
    require_exp: bool = True
    require_iat: bool = False
    require_nbf: bool = False

    def __post_init__(self) -> None:
        if self.algorithm not in ALLOWED_ALGORITHMS:
            raise ValueError(f"Unsupported algorithm: {self.algorithm}")
        if self.algorithm.startswith("HS"):
            if not self.secret:
                raise ValueError(f"HMAC key {self.key_id} requires secret")
        else:
            if not self.public_key_pem:
                raise ValueError(f"Asymmetric key {self.key_id} requires public_key_pem")


def _normalize_pem(pem: str) -> str:
    pem = pem.strip()
    if "BEGIN" not in pem:
        raise JWTVerificationError("Public key must be PEM or base64-encoded PEM")
    return pem


def _get_key_for_verify(cfg: JWTKeyConfig) -> Any:
    if cfg.algorithm.startswith("HS"):
        return cfg.secret.encode("utf-8") if isinstance(cfg.secret, str) else cfg.secret
    return _normalize_pem(cfg.public_key_pem or "")


class MultiAlgorithmJWTVerifier:
    """
    Verify JWTs using registered keys; resolves key by optional kid header or explicit key_id.
    """

    def __init__(self, keys: Sequence[JWTKeyConfig]) -> None:
        self._keys: Dict[str, JWTKeyConfig] = {}
        self._default_key_id: Optional[str] = None
        for k in keys:
            if k.key_id in self._keys:
                raise ValueError(f"Duplicate key_id: {k.key_id}")
            self._keys[k.key_id] = k
        if len(self._keys) == 1:
            self._default_key_id = next(iter(self._keys))

    def register_key(self, cfg: JWTKeyConfig) -> None:
        if cfg.key_id in self._keys:
            raise ValueError(f"Duplicate key_id: {cfg.key_id}")
        self._keys[cfg.key_id] = cfg
        if self._default_key_id is None and len(self._keys) == 1:
            self._default_key_id = cfg.key_id

    def _resolve_config(
        self,
        headers: Dict[str, Any],
        key_id: Optional[str],
    ) -> JWTKeyConfig:
        kid = headers.get("kid")
        alg = headers.get("alg")
        if alg and alg not in ALLOWED_ALGORITHMS:
            raise JWTVerificationError("Unsupported token algorithm")
        if alg == "none":
            raise JWTVerificationError("Algorithm none is not allowed")
        chosen_id = key_id or kid or self._default_key_id
        if not chosen_id:
            raise JWTVerificationError("No key identifier (kid) and no default key configured")
        cfg = self._keys.get(chosen_id)
        if not cfg:
            raise JWTVerificationError("Unknown signing key")
        if alg and alg != cfg.algorithm:
            raise JWTVerificationError("Algorithm does not match configured key")
        return cfg

    def decode_unverified_header_and_payload(self, token: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                raise JWTVerificationError("Malformed token")
            header = json.loads(
                base64.urlsafe_b64decode(parts[0] + "=" * (-len(parts[0]) % 4)).decode("utf-8")
            )
            payload = json.loads(
                base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)).decode("utf-8")
            )
            return header, payload
        except JWTVerificationError:
            raise
        except Exception as exc:
            raise JWTVerificationError("Invalid token structure") from exc

    def verify(
        self,
        token: str,
        *,
        key_id: Optional[str] = None,
        issuer: Optional[Union[str, Sequence[str]]] = None,
        audience: Optional[Union[str, Sequence[str]]] = None,
    ) -> Dict[str, Any]:
        try:
            header, _ = self.decode_unverified_header_and_payload(token)
        except JWTVerificationError:
            raise
        cfg = self._resolve_config(header, key_id)
        key = _get_key_for_verify(cfg)
        decode_issuer = issuer if issuer is not None else cfg.issuer
        decode_audience = audience if audience is not None else cfg.audience
        options = {
            "verify_signature": True,
            "verify_exp": cfg.require_exp,
            "verify_nbf": cfg.require_nbf,
            "verify_iat": cfg.require_iat,
            "require": [],
        }
        if cfg.require_exp:
            options["require"].append("exp")
        try:
            payload = jwt.decode(
                token,
                key=key,
                algorithms=[cfg.algorithm],
                issuer=decode_issuer,
                audience=decode_audience,
                leeway=cfg.leeway_seconds,
                options=options,
            )
        except jwt.ExpiredSignatureError as exc:
            raise JWTVerificationError("Token has expired") from exc
        except jwt.InvalidAudienceError as exc:
            raise JWTVerificationError("Invalid audience") from exc
        except jwt.InvalidIssuerError as exc:
            raise JWTVerificationError("Invalid issuer") from exc
        except jwt.InvalidTokenError as exc:
            raise JWTVerificationError("Invalid token") from exc
        return dict(payload)


class FlaskJWTMultiAuth:
    """Flask extension: attach verifier and optional route protection."""

    def __init__(self, app: Optional[Flask] = None, verifier: Optional[MultiAlgorithmJWTVerifier] = None) -> None:
        self.verifier = verifier
        self._lock = threading.Lock()
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        app.extensions = getattr(app, "extensions", {})
        app.extensions["jwt_multi_auth"] = self

    @property
    def verifier_instance(self) -> MultiAlgorithmJWTVerifier:
        if self.verifier is None:
            raise RuntimeError("MultiAlgorithmJWTVerifier not configured")
        return self.verifier

    def set_verifier(self, verifier: MultiAlgorithmJWTVerifier) -> None:
        with self._lock:
            self.verifier = verifier

    def get_token_from_request(self, req: Request) -> Optional[str]:
        auth = req.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
        return req.args.get("access_token")

    def verify_request(
        self,
        req: Optional[Request] = None,
        *,
        key_id: Optional[str] = None,
        issuer: Optional[Union[str, Sequence[str]]] = None,
        audience: Optional[Union[str, Sequence[str]]] = None,
    ) -> Dict[str, Any]:
        r = req or request
        token = self.get_token_from_request(r)
        if not token:
            raise JWTVerificationError("Missing bearer token")
        return self.verifier_instance.verify(token, key_id=key_id, issuer=issuer, audience=audience)

    def jwt_required(
        self,
        *,
        key_id: Optional[str] = None,
        issuer: Optional[Union[str, Sequence[str]]] = None,
        audience: Optional[Union[str, Sequence[str]]] = None,
        payload_attr: str = "jwt_payload",
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(f)
            def wrapped(*args: Any, **kwargs: Any) -> Any:
                try:
                    payload = self.verify_request(key_id=key_id, issuer=issuer, audience=audience)
                except JWTVerificationError as e:
                    return jsonify({"error": str(e)}), e.status_code
                setattr(g, payload_attr, payload)
                return f(*args, **kwargs)

            return wrapped

        return decorator


def load_verifier_from_env(prefix: str = "JWT_") -> MultiAlgorithmJWTVerifier:
    """
    Example: JWT_INTERNAL_HS256_SECRET, JWT_PUBLIC_RS256_KEY_ID + JWT_PUBLIC_RS256_PUBLIC_KEY_PEM
    For simplicity, use explicit code registration in production instead of parsing complex env.
    """
    keys: List[JWTKeyConfig] = []
    internal_secret = os.environ.get(f"{prefix}INTERNAL_HS256_SECRET")
    if internal_secret:
        keys.append(
            JWTKeyConfig(
                key_id=os.environ.get(f"{prefix}INTERNAL_KEY_ID", "internal-hs256"),
                algorithm="HS256",
                secret=internal_secret,
                issuer=os.environ.get(f"{prefix}INTERNAL_ISSUER"),
                audience=os.environ.get(f"{prefix}INTERNAL_AUDIENCE"),
            )
        )
    public_pem = os.environ.get(f"{prefix}PUBLIC_RS256_PUBLIC_KEY_PEM")
    if public_pem:
        keys.append(
            JWTKeyConfig(
                key_id=os.environ.get(f"{prefix}PUBLIC_KEY_ID", "public-rs256"),
                algorithm="RS256",
                public_key_pem=public_pem.replace("\\n", "\n"),
                issuer=os.environ.get(f"{prefix}PUBLIC_ISSUER"),
                audience=os.environ.get(f"{prefix}PUBLIC_AUDIENCE"),
            )
        )
    if not keys:
        raise ValueError("No JWT keys configured in environment")
    return MultiAlgorithmJWTVerifier(keys)


if __name__ == "__main__":
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    logging.basicConfig(level=logging.INFO)
    demo_secret = "internal-shared-secret-at-least-32-chars!!"
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    token_hs = jwt.encode(
        {"sub": "svc-a", "iss": "internal", "aud": "api"},
        demo_secret,
        algorithm="HS256",
        headers={"kid": "internal-hs256"},
    )
    token_rs = jwt.encode(
        {"sub": "user-1", "iss": "auth", "aud": "public"},
        private_key,
        algorithm="RS256",
        headers={"kid": "public-rs256"},
    )
    verifier = MultiAlgorithmJWTVerifier(
        [
            JWTKeyConfig(
                key_id="internal-hs256",
                algorithm="HS256",
                secret=demo_secret,
                issuer="internal",
                audience="api",
            ),
            JWTKeyConfig(
                key_id="public-rs256",
                algorithm="RS256",
                public_key_pem=public_pem,
                issuer="auth",
                audience="public",
            ),
        ]
    )
    app = Flask(__name__)
    jwt_auth = FlaskJWTMultiAuth(app, verifier)

    @app.route("/health")
    def health() -> tuple[Dict[str, str], int]:
        return {"status": "ok"}, 200

    @app.route("/decode-hs", methods=["GET"])
    @jwt_auth.jwt_required(key_id="internal-hs256")
    def decode_hs() -> tuple[Dict[str, Any], int]:
        return {"payload": getattr(g, "jwt_payload")}, 200

    @app.route("/decode-rs", methods=["GET"])
    @jwt_auth.jwt_required(key_id="public-rs256")
    def decode_rs() -> tuple[Dict[str, Any], int]:
        return {"payload": getattr(g, "jwt_payload")}, 200

    @app.route("/decode-auto", methods=["GET"])
    def decode_auto() -> tuple[Any, int]:
        try:
            p = jwt_auth.verify_request()
            return {"payload": p}, 200
        except JWTVerificationError as e:
            return jsonify({"error": str(e)}), e.status_code

    client = app.test_client()
    r1 = client.get("/decode-hs", headers={"Authorization": f"Bearer {token_hs}"})
    r2 = client.get("/decode-rs", headers={"Authorization": f"Bearer {token_rs}"})
    r3 = client.get("/decode-auto", headers={"Authorization": f"Bearer {token_hs}"})
    assert r1.status_code == 200 and r2.status_code == 200 and r3.status_code == 200
    logger.info("Demo OK: %s %s %s", r1.json, r2.json, r3.json)
