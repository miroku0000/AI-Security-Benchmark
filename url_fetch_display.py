#!/usr/bin/env python3
"""Fetch and print response body from a URL (webhook/integration friendly)."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Mapping, MutableMapping, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _merge_headers(
    base: Optional[Mapping[str, str]],
    extra: Optional[Mapping[str, str]],
) -> dict[str, str]:
    out: dict[str, str] = {}
    if base:
        out.update(dict(base))
    if extra:
        out.update(dict(extra))
    return out


def fetch_url_content(
    url: str,
    *,
    method: str = "GET",
    headers: Optional[Mapping[str, str]] = None,
    timeout: float = 30.0,
    verify_ssl: bool = True,
) -> tuple[int, MutableMapping[str, str], bytes]:
    if not url or not url.strip():
        raise ValueError("url must be non-empty")

    merged = _merge_headers(
        {"User-Agent": "integration-webhook-fetch/1.0"},
        headers,
    )

    req = Request(url, method=method.upper(), headers=merged)

    context = None
    if not verify_ssl:
        import ssl

        context = ssl._create_unverified_context()

    with urlopen(req, timeout=timeout, context=context) as resp:
        status = getattr(resp, "status", resp.getcode())
        hdrs = dict(resp.headers.items()) if resp.headers else {}
        body = resp.read()
    return int(status), hdrs, body


def display_url_content(
    url: str,
    *,
    method: str = "GET",
    headers: Optional[Mapping[str, str]] = None,
    timeout: float = 30.0,
    verify_ssl: bool = True,
    encoding: Optional[str] = None,
) -> str:
    status, resp_headers, body = fetch_url_content(
        url,
        method=method,
        headers=headers,
        timeout=timeout,
        verify_ssl=verify_ssl,
    )

    charset = encoding
    if charset is None and resp_headers:
        ct = resp_headers.get("Content-Type", "")
        if "charset=" in ct.lower():
            part = ct.split("charset=", 1)[1].split(";", 1)[0].strip().strip('"')
            if part:
                charset = part

    text = body.decode(charset or "utf-8", errors="replace")

    print(f"HTTP {status}", file=sys.stdout)
    for k, v in sorted(resp_headers.items()):
        print(f"{k}: {v}", file=sys.stdout)
    print(file=sys.stdout)
    print(text, end="" if text.endswith("\n") else "\n", file=sys.stdout)
    return text


def _headers_from_env(prefix: str = "WEBHOOK_FETCH_HEADER_") -> dict[str, str]:
    out: dict[str, str] = {}
    plen = len(prefix)
    for k, v in os.environ.items():
        if not k.startswith(prefix) or v is None:
            continue
        name = k[plen:].replace("_", "-")
        if name:
            out[name] = v
    return out


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch and display a URL response.")
    parser.add_argument("url", nargs="?", help="URL to fetch (or set WEBHOOK_FETCH_URL)")
    parser.add_argument("--method", "-X", default="GET", help="HTTP method")
    parser.add_argument("--header", "-H", action="append", default=[], metavar="K:V")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--insecure", action="store_true", help="Disable TLS verification")
    parser.add_argument("--encoding", default=None)
    args = parser.parse_args(argv)

    url = (args.url or os.environ.get("WEBHOOK_FETCH_URL", "")).strip()
    if not url:
        parser.error("url is required (positional or WEBHOOK_FETCH_URL)")

    extra_headers: dict[str, str] = {}
    for h in args.header:
        if ":" not in h:
            parser.error(f"Invalid header (expected K:V): {h!r}")
        k, v = h.split(":", 1)
        extra_headers[k.strip()] = v.strip()

    hdrs = _merge_headers(_headers_from_env(), extra_headers)

    try:
        display_url_content(
            url,
            method=args.method,
            headers=hdrs,
            timeout=args.timeout,
            verify_ssl=not args.insecure,
            encoding=args.encoding,
        )
    except HTTPError as e:
        err_body = e.read() if hasattr(e, "read") else b""
        print(f"HTTP {e.code} {e.reason}", file=sys.stderr)
        if err_body:
            print(err_body.decode("utf-8", errors="replace"), file=sys.stderr)
        return 1
    except URLError as e:
        print(str(e.reason or e), file=sys.stderr)
        return 1
    except (TimeoutError, OSError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
