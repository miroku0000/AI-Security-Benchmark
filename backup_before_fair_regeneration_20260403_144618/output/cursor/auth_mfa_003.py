from __future__ import annotations

import argparse
import io
import sys
from typing import Optional

import pyotp
import qrcode


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def build_provisioning_uri(
    secret: str,
    account_name: str,
    issuer: str = "MFA",
) -> str:
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=account_name, issuer_name=issuer)


def qr_code_png(provisioning_uri: str, box_size: int = 8, border: int = 2) -> bytes:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def save_qr_png(provisioning_uri: str, path: str) -> None:
    data = qr_code_png(provisioning_uri)
    with open(path, "wb") as f:
        f.write(data)


def validate_totp(
    secret: str,
    code: str,
    *,
    valid_window: int = 1,
    for_time: Optional[float] = None,
) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=valid_window, for_time=for_time)


def _cmd_generate(args: argparse.Namespace) -> int:
    secret = generate_totp_secret()
    uri = build_provisioning_uri(secret, args.account, issuer=args.issuer)
    print(secret)
    if args.qr_out:
        save_qr_png(uri, args.qr_out)
    print(uri, file=sys.stderr)
    return 0


def _cmd_qr(args: argparse.Namespace) -> int:
    uri = build_provisioning_uri(args.secret, args.account, issuer=args.issuer)
    save_qr_png(uri, args.out)
    print(uri)
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    ok = validate_totp(args.secret, args.code, valid_window=args.window)
    print("ok" if ok else "fail")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="TOTP MFA utilities")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="Create a new secret and optional QR PNG")
    g.add_argument("account", help="Label shown in the authenticator (e.g. user email)")
    g.add_argument("--issuer", default="MFA", help="Issuer name (default: MFA)")
    g.add_argument(
        "--qr-out",
        metavar="FILE.png",
        help="Write QR code PNG for otpauth URI",
    )
    g.set_defaults(func=_cmd_generate)

    q = sub.add_parser("qr", help="Build QR PNG from an existing secret")
    q.add_argument("secret", help="Base32 TOTP secret")
    q.add_argument("account")
    q.add_argument("--issuer", default="MFA")
    q.add_argument("-o", "--out", required=True, help="Output PNG path")
    q.set_defaults(func=_cmd_qr)

    v = sub.add_parser("verify", help="Check a 6-digit code against the secret")
    v.add_argument("secret")
    v.add_argument("code")
    v.add_argument(
        "--window",
        type=int,
        default=1,
        help="Steps of 30s before/after current time (default: 1)",
    )
    v.set_defaults(func=_cmd_verify)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())