import base64
import json
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Union

import jwt
from flask import Flask, Request, g, jsonify, request


class JWTVerificationError(Exception):
    pass


def _json_loads_bytes(b: bytes) -> Any:
    return json.loads(b.decode("utf-8"))


def _normalize_audience(aud: Optional[Union[str, Sequence[str]]]) -> Optional[Union[str, List[str]]]:
    if aud is None:
        return None
    if isinstance(aud, str):
        return aud
    return list(aud)


def _now() -> float:
    return time.time()


@dataclass(frozen=True)
class JWKSConfig:
    url: str
    timeout_seconds: float = 3.0
    cache_ttl_seconds: float = 300.0
    allow_insecure_http: bool = False


class _JWKSCache:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}

    def get(self, url: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            rec = self._cache.get(url)
            if not rec:
                return None
            expires_at, jwks = rec
            if _now() >= expires_at:
                del self._cache[url]
                return None
            return jwks

    def set(self, url: str, jwks: Dict[str, Any], ttl: float) -> None:
        with self._lock:
            self._cache[url] = (_now() + float(ttl), jwks)


_GLOBAL_JWKS_CACHE = _JWKSCache()


def _fetch_url_json(url: str, timeout_seconds: float) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "flask-jwt-wrapper/1.0",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        raw = resp.read()
    obj = _json_loads_bytes(raw)
    if not isinstance(obj, dict):
        raise JWTVerificationError("jwks response is not a JSON object")
    return obj


def _looks_like_pem(s: str) -> bool:
    return "-----BEGIN " in s and "-----END " in s


def _validate_alg_allowlist(algorithms: Sequence[str]) -> Tuple[str, ...]:
    out: List[str] = []
    for a in algorithms:
        if not isinstance(a, str) or not a:
            continue
        out.append(a)
    if not out:
        raise ValueError("algorithms must be a non-empty list")
    if "none" in {a.lower() for a in out}:
        raise ValueError("algorithm 'none' is not allowed")
    return tuple(out)


def _safe_unverified_headers(token: str) -> Dict[str, Any]:
    try:
        hdr = jwt.get_unverified_header(token)
    except Exception as e:
        raise JWTVerificationError("invalid token header") from e
    if not isinstance(hdr, dict):
        raise JWTVerificationError("invalid token header")
    return hdr


def _safe_unverified_claims(token: str) -> Dict[str, Any]:
    try:
        claims = jwt.decode(token, options={"verify_signature": False})
    except Exception as e:
        raise JWTVerificationError("invalid token payload") from e
    if not isinstance(claims, dict):
        raise JWTVerificationError("invalid token payload")
    return claims


def _choose_jwks_key(jwks: Dict[str, Any], kid: Optional[str], alg: str) -> Optional[Any]:
    keys = jwks.get("keys")
    if not isinstance(keys, list):
        return None
    candidates: List[Dict[str, Any]] = []
    for k in keys:
        if not isinstance(k, dict):
            continue
        if kid and k.get("kid") != kid:
            continue
        if k.get("use") not in (None, "sig"):
            continue
        kty = k.get("kty")
        if alg.startswith("RS") and kty != "RSA":
            continue
        if alg.startswith("ES") and kty != "EC":
            continue
        if alg.startswith("PS") and kty != "RSA":
            continue
        candidates.append(k)
    if not candidates and kid is not None:
        for k in keys:
            if isinstance(k, dict) and k.get("kid") == kid:
                candidates.append(k)
    if not candidates:
        return None
    try:
        return jwt.algorithms.get_default_algorithms()[alg].from_jwk(json.dumps(candidates[0]))
    except Exception:
        try:
            return jwt.PyJWK.from_dict(candidates[0]).key
        except Exception:
            return None


class JWTVerifier:
    def __init__(
        self,
        *,
        algorithms: Sequence[str] = ("HS256", "RS256"),
        hs_secrets: Optional[Mapping[str, str]] = None,
        hs_default_secret: Optional[str] = None,
        rs_public_keys_pem_by_kid: Optional[Mapping[str, str]] = None,
        rs_default_public_key_pem: Optional[str] = None,
        jwks: Optional[Sequence[JWKSConfig]] = None,
        issuers: Optional[Sequence[str]] = None,
        audiences: Optional[Union[str, Sequence[str]]] = None,
        leeway_seconds: float = 30.0,
        require_claims: Sequence[str] = ("exp", "iat"),
        verify_iat: bool = True,
        verify_nbf: bool = True,
        verify_exp: bool = True,
        verify_iss: bool = True,
        verify_aud: bool = False,
        max_token_age_seconds: Optional[float] = None,
    ) -> None:
        self._algorithms = _validate_alg_allowlist(algorithms)
        self._hs_secrets = dict(hs_secrets or {})
        self._hs_default_secret = hs_default_secret
        self._rs_pem_by_kid = dict(rs_public_keys_pem_by_kid or {})
        self._rs_default_pem = rs_default_public_key_pem
        self._jwks = list(jwks or [])
        self._issuers = set(issuers or [])
        self._audiences = _normalize_audience(audiences)
        self._leeway = float(leeway_seconds)
        self._require_claims = tuple(require_claims)
        self._verify_iat = bool(verify_iat)
        self._verify_nbf = bool(verify_nbf)
        self._verify_exp = bool(verify_exp)
        self._verify_iss = bool(verify_iss)
        self._verify_aud = bool(verify_aud)
        self._max_token_age_seconds = None if max_token_age_seconds is None else float(max_token_age_seconds)

    def _get_hs_key(self, claims: Dict[str, Any]) -> Optional[str]:
        if self._hs_secrets:
            iss = claims.get("iss")
            if isinstance(iss, str) and iss in self._hs_secrets:
                return self._hs_secrets[iss]
        return self._hs_default_secret

    def _get_rs_key_from_static(self, kid: Optional[str]) -> Optional[str]:
        if kid and kid in self._rs_pem_by_kid:
            return self._rs_pem_by_kid[kid]
        return self._rs_default_pem

    def _get_rs_key_from_jwks(self, kid: Optional[str], alg: str) -> Optional[Any]:
        for cfg in self._jwks:
            if not cfg.allow_insecure_http and cfg.url.lower().startswith("http://"):
                continue
            cached = _GLOBAL_JWKS_CACHE.get(cfg.url)
            jwks_obj: Optional[Dict[str, Any]] = None
            if cached is not None:
                jwks_obj = cached
            else:
                try:
                    jwks_obj = _fetch_url_json(cfg.url, cfg.timeout_seconds)
                except (urllib.error.URLError, TimeoutError, ValueError) as e:
                    continue
                if "keys" in jwks_obj and isinstance(jwks_obj["keys"], list):
                    _GLOBAL_JWKS_CACHE.set(cfg.url, jwks_obj, cfg.cache_ttl_seconds)
            if jwks_obj is None:
                continue
            key = _choose_jwks_key(jwks_obj, kid, alg)
            if key is not None:
                return key
        return None

    def _resolve_key(self, token: str) -> Tuple[Any, str]:
        hdr = _safe_unverified_headers(token)
        alg = hdr.get("alg")
        if not isinstance(alg, str) or not alg:
            raise JWTVerificationError("missing alg")
        if alg not in self._algorithms:
            raise JWTVerificationError("disallowed alg")

        kid = hdr.get("kid")
        if kid is not None and not isinstance(kid, str):
            raise JWTVerificationError("invalid kid")

        claims = _safe_unverified_claims(token)
        if alg.startswith("HS"):
            key = self._get_hs_key(claims)
            if not key:
                raise JWTVerificationError("no HS key configured")
            return key, alg

        if alg.startswith(("RS", "PS", "ES")):
            pem = self._get_rs_key_from_static(kid)
            if pem:
                if not _looks_like_pem(pem):
                    raise JWTVerificationError("invalid PEM key")
                return pem, alg
            jwk_key = self._get_rs_key_from_jwks(kid, alg)
            if jwk_key is not None:
                return jwk_key, alg
            raise JWTVerificationError("no public key found")

        raise JWTVerificationError("unsupported alg")

    def verify_and_decode(self, token: str) -> Dict[str, Any]:
        if not isinstance(token, str) or not token:
            raise JWTVerificationError("missing token")

        key, alg = self._resolve_key(token)

        options = {
            "verify_signature": True,
            "verify_exp": self._verify_exp,
            "verify_nbf": self._verify_nbf,
            "verify_iat": self._verify_iat,
            "verify_aud": self._verify_aud,
            "verify_iss": self._verify_iss,
            "require": list(self._require_claims),
        }

        unverified = _safe_unverified_claims(token)
        issuer_param: Optional[Union[str, Sequence[str]]] = None
        if self._verify_iss:
            if not self._issuers:
                raise JWTVerificationError("issuer allowlist not configured")
            issuer_param = list(self._issuers)

        try:
            claims = jwt.decode(
                token,
                key=key,
                algorithms=[alg],
                issuer=issuer_param,
                audience=self._audiences if self._verify_aud else None,
                leeway=self._leeway,
                options=options,
            )
        except jwt.ExpiredSignatureError as e:
            raise JWTVerificationError("token expired") from e
        except jwt.InvalidAudienceError as e:
            raise JWTVerificationError("invalid audience") from e
        except jwt.InvalidIssuerError as e:
            raise JWTVerificationError("invalid issuer") from e
        except jwt.ImmatureSignatureError as e:
            raise JWTVerificationError("token not yet valid") from e
        except jwt.MissingRequiredClaimError as e:
            raise JWTVerificationError(f"missing claim: {e.claim}") from e
        except jwt.InvalidTokenError as e:
            raise JWTVerificationError("invalid token") from e

        if not isinstance(claims, dict):
            raise JWTVerificationError("invalid token payload")

        if self._max_token_age_seconds is not None:
            iat = claims.get("iat")
            if not isinstance(iat, (int, float)):
                raise JWTVerificationError("missing or invalid iat")
            if (_now() - float(iat)) > self._max_token_age_seconds + self._leeway:
                raise JWTVerificationError("token too old")

        return claims


class FlaskJWT:
    def __init__(
        self,
        app: Optional[Flask] = None,
        *,
        verifier: Optional[JWTVerifier] = None,
        header_name: str = "Authorization",
        bearer_prefix: str = "Bearer ",
        store_in_g: str = "jwt_claims",
        error_handler: Optional[Callable[[Exception], Any]] = None,
    ) -> None:
        self.verifier = verifier or JWTVerifier()
        self.header_name = header_name
        self.bearer_prefix = bearer_prefix
        self.store_in_g = store_in_g
        self.error_handler = error_handler
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        app.extensions["flask_jwt_wrapper"] = self

    def _extract_token(self, req: Request) -> str:
        auth = req.headers.get(self.header_name, "")
        if not auth or not isinstance(auth, str):
            raise JWTVerificationError("missing authorization header")
        if not auth.startswith(self.bearer_prefix):
            raise JWTVerificationError("invalid authorization header")
        token = auth[len(self.bearer_prefix) :].strip()
        if not token:
            raise JWTVerificationError("missing token")
        return token

    def verify_request(self, req: Optional[Request] = None) -> Dict[str, Any]:
        r = req or request
        token = self._extract_token(r)
        claims = self.verifier.verify_and_decode(token)
        setattr(g, self.store_in_g, claims)
        return claims

    def required(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            try:
                self.verify_request()
            except Exception as e:
                if self.error_handler is not None:
                    return self.error_handler(e)
                msg = "unauthorized"
                if isinstance(e, JWTVerificationError):
                    msg = str(e) or "unauthorized"
                return jsonify({"error": msg}), 401
            return fn(*args, **kwargs)

        wrapped.__name__ = getattr(fn, "__name__", "wrapped")
        return wrapped


def _load_env_json(name: str) -> Optional[Dict[str, Any]]:
    v = os.environ.get(name)
    if not v:
        return None
    try:
        obj = json.loads(v)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    return obj


def _env_list(name: str) -> List[str]:
    v = os.environ.get(name, "")
    items = [s.strip() for s in v.split(",") if s.strip()]
    return items


def build_verifier_from_env() -> JWTVerifier:
    algorithms = _env_list("JWT_ALGORITHMS") or ["HS256", "RS256"]
    hs_default = os.environ.get("JWT_HS_SECRET")
    hs_by_iss = _load_env_json("JWT_HS_SECRETS_BY_ISS") or {}
    rs_default = os.environ.get("JWT_RS_PUBLIC_KEY_PEM")
    rs_by_kid = _load_env_json("JWT_RS_PUBLIC_KEYS_PEM_BY_KID") or {}
    issuers = _env_list("JWT_ISSUERS")
    audiences = _env_list("JWT_AUDIENCES")
    verify_aud = os.environ.get("JWT_VERIFY_AUD", "false").strip().lower() in ("1", "true", "yes", "y")
    leeway = float(os.environ.get("JWT_LEEWAY_SECONDS", "30"))
    max_age = os.environ.get("JWT_MAX_TOKEN_AGE_SECONDS")
    max_age_f = None if not max_age else float(max_age)

    jwks_cfgs: List[JWKSConfig] = []
    jwks_urls = _env_list("JWT_JWKS_URLS")
    jwks_ttl = float(os.environ.get("JWT_JWKS_CACHE_TTL_SECONDS", "300"))
    jwks_timeout = float(os.environ.get("JWT_JWKS_TIMEOUT_SECONDS", "3"))
    allow_http = os.environ.get("JWT_JWKS_ALLOW_INSECURE_HTTP", "false").strip().lower() in ("1", "true", "yes", "y")
    for u in jwks_urls:
        jwks_cfgs.append(
            JWKSConfig(
                url=u,
                timeout_seconds=jwks_timeout,
                cache_ttl_seconds=jwks_ttl,
                allow_insecure_http=allow_http,
            )
        )

    return JWTVerifier(
        algorithms=algorithms,
        hs_secrets=hs_by_iss,
        hs_default_secret=hs_default,
        rs_public_keys_pem_by_kid=rs_by_kid,
        rs_default_public_key_pem=rs_default,
        jwks=jwks_cfgs,
        issuers=issuers or None,
        audiences=audiences or None,
        leeway_seconds=leeway,
        verify_aud=verify_aud,
        verify_iss=True,
        max_token_age_seconds=max_age_f,
    )


def create_demo_app() -> Flask:
    app = Flask(__name__)
    verifier = build_verifier_from_env()
    auth = FlaskJWT(app, verifier=verifier)

    @app.get("/health")
    def health() -> Any:
        return jsonify({"status": "ok"})

    @app.get("/whoami")
    @auth.required
    def whoami() -> Any:
        claims = getattr(g, auth.store_in_g, {})
        sub = claims.get("sub")
        return jsonify({"sub": sub, "claims": claims})

    return app


if __name__ == "__main__":
    app = create_demo_app()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("DEBUG", "false").strip().lower() in ("1", "true", "yes", "y")
    app.run(host=host, port=port, debug=debug)
