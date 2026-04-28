#!/usr/bin/env python3

import argparse
import json
import os
import sys
from typing import Any, Dict, Optional, Sequence

import jwt
from jwt import InvalidTokenError


def _load_value(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    if value.startswith("@"):
        with open(value[1:], "r", encoding="utf-8") as f:
            return f.read()
    return value


def decode_and_verify_jwt(
    token: str,
    *,
    secret: Optional[str] = None,
    public_key: Optional[str] = None,
    algorithms: Optional[Sequence[str]] = None,
    audience: Optional[str] = None,
    issuer: Optional[str] = None,
    leeway: int = 0,
    verify_signature: bool = True,
) -> Dict[str, Any]:
    header = jwt.get_unverified_header(token)
    unverified_payload = jwt.decode(
        token,
        options={
            "verify_signature": False,
            "verify_exp": False,
            "verify_nbf": False,
            "verify_iat": False,
            "verify_aud": False,
            "verify_iss": False,
        },
        algorithms=algorithms or ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512", "ES256", "ES384", "ES512"],
    )

    result: Dict[str, Any] = {
        "header": header,
        "payload_unverified": unverified_payload,
        "payload_verified": None,
        "verified": False,
    }

    if not verify_signature:
        return result

    key = public_key or secret
    if not key:
        raise ValueError("A secret or public key is required when verify_signature=True")

    verified_payload = jwt.decode(
        token,
        key=key,
        algorithms=list(algorithms) if algorithms else [header.get("alg")] if header.get("alg") else None,
        audience=audience,
        issuer=issuer,
        leeway=leeway,
        options={"require": []},
    )

    result["payload_verified"] = verified_payload
    result["verified"] = True
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Decode and optionally verify a JWT for debugging.")
    parser.add_argument("token", help="JWT token string")
    parser.add_argument("--secret", help="HMAC secret, or @path to read from file")
    parser.add_argument("--public-key", help="Public key, or @path to read from file")
    parser.add_argument(
        "--algorithms",
        nargs="+",
        help="Allowed algorithms, e.g. HS256 RS256",
    )
    parser.add_argument("--audience", help="Expected audience claim")
    parser.add_argument("--issuer", help="Expected issuer claim")
    parser.add_argument("--leeway", type=int, default=0, help="Leeway in seconds for time-based claims")
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Decode without verifying signature or claims",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    args = parser.parse_args()

    secret = _load_value(args.secret) or os.getenv("JWT_SECRET")
    public_key = _load_value(args.public_key) or os.getenv("JWT_PUBLIC_KEY")

    try:
        result = decode_and_verify_jwt(
            args.token,
            secret=secret,
            public_key=public_key,
            algorithms=args.algorithms,
            audience=args.audience,
            issuer=args.issuer,
            leeway=args.leeway,
            verify_signature=not args.no_verify,
        )
        if args.pretty:
            print(json.dumps(result, indent=2, sort_keys=True, default=str))
        else:
            print(json.dumps(result, default=str))
        return 0
    except (InvalidTokenError, ValueError, OSError) as exc:
        error = {"verified": False, "error": type(exc).__name__, "message": str(exc)}
        if args.pretty:
            print(json.dumps(error, indent=2, sort_keys=True))
        else:
            print(json.dumps(error))
        return 1


if __name__ == "__main__":
    sys.exit(main())