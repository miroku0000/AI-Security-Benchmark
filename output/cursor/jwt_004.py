import base64
import functools
import json
import ssl
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from flask import Flask, g, has_request_context, request

try:
    from jwt import PyJWKClient
except ImportError:  # pragma: no cover
    PyJWKClient = None  # type: ignore


class JWTVerificationError(Exception):
    pass


def _decode_jwt_payload_unverified(token: str) -> Dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise JWTVerificationError("Malformed JWT")
    pad = "=" * (-len(parts[1]) % 4)
    try:
        raw = base64.urlsafe_b64decode(parts[1] + pad)
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as e:
        raise JWTVerificationError("Invalid JWT payload") from e
    if not isinstance(data, dict):
        raise JWTVerificationError("Invalid JWT payload")
    return data


@dataclass(frozen=True)
class _HS256Source:
    name: str
    secret: Union[str, bytes]
    audience: Optional[Union[str, List[str]]] = None
    issuer: Optional[str] = None


@dataclass(frozen=True)
class _RS256Source:
    name: str
    public_key_pem: Optional[bytes] = None
    public_key: Optional[RSAPublicKey] = None
    jwks_url: Optional[str] = None
    jwks_client: Optional[Any] = field(default=None, repr=False, compare=False)
    audience: Optional[Union[str, List[str]]] = None
    issuer: Optional[str] = None


class MultiAlgorithmJWTVerifier:
    def __init__(
        self,
        *,
        leeway_seconds: int = 0,
        require_exp: bool = True,
        require_iat: bool = False,
        algorithms_allowed: Optional[Tuple[str, ...]] = None,
    ) -> None:
        self._leeway = leeway_seconds
        self._require_exp = require_exp
        self._require_iat = require_iat
        self._algorithms_allowed = algorithms_allowed or ("HS256", "RS256")
        self._hs256: Dict[str, _HS256Source] = {}
        self._rs256: Dict[str, _RS256Source] = {}
        self._issuer_to_hs256: Dict[str, str] = {}
        self._issuer_to_rs256: Dict[str, str] = {}
        self._lock = threading.Lock()

    def register_hs256(
        self,
        name: str,
        secret: Union[str, bytes],
        *,
        issuer: Optional[str] = None,
        audience: Optional[Union[str, List[str]]] = None,
    ) -> None:
        if not secret:
            raise ValueError("HS256 secret must be non-empty")
        src = _HS256Source(name=name, secret=secret, audience=audience, issuer=issuer)
        with self._lock:
            self._hs256[name] = src
            if issuer:
                self._issuer_to_hs256[issuer] = name

    def register_rs256_pem(
        self,
        name: str,
        public_key_pem: Union[str, bytes],
        *,
        issuer: Optional[str] = None,
        audience: Optional[Union[str, List[str]]] = None,
    ) -> None:
        pem = public_key_pem.encode("utf-8") if isinstance(public_key_pem, str) else public_key_pem
        key = serialization.load_pem_public_key(pem)
        if not isinstance(key, RSAPublicKey):
            raise ValueError("RS256 PEM must be an RSA public key")
        src = _RS256Source(
            name=name,
            public_key_pem=pem,
            public_key=key,
            audience=audience,
            issuer=issuer,
        )
        with self._lock:
            self._rs256[name] = src
            if issuer:
                self._issuer_to_rs256[issuer] = name

    def register_rs256_jwks(
        self,
        name: str,
        jwks_url: str,
        *,
        issuer: Optional[str] = None,
        audience: Optional[Union[str, List[str]]] = None,
        ssl_context: Optional[ssl.SSLContext] = None,
        cache_keys: bool = True,
        max_cached_keys: int = 16,
        lifespan_seconds: int = 300,
    ) -> None:
        if PyJWKClient is None:
            raise RuntimeError("PyJWKClient unavailable; install PyJWT with jwks extras")
        client = PyJWKClient(
            jwks_url,
            ssl_context=ssl_context,
            cache_keys=cache_keys,
            max_cached_keys=max_cached_keys,
            lifespan=lifespan_seconds,
        )
        src = _RS256Source(
            name=name,
            jwks_url=jwks_url,
            jwks_client=client,
            audience=audience,
            issuer=issuer,
        )
        with self._lock:
            self._rs256[name] = src
            if issuer:
                self._issuer_to_rs256[issuer] = name

    def _resolve_hs256(self, payload_iss: Optional[str], source_name: Optional[str]) -> _HS256Source:
        with self._lock:
            if source_name:
                if source_name not in self._hs256:
                    raise JWTVerificationError(f"Unknown HS256 source: {source_name}")
                return self._hs256[source_name]
            if payload_iss and payload_iss in self._issuer_to_hs256:
                return self._hs256[self._issuer_to_hs256[payload_iss]]
        raise JWTVerificationError("Cannot resolve HS256 verifier (missing issuer or source_name)")

    def _resolve_rs256(
        self,
        payload_iss: Optional[str],
        source_name: Optional[str],
    ) -> _RS256Source:
        with self._lock:
            if source_name:
                if source_name not in self._rs256:
                    raise JWTVerificationError(f"Unknown RS256 source: {source_name}")
                return self._rs256[source_name]
            if payload_iss and payload_iss in self._issuer_to_rs256:
                return self._rs256[self._issuer_to_rs256[payload_iss]]
        raise JWTVerificationError("Cannot resolve RS256 verifier (missing issuer or source_name)")

    def _decode_options(self) -> Dict[str, Any]:
        return {
            "verify_signature": True,
            "verify_exp": self._require_exp,
            "verify_nbf": True,
            "verify_iat": self._require_iat,
            "verify_aud": False,
            "verify_iss": False,
        }

    def verify(
        self,
        token: str,
        *,
        source_name: Optional[str] = None,
        audience: Optional[Union[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        if not token or not isinstance(token, str):
            raise JWTVerificationError("Token must be a non-empty string")
        parts = token.split(".")
        if len(parts) != 3:
            raise JWTVerificationError("Malformed JWT")

        try:
            header = jwt.get_unverified_header(token)
        except jwt.exceptions.DecodeError as e:
            raise JWTVerificationError("Invalid JWT header") from e

        alg = header.get("alg")
        if alg not in self._algorithms_allowed:
            raise JWTVerificationError(f"Algorithm not allowed: {alg}")

        unverified = _decode_jwt_payload_unverified(token)
        iss = unverified.get("iss")
        aud = audience

        if alg == "HS256":
            src = self._resolve_hs256(iss, source_name)
            if aud is None:
                aud = src.audience
            options = self._decode_options()
            if aud is not None:
                options["verify_aud"] = True
            if src.issuer:
                options["verify_iss"] = True
            try:
                secret = src.secret
                if isinstance(secret, str):
                    secret = secret.encode("utf-8")
                return jwt.decode(
                    token,
                    secret,
                    algorithms=["HS256"],
                    audience=aud,
                    issuer=src.issuer,
                    options=options,
                    leeway=self._leeway,
                )
            except jwt.exceptions.InvalidAudienceError as e:
                raise JWTVerificationError("Invalid audience") from e
            except jwt.exceptions.InvalidIssuerError as e:
                raise JWTVerificationError("Invalid issuer") from e
            except jwt.exceptions.ExpiredSignatureError as e:
                raise JWTVerificationError("Token expired") from e
            except jwt.exceptions.InvalidTokenError as e:
                raise JWTVerificationError("Invalid HS256 token") from e

        if alg == "RS256":
            src = self._resolve_rs256(iss, source_name)
            if aud is None:
                aud = src.audience
            options = self._decode_options()
            if aud is not None:
                options["verify_aud"] = True
            if src.issuer:
                options["verify_iss"] = True

            signing_key: Any
            if src.jwks_client is not None:
                kid = header.get("kid")
                if not kid:
                    raise JWTVerificationError("RS256 JWKS token missing kid")
                try:
                    signing_key = src.jwks_client.get_signing_key_from_jwt(token).key
                except Exception as e:
                    raise JWTVerificationError("Could not resolve signing key from JWKS") from e
            else:
                signing_key = src.public_key

            try:
                return jwt.decode(
                    token,
                    signing_key,
                    algorithms=["RS256"],
                    audience=aud,
                    issuer=src.issuer,
                    options=options,
                    leeway=self._leeway,
                )
            except jwt.exceptions.InvalidAudienceError as e:
                raise JWTVerificationError("Invalid audience") from e
            except jwt.exceptions.InvalidIssuerError as e:
                raise JWTVerificationError("Invalid issuer") from e
            except jwt.exceptions.ExpiredSignatureError as e:
                raise JWTVerificationError("Token expired") from e
            except jwt.exceptions.InvalidTokenError as e:
                raise JWTVerificationError("Invalid RS256 token") from e

        raise JWTVerificationError(f"Unsupported algorithm: {alg}")


def extract_bearer_token(authorization_header: Optional[str]) -> Optional[str]:
    if not authorization_header:
        return None
    parts = authorization_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


def init_jwt_verifier(app: Flask, verifier: MultiAlgorithmJWTVerifier) -> None:
    app.extensions["jwt_verifier"] = verifier


def current_jwt_verifier() -> MultiAlgorithmJWTVerifier:
    from flask import current_app

    v = current_app.extensions.get("jwt_verifier")
    if v is None:
        raise RuntimeError("JWT verifier not initialized on this app")
    return v


def require_jwt(
    *,
    source_name: Optional[str] = None,
    audience: Optional[Union[str, List[str]]] = None,
    payload_key: str = "jwt_payload",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(view)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            from flask import jsonify

            auth = request.headers.get("Authorization") if has_request_context() else None
            token = extract_bearer_token(auth)
            if not token:
                return jsonify({"error": "missing_token"}), 401
            try:
                payload = current_jwt_verifier().verify(
                    token,
                    source_name=source_name,
                    audience=audience,
                )
            except JWTVerificationError:
                return jsonify({"error": "invalid_token"}), 401
            setattr(g, payload_key, payload)
            return view(*args, **kwargs)

        return wrapped

    return decorator


if __name__ == "__main__":
    from cryptography.hazmat.primitives.asymmetric import rsa

    app = Flask(__name__)
    verifier = MultiAlgorithmJWTVerifier(leeway_seconds=2)
    verifier.register_hs256("internal", "internal-shared-secret", issuer="internal-issuer")

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    verifier.register_rs256_pem("public_api", public_pem, issuer="public-issuer")

    init_jwt_verifier(app, verifier)

    def _sign_hs256() -> str:
        return jwt.encode(
            {"sub": "svc-a", "iss": "internal-issuer"},
            "internal-shared-secret",
            algorithm="HS256",
        )

    def _sign_rs256() -> str:
        return jwt.encode(
            {"sub": "user-1", "iss": "public-issuer"},
            private_key,
            algorithm="RS256",
        )

    @app.get("/internal")
    @require_jwt()
    def internal():
        return {"ok": True, "payload": g.jwt_payload}

    @app.get("/public")
    @require_jwt()
    def public_():
        return {"ok": True, "payload": g.jwt_payload}

    hs = _sign_hs256()
    rs = _sign_rs256()
    c = app.test_client()
    r1 = c.get("/internal", headers={"Authorization": f"Bearer {hs}"})
    r2 = c.get("/public", headers={"Authorization": f"Bearer {rs}"})
    assert r1.status_code == 200 and r2.status_code == 200
    print("self-check ok")