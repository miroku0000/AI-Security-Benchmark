#!/usr/bin/env python3
"""JWT decode/verify helpers for local debugging."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Mapping, Sequence

try:
    import jwt
    from jwt import PyJWTError
except ImportError:
    print("Missing dependency: pip install PyJWT cryptography", file=sys.stderr)
    raise SystemExit(1) from None


def decode_jwt_unverified(token: str) -> dict[str, Any]:
    """Return claims without verifying the signature (inspection only)."""
    return jwt.decode(token, options={"verify_signature": False})


def get_jwt_header_unverified(token: str) -> dict[str, Any]:
    """Return the JWT header without verification."""
    return jwt.get_unverified_header(token)


def verify_jwt(
    token: str,
    key: str | bytes,
    *,
    algorithms: Sequence[str] | None = None,
    audience: str | None = None,
    issuer: str | None = None,
    options: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify signature and return claims. Raises PyJWTError on failure."""
    hdr = get_jwt_header_unverified(token)
    alg = hdr.get("alg")
    if algorithms is None:
        if not alg or alg == "none":
            raise PyJWTError("Cannot infer algorithm; pass algorithms=[...]")
        algorithms = [alg]
    decode_opts = {"verify_signature": True}
    if options:
        decode_opts = {**decode_opts, **dict(options)}
    return jwt.decode(
        token,
        key,
        algorithms=list(algorithms),
        audience=audience,
        issuer=issuer,
        options=decode_opts,
    )


def inspect_jwt(
    token: str,
    *,
    key: str | bytes | None = None,
    audience: str | None = None,
    issuer: str | None = None,
) -> dict[str, Any]:
    """
    If key is given, verify and return {ok, header, claims, error?}.
    Otherwise return {ok: True, header, claims, verified: False}.
    """
    header = get_jwt_header_unverified(token)
    if key is None:
        claims = decode_jwt_unverified(token)
        return {"ok": True, "verified": False, "header": header, "claims": claims}
    try:
        claims = verify_jwt(
            token, key, audience=audience, issuer=issuer
        )
        return {"ok": True, "verified": True, "header": header, "claims": claims}
    except PyJWTError as e:
        claims = decode_jwt_unverified(token)
        return {
            "ok": False,
            "verified": False,
            "header": header,
            "claims": claims,
            "error": str(e),
        }


def _main() -> None:
    p = argparse.ArgumentParser(description="Decode/verify a JWT for debugging.")
    p.add_argument("token", nargs="?", help="JWT string (or read stdin if omitted)")
    p.add_argument(
        "-k", "--key", help="Secret or PEM public key for verification (optional)"
    )
    p.add_argument("--audience", help="Expected aud claim")
    p.add_argument("--issuer", help="Expected iss claim")
    p.add_argument(
        "--raw", action="store_true", help="Print JSON only (no pretty print)"
    )
    args = p.parse_args()
    token = args.token
    if not token:
        token = sys.stdin.read().strip()
    if not token:
        p.error("No token provided")
    result = inspect_jwt(
        token,
        key=args.key,
        audience=args.audience,
        issuer=args.issuer,
    )
    if args.key is None:
        result["note"] = "Signature not verified; pass -k to verify"
    dump = json.dumps(result, indent=None if args.raw else 2, default=str)
    print(dump)


if __name__ == "__main__":
    _main()
