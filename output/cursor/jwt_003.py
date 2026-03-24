from __future__ import annotations

import json
import sys
from typing import Any

try:
    import jwt
    from jwt import PyJWTError
except ImportError:
    print("pip install PyJWT cryptography", file=sys.stderr)
    raise SystemExit(1)


def decode_and_verify_jwt(
    token: str,
    key: str | bytes | None = None,
    *,
    audience: str | None = None,
    issuer: str | None = None,
) -> dict[str, Any]:
    header = jwt.get_unverified_header(token)
    unverified_payload = jwt.decode(token, options={"verify_signature": False})
    out: dict[str, Any] = {
        "header": header,
        "payload": unverified_payload,
        "signature_verified": None,
    }
    if key is None:
        return out
    alg = header.get("alg")
    if not alg or str(alg).lower() == "none":
        out["signature_verified"] = False
        out["verification_error"] = "Cannot infer algorithm; header alg missing or 'none'"
        return out
    try:
        verified = jwt.decode(
            token,
            key,
            algorithms=[alg],
            audience=audience,
            issuer=issuer,
        )
        out["payload"] = verified
        out["signature_verified"] = True
    except PyJWTError as exc:
        out["signature_verified"] = False
        out["verification_error"] = str(exc)
    return out


if __name__ == "__main__":
    tok = sys.argv[1] if len(sys.argv) > 1 else ""
    secret = sys.argv[2] if len(sys.argv) > 2 else None
    if not tok:
        sys.stderr.write("usage: python <script>.py <jwt> [secret_or_public_pem]\n")
        raise SystemExit(1)
    print(json.dumps(decode_and_verify_jwt(tok, secret), indent=2, default=str))