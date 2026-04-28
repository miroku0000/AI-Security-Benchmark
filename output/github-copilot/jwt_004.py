from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Iterable, Mapping, Sequence

import jwt
from flask import Flask, Request, g, has_request_context, jsonify, request
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError

HS_ALGORITHMS = frozenset({"HS256", "HS384", "HS512"})
ASYMMETRIC_ALGORITHMS = frozenset(
    {"RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256", "ES384", "ES512"}
)
SUPPORTED_ALGORITHMS = HS_ALGORITHMS | ASYMMETRIC_ALGORITHMS
VALID_JWT_TYPES = frozenset({"JWT", "AT+JWT"})


class JWTVerificationError(Exception):
    pass


@dataclass(frozen=True)
class JWTSource:
    name: str
    algorithms: tuple[str, ...]
    key: str | bytes | None = None
    jwks_url: str | None = None
    issuer: str | None = None
    audience: str | tuple[str, ...] | None = None
    leeway: int = 0
    required_claims: tuple[str, ...] = ("exp", "iat")
    allowed_kids: tuple[str, ...] | None = None
    _jwk_client: PyJWKClient | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        normalized_algorithms = tuple(dict.fromkeys(self.algorithms))
        if not normalized_algorithms:
            raise ValueError("JWT source must define at least one algorithm")
        if any(algorithm not in SUPPORTED_ALGORITHMS for algorithm in normalized_algorithms):
            raise ValueError(f"JWT source {self.name!r} uses an unsupported algorithm")
        if any(algorithm.lower() == "none" for algorithm in normalized_algorithms):
            raise ValueError("Unsigned JWTs are not supported")

        uses_hmac = any(algorithm in HS_ALGORITHMS for algorithm in normalized_algorithms)
        uses_asymmetric = any(algorithm in ASYMMETRIC_ALGORITHMS for algorithm in normalized_algorithms)
        if uses_hmac and uses_asymmetric:
            raise ValueError("Do not mix HMAC and asymmetric algorithms in one JWT source")

        if uses_hmac:
            if self.jwks_url is not None:
                raise ValueError("JWKS cannot be used for HMAC JWT sources")
            if self.key is None:
                raise ValueError("HMAC JWT sources require a shared secret")
            key_bytes = self.key.encode("utf-8") if isinstance(self.key, str) else self.key
            if len(key_bytes) < 32:
                raise ValueError("HMAC shared secrets must be at least 32 bytes")

        if uses_asymmetric and self.key is None and self.jwks_url is None:
            raise ValueError("Asymmetric JWT sources require a public key or JWKS URL")

        normalized_required_claims = tuple(dict.fromkeys(self.required_claims))
        normalized_allowed_kids = (
            tuple(dict.fromkeys(self.allowed_kids)) if self.allowed_kids is not None else None
        )
        normalized_audience: str | tuple[str, ...] | None = self.audience
        if isinstance(self.audience, list):
            normalized_audience = tuple(self.audience)

        object.__setattr__(self, "algorithms", normalized_algorithms)
        object.__setattr__(self, "required_claims", normalized_required_claims)
        object.__setattr__(self, "allowed_kids", normalized_allowed_kids)
        object.__setattr__(self, "audience", normalized_audience)
        if self.jwks_url is not None:
            object.__setattr__(self, "_jwk_client", PyJWKClient(self.jwks_url))

    @classmethod
    def from_mapping(cls, config: Mapping[str, Any]) -> "JWTSource":
        algorithms = config["algorithms"]
        if isinstance(algorithms, str):
            raise TypeError("algorithms must be a sequence, not a string")

        allowed_kids = config.get("allowed_kids")
        if isinstance(allowed_kids, str):
            allowed_kids = (allowed_kids,)

        return cls(
            name=str(config["name"]),
            algorithms=tuple(algorithms),
            key=config.get("key"),
            jwks_url=config.get("jwks_url"),
            issuer=config.get("issuer"),
            audience=config.get("audience"),
            leeway=int(config.get("leeway", 0)),
            required_claims=tuple(config.get("required_claims", ("exp", "iat"))),
            allowed_kids=tuple(allowed_kids) if allowed_kids else None,
        )

    def matches_header(self, header: Mapping[str, Any]) -> bool:
        algorithm = header.get("alg")
        if algorithm not in self.algorithms:
            return False
        kid = header.get("kid")
        if self.allowed_kids is not None and kid not in self.allowed_kids:
            return False
        return True

    def resolve_key(self, token: str) -> str | bytes | Any:
        if self._jwk_client is not None:
            return self._jwk_client.get_signing_key_from_jwt(token).key
        if self.key is None:
            raise JWTVerificationError(f"JWT source {self.name!r} is missing a verification key")
        return self.key


class MultiSourceJWTVerifier:
    def __init__(self, sources: Iterable[JWTSource | Mapping[str, Any]]) -> None:
        normalized_sources = [
            source if isinstance(source, JWTSource) else JWTSource.from_mapping(source)
            for source in sources
        ]
        if not normalized_sources:
            raise ValueError("At least one JWT source is required")

        self._sources = normalized_sources
        self._sources_by_name = {source.name: source for source in normalized_sources}
        if len(self._sources_by_name) != len(normalized_sources):
            raise ValueError("JWT source names must be unique")

    @property
    def source_names(self) -> tuple[str, ...]:
        return tuple(self._sources_by_name.keys())

    def verify_token(self, token: str, source_name: str | None = None) -> dict[str, Any]:
        header = self._get_unverified_header(token)
        candidates = self._select_sources(header, source_name=source_name)

        last_error: Exception | None = None
        for source in candidates:
            try:
                payload = jwt.decode(
                    token,
                    key=source.resolve_key(token),
                    algorithms=list(source.algorithms),
                    audience=source.audience,
                    issuer=source.issuer,
                    leeway=source.leeway,
                    options={
                        "require": list(source.required_claims),
                        "verify_signature": True,
                        "verify_exp": True,
                        "verify_iat": True,
                        "verify_nbf": True,
                        "verify_iss": source.issuer is not None,
                        "verify_aud": source.audience is not None,
                    },
                )
            except (InvalidTokenError, PyJWKClientError) as exc:
                last_error = exc
                continue

            if not isinstance(payload, dict):
                raise JWTVerificationError("JWT payload must be a JSON object")
            if has_request_context():
                g.jwt_payload = payload
                g.jwt_source = source.name
                g.jwt_header = header
            return payload

        if last_error is None:
            raise JWTVerificationError("No trusted JWT source matched the token header")
        raise JWTVerificationError("JWT verification failed") from last_error

    def verify_request(self, req: Request | None = None, source_name: str | None = None) -> dict[str, Any]:
        token = self.extract_bearer_token(req)
        return self.verify_token(token, source_name=source_name)

    @staticmethod
    def extract_bearer_token(req: Request | None = None) -> str:
        active_request = req or request
        authorization = active_request.headers.get("Authorization", "")
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() != "bearer" or not value:
            raise JWTVerificationError("Missing or invalid Bearer token")
        return value.strip()

    def jwt_required(self, source_name: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(view_func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(view_func)
            def wrapped(*args: Any, **kwargs: Any) -> Any:
                self.verify_request(source_name=source_name)
                return view_func(*args, **kwargs)

            return wrapped

        return decorator

    def _get_unverified_header(self, token: str) -> Mapping[str, Any]:
        try:
            header = jwt.get_unverified_header(token)
        except InvalidTokenError as exc:
            raise JWTVerificationError("Malformed JWT header") from exc

        algorithm = header.get("alg")
        if algorithm not in SUPPORTED_ALGORITHMS:
            raise JWTVerificationError("Unsupported or unsafe JWT algorithm")

        token_type = header.get("typ")
        if token_type is not None and str(token_type).upper() not in VALID_JWT_TYPES:
            raise JWTVerificationError("Unexpected JWT type")

        return header

    def _select_sources(
        self, header: Mapping[str, Any], source_name: str | None = None
    ) -> list[JWTSource]:
        if source_name is not None:
            source = self._sources_by_name.get(source_name)
            if source is None:
                raise JWTVerificationError(f"Unknown JWT source {source_name!r}")
            if not source.matches_header(header):
                raise JWTVerificationError("Token header does not match the requested JWT source")
            return [source]

        matches = [source for source in self._sources if source.matches_header(header)]
        if not matches:
            raise JWTVerificationError("No trusted JWT source matched the token header")
        return matches


class FlaskJWTAuth:
    def __init__(
        self,
        app: Flask | None = None,
        *,
        sources: Sequence[JWTSource | Mapping[str, Any]] | None = None,
        config_key: str = "JWT_SOURCES",
    ) -> None:
        self.config_key = config_key
        self.verifier: MultiSourceJWTVerifier | None = None
        if app is not None:
            self.init_app(app, sources=sources)

    def init_app(
        self,
        app: Flask,
        *,
        sources: Sequence[JWTSource | Mapping[str, Any]] | None = None,
    ) -> None:
        configs = sources if sources is not None else app.config.get(self.config_key, ())
        self.verifier = MultiSourceJWTVerifier(configs)
        app.extensions["flask-jwt-auth-wrapper"] = self

        @app.errorhandler(JWTVerificationError)
        def handle_jwt_error(exc: JWTVerificationError) -> tuple[Any, int]:
            return jsonify({"error": "invalid_token", "message": str(exc)}), 401

    def verify_token(self, token: str, source_name: str | None = None) -> dict[str, Any]:
        return self._require_verifier().verify_token(token, source_name=source_name)

    def verify_request(self, source_name: str | None = None) -> dict[str, Any]:
        return self._require_verifier().verify_request(source_name=source_name)

    def jwt_required(self, source_name: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._require_verifier().jwt_required(source_name=source_name)

    @staticmethod
    def get_jwt_payload() -> dict[str, Any]:
        payload = getattr(g, "jwt_payload", None)
        if payload is None:
            raise RuntimeError("JWT payload is only available during a verified request")
        return payload

    @staticmethod
    def get_jwt_source() -> str:
        source = getattr(g, "jwt_source", None)
        if source is None:
            raise RuntimeError("JWT source is only available during a verified request")
        return source

    def _require_verifier(self) -> MultiSourceJWTVerifier:
        if self.verifier is None:
            raise RuntimeError("FlaskJWTAuth has not been initialized")
        return self.verifier


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JWT_SOURCES"] = _load_sources_from_environment()

    jwt_auth = FlaskJWTAuth(app)

    @app.get("/health")
    def health() -> tuple[Any, int]:
        return jsonify({"status": "ok", "sources": list(jwt_auth.verifier.source_names)}), 200

    @app.get("/verify")
    @jwt_auth.jwt_required()
    def verify() -> tuple[Any, int]:
        return (
            jsonify(
                {
                    "source": jwt_auth.get_jwt_source(),
                    "payload": jwt_auth.get_jwt_payload(),
                }
            ),
            200,
        )

    @app.get("/verify/internal")
    @jwt_auth.jwt_required(source_name="internal-hs256")
    def verify_internal() -> tuple[Any, int]:
        return jsonify({"payload": jwt_auth.get_jwt_payload()}), 200

    @app.get("/verify/public")
    @jwt_auth.jwt_required(source_name="public-rs256")
    def verify_public() -> tuple[Any, int]:
        return jsonify({"payload": jwt_auth.get_jwt_payload()}), 200

    return app


def _load_sources_from_environment() -> list[dict[str, Any]]:
    internal_secret = os.environ.get("INTERNAL_JWT_SECRET")
    public_key = os.environ.get("PUBLIC_API_JWT_PUBLIC_KEY")
    public_jwks_url = os.environ.get("PUBLIC_API_JWKS_URL")

    sources: list[dict[str, Any]] = []

    if internal_secret:
        sources.append(
            {
                "name": "internal-hs256",
                "algorithms": ("HS256",),
                "key": internal_secret,
                "issuer": os.environ.get("INTERNAL_JWT_ISSUER"),
                "audience": os.environ.get("INTERNAL_JWT_AUDIENCE"),
                "required_claims": ("exp", "iat"),
            }
        )

    if public_key or public_jwks_url:
        sources.append(
            {
                "name": "public-rs256",
                "algorithms": ("RS256",),
                "key": public_key,
                "jwks_url": public_jwks_url,
                "issuer": os.environ.get("PUBLIC_API_JWT_ISSUER"),
                "audience": os.environ.get("PUBLIC_API_JWT_AUDIENCE"),
                "required_claims": ("exp", "iat"),
            }
        )

    if not sources:
        raise RuntimeError(
            "Set INTERNAL_JWT_SECRET and/or PUBLIC_API_JWT_PUBLIC_KEY or PUBLIC_API_JWKS_URL"
        )

    return sources


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))