"""
Multi-algorithm JWT verification wrapper (HS256, RS256, JWKS-backed RS256).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Sequence, Union

import jwt
from jwt import PyJWKClient

__all__ = [
    "VerifierSpec",
    "MultiAlgorithmJWTVerifier",
    "verify_jwt",
]


KeyType = Union[str, bytes]


@dataclass(frozen=True)
class VerifierSpec:
    """
    Describes how to verify tokens from one issuer/key source.

    For symmetric algorithms (HS256), `key` is the shared secret.
    For asymmetric algorithms (RS256), `key` is PEM-encoded public key.
    If `jwks_uri` is set, the signing key is resolved from JWKS using the token's `kid`
    (RS256/ES256 etc.); `key` is ignored for verification in that case.
    """

    name: str
    algorithms: tuple[str, ...]
    key: Optional[KeyType] = None
    jwks_uri: Optional[str] = None
    issuer: Optional[Union[str, Sequence[str]]] = None
    audience: Optional[Union[str, Sequence[str]]] = None
    kid: Optional[str] = None
    jwks_client_factory: Optional[Callable[[str], PyJWKClient]] = None

    def __post_init__(self) -> None:
        if not self.algorithms:
            raise ValueError("algorithms must be non-empty")
        if self.jwks_uri is None and self.key is None:
            raise ValueError("either key or jwks_uri must be provided")


class MultiAlgorithmJWTVerifier:
    """
    Verifies JWTs against one or more VerifierSpec entries. Only explicitly allowed
    algorithms are considered; the token header's `alg` must match a spec that
    also passes optional issuer/audience/kid constraints before verification is attempted.
    """

    def __init__(
        self,
        specs: Sequence[VerifierSpec],
        *,
        leeway: int = 0,
        options: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self._specs = tuple(specs)
        self._leeway = leeway
        self._options = dict(options) if options else None
        self._jwks_lock = threading.Lock()
        self._jwks_clients: dict[str, PyJWKClient] = {}

    def _get_jwks_client(self, uri: str, factory: Optional[Callable[[str], PyJWKClient]]) -> PyJWKClient:
        with self._jwks_lock:
            if uri not in self._jwks_clients:
                self._jwks_clients[uri] = (factory or PyJWKClient)(uri)
            return self._jwks_clients[uri]

    def _decode_kwargs(
        self,
        spec: VerifierSpec,
        algorithms: list[str],
    ) -> dict[str, Any]:
        kw: dict[str, Any] = {
            "algorithms": algorithms,
            "leeway": self._leeway,
        }
        if spec.issuer is not None:
            kw["issuer"] = spec.issuer
        if spec.audience is not None:
            kw["audience"] = spec.audience
        if self._options is not None:
            kw["options"] = self._options
        return kw

    def verify(self, token: str) -> dict[str, Any]:
        if not token or not isinstance(token, str):
            raise jwt.InvalidTokenError("token must be a non-empty string")

        header = jwt.get_unverified_header(token)
        header_alg = header.get("alg")
        header_kid = header.get("kid")

        if not header_alg:
            raise jwt.InvalidTokenError("token header missing alg")

        last_error: Optional[Exception] = None

        for spec in self._specs:
            if header_alg not in spec.algorithms:
                continue
            if spec.kid is not None and header_kid != spec.kid:
                continue

            algorithms = [header_alg]

            try:
                if spec.jwks_uri:
                    client = self._get_jwks_client(spec.jwks_uri, spec.jwks_client_factory)
                    signing_key = client.get_signing_key_from_jwt(token)
                    payload = jwt.decode(
                        token,
                        signing_key.key,
                        **self._decode_kwargs(spec, algorithms),
                    )
                else:
                    assert spec.key is not None
                    payload = jwt.decode(
                        token,
                        spec.key,
                        **self._decode_kwargs(spec, algorithms),
                    )
                return payload
            except jwt.PyJWTError as exc:
                last_error = exc
                continue

        if last_error is not None:
            raise last_error
        raise jwt.InvalidTokenError("no matching verifier for token alg/kid/issuer constraints")


def verify_jwt(
    token: str,
    specs: Sequence[VerifierSpec],
    *,
    leeway: int = 0,
    options: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    return MultiAlgorithmJWTVerifier(specs, leeway=leeway, options=options).verify(token)
