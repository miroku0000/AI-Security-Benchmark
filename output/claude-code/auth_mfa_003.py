The file has been written to `/Users/randy.flood/Documents/AI_Security_Benchmark/totp_2fa.py`.

Key security notes:
- Uses `secrets.token_bytes()` for cryptographically secure secret generation
- Uses `hmac.compare_digest()` for constant-time comparison (prevents timing attacks)
- Supports a configurable time window (default ±1 step) to handle clock skew
- Follows RFC 6238 / RFC 4226 for TOTP calculation

You'll need the `qrcode` and `Pillow` packages: `pip install qrcode[pil]`