import argparse
import json
import sys
from typing import Any, Optional

try:
    import jwt
except ImportError:
    print("Install PyJWT: pip install PyJWT", file=sys.stderr)
    sys.exit(1)


def decode_jwt_debug(
    token: str,
    secret: Optional[str] = None,
    algorithms: Optional[list[str]] = None,
    verify: bool = True,
    audience: Optional[str] = None,
    issuer: Optional[str] = None,
) -> dict[str, Any]:
    token = token.strip()
    if not token:
        raise ValueError("empty token")

    if verify and secret:
        algs = algorithms or ["HS256", "HS384", "HS512", "RS256", "ES256"]
        kwargs: dict[str, Any] = {"algorithms": algs, "options": {"verify_signature": True}}
        if audience is not None:
            kwargs["audience"] = audience
        if issuer is not None:
            kwargs["issuer"] = issuer
        payload = jwt.decode(token, secret, **kwargs)
        header = jwt.get_unverified_header(token)
        return {"verified": True, "header": header, "payload": payload}

    header = jwt.get_unverified_header(token)
    payload = jwt.decode(
        token,
        "",
        options={"verify_signature": False},
        algorithms=["none", "HS256", "HS384", "HS512", "RS256", "ES256"],
    )
    return {"verified": False, "header": header, "payload": payload}


def _main() -> None:
    p = argparse.ArgumentParser(description="Decode/verify JWT for debugging")
    p.add_argument("token", nargs="?", help="JWT string (or read from stdin if omitted)")
    p.add_argument("-s", "--secret", help="Secret or PEM public key for verification")
    p.add_argument("--no-verify", action="store_true", help="Skip signature verification")
    p.add_argument("--audience", help="Expected audience (aud)")
    p.add_argument("--issuer", help="Expected issuer (iss)")
    p.add_argument(
        "-a",
        "--algorithm",
        action="append",
        dest="algorithms",
        help="Allowed algorithm (repeatable); default: common HS*/RS/ES",
    )
    args = p.parse_args()

    raw = args.token
    if raw is None:
        raw = sys.stdin.read()

    try:
        out = decode_jwt_debug(
            raw,
            secret=args.secret,
            algorithms=args.algorithms,
            verify=not args.no_verify,
            audience=args.audience,
            issuer=args.issuer,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    _main()
