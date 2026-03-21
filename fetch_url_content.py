#!/usr/bin/env python3
"""Fetch and display HTTP(S) URL content for webhook/integration use."""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from typing import Any, Mapping, MutableMapping


def fetch_and_display_url(
    url: str,
    *,
    method: str = "GET",
    headers: Mapping[str, str] | None = None,
    body: bytes | None = None,
    timeout: float = 30.0,
    display: bool = True,
) -> tuple[int, dict[str, Any], bytes]:
    """
    Fetch a URL and optionally print status, headers, and body to stdout.
    Returns (status_code, response_headers_dict, response_body_bytes).
    """
    req = urllib.request.Request(
        url,
        data=body,
        method=method.upper(),
        headers=dict(headers or {}),
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            hdrs = {k.lower(): v for k, v in resp.getheaders()}
            raw = resp.read()
    except urllib.error.HTTPError as e:
        status = e.code
        hdrs = {k.lower(): v for k, v in e.headers.items()} if e.headers else {}
        raw = e.read()
    if display:
        print(f"status: {status}", file=sys.stdout)
        print("headers:", file=sys.stdout)
        for k, v in sorted(hdrs.items()):
            print(f"  {k}: {v}", file=sys.stdout)
        print("body:", file=sys.stdout)
        ct = hdrs.get("content-type", "")
        enc = "utf-8"
        if "charset=" in ct:
            enc = ct.split("charset=", 1)[1].split(";")[0].strip().strip('"') or enc
        try:
            text = raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            text = raw.decode("utf-8", errors="replace")
        print(text, file=sys.stdout)
    return status, hdrs, raw


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Fetch and display URL content.")
    p.add_argument("url", help="HTTP or HTTPS URL to fetch")
    p.add_argument("-X", "--request", default="GET", help="HTTP method (default GET)")
    p.add_argument("-H", "--header", action="append", default=[], metavar="KEY: VALUE", help="Request header (repeatable)")
    p.add_argument("-d", "--data", help="Request body as string (UTF-8)")
    p.add_argument("--json", dest="json_body", help="JSON object/array as string; sets Content-Type if not set")
    p.add_argument("-t", "--timeout", type=float, default=30.0)
    p.add_argument("-q", "--quiet", action="store_true", help="Do not print to stdout")
    args = p.parse_args(argv)

    hdrs: MutableMapping[str, str] = {}
    for h in args.header:
        if ":" in h:
            k, v = h.split(":", 1)
            hdrs[k.strip()] = v.strip()
    body: bytes | None = None
    if args.json_body is not None:
        body = args.json_body.encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    elif args.data is not None:
        body = args.data.encode("utf-8")

    fetch_and_display_url(
        args.url,
        method=args.request,
        headers=hdrs,
        body=body,
        timeout=args.timeout,
        display=not args.quiet,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
