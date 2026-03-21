from __future__ import annotations

import json
import sys
from typing import Any, Optional

import jwt


def decode_jwt_debug(
    token: str,
    key: Optional[str | bytes] = None,
    *,
    audience: Optional[str] = None,
    issuer: Optional[str] = None,
    verify_signature: bool = True,
    verify_exp: bool = True,
) -> dict[str, Any]:
    token = token.strip()
    header = jwt.get_unverified_header(token)
    unverified_options: dict[str, Any] = {
        "verify_signature": False,
        "verify_exp": False,
    }
    payload_unverified = jwt.decode(token, options=unverified_options)

    out: dict[str, Any] = {
        "header": header,
        "payload_unverified": payload_unverified,
        "verification": None,
    }

    if key is None or not verify_signature:
        return out

    alg = header.get("alg")
    if alg is None or alg.upper() == "NONE":
        out["verification"] = {"ok": False, "error": "alg missing or 'none'; refusing to verify"}
        return out

    decode_kw: dict[str, Any] = {
        "algorithms": [alg],
        "options": {"verify_exp": verify_exp},
    }
    if audience is not None:
        decode_kw["audience"] = audience
    if issuer is not None:
        decode_kw["issuer"] = issuer

    try:
        verified = jwt.decode(token, key, **decode_kw)
        out["verification"] = {"ok": True, "payload": verified}
    except jwt.ExpiredSignatureError as exc:
        out["verification"] = {"ok": False, "error": f"expired: {exc}"}
    except jwt.InvalidSignatureError as exc:
        out["verification"] = {"ok": False, "error": f"invalid signature: {exc}"}
    except jwt.InvalidTokenError as exc:
        out["verification"] = {"ok": False, "error": str(exc)}

    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python -m utils.jwt_debug <jwt> [signing_key]",
            file=sys.stderr,
        )
        sys.exit(2)
    tok = sys.argv[1]
    sec = sys.argv[2] if len(sys.argv) > 2 else None
    result = decode_jwt_debug(tok, key=sec)
    print(json.dumps(result, indent=2, default=str))
