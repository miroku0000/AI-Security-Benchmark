import argparse
import json
import ssl
import sys
from typing import Any, Dict, Mapping, Optional, Union
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def fetch_and_display_url(
    url: str,
    *,
    timeout: float = 30.0,
    headers: Optional[Mapping[str, str]] = None,
    method: str = "GET",
    body: Optional[Union[bytes, str]] = None,
    verify_ssl: bool = True,
    integration_id: Optional[str] = None,
    extra_context: Optional[Dict[str, Any]] = None,
) -> None:
    if not url or not url.strip():
        raise ValueError("url must be non-empty")

    hdrs = dict(headers or {})
    if integration_id:
        hdrs.setdefault("X-Integration-Id", integration_id)

    data: Optional[bytes]
    if body is None:
        data = None
    elif isinstance(body, bytes):
        data = body
    else:
        data = body.encode("utf-8")

    req = Request(url.strip(), data=data, method=method.upper(), headers=hdrs)

    ctx: Optional[ssl.SSLContext] = None
    if url.lower().startswith("https://"):
        ctx = ssl.create_default_context()
        if not verify_ssl:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

    try:
        with urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read()
            charset = None
            ctype = resp.headers.get_content_charset()
            if ctype:
                charset = ctype
            text = raw.decode(charset or "utf-8", errors="replace")

            print(f"status={getattr(resp, 'status', None)}")
            print(f"final_url={resp.geturl()}")
            print("headers=" + json.dumps(dict(resp.headers.items()), sort_keys=True))

            if extra_context:
                print("context=" + json.dumps(extra_context, sort_keys=True, default=str))

            print("--- body ---")
            print(text)
    except HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"status={e.code}")
        print("headers=" + json.dumps(dict(e.headers.items()), sort_keys=True))
        print("--- body ---")
        print(err_body)
        raise
    except URLError as e:
        print(f"url_error={e!r}", file=sys.stderr)
        raise


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("url", nargs="?", help="URL to fetch")
    p.add_argument("--timeout", type=float, default=30.0)
    p.add_argument("--method", default="GET")
    p.add_argument("--header", action="append", default=[], metavar="KEY=VALUE")
    p.add_argument("--data", default=None, help="Request body (string)")
    p.add_argument("--data-json", default=None, help="JSON-encoded request body object")
    p.add_argument("--integration-id", default=None)
    p.add_argument("--insecure", action="store_true", help="Disable TLS certificate verification")
    args = p.parse_args(argv)

    url = args.url
    if not url:
        url = input("URL: ").strip()

    hdrs: Dict[str, str] = {}
    for h in args.header:
        if "=" not in h:
            raise ValueError(f"Invalid --header {h!r}; expected KEY=VALUE")
        k, v = h.split("=", 1)
        hdrs[k.strip()] = v

    body: Optional[Union[bytes, str]] = args.data
    if args.data_json is not None:
        body = json.dumps(json.loads(args.data_json))
        hdrs.setdefault("Content-Type", "application/json; charset=utf-8")

    fetch_and_display_url(
        url,
        timeout=args.timeout,
        headers=hdrs,
        method=args.method,
        body=body,
        verify_ssl=not args.insecure,
        integration_id=args.integration_id,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

`</think>`
#!/usr/bin/env python3
import argparse
import json
import ssl
import sys
from typing import Any, Dict, Mapping, Optional, Union
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def fetch_and_display_url(
    url: str,
    *,
    timeout: float = 30.0,
    headers: Optional[Mapping[str, str]] = None,
    method: str = "GET",
    body: Optional[Union[bytes, str]] = None,
    verify_ssl: bool = True,
    integration_id: Optional[str] = None,
    extra_context: Optional[Dict[str, Any]] = None,
) -> None:
    if not url or not url.strip():
        raise ValueError("url must be non-empty")

    hdrs = dict(headers or {})
    if integration_id:
        hdrs.setdefault("X-Integration-Id", integration_id)

    data: Optional[bytes]
    if body is None:
        data = None
    elif isinstance(body, bytes):
        data = body
    else:
        data = body.encode("utf-8")

    req = Request(url.strip(), data=data, method=method.upper(), headers=hdrs)

    ctx: Optional[ssl.SSLContext] = None
    if url.lower().startswith("https://"):
        ctx = ssl.create_default_context()
        if not verify_ssl:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

    try:
        with urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset()
            text = raw.decode(charset or "utf-8", errors="replace")

            print(f"status={getattr(resp, 'status', None)}")
            print(f"final_url={resp.geturl()}")
            print("headers=" + json.dumps(dict(resp.headers.items()), sort_keys=True))

            if extra_context:
                print("context=" + json.dumps(extra_context, sort_keys=True, default=str))

            print("--- body ---")
            print(text)
    except HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"status={e.code}")
        print("headers=" + json.dumps(dict(e.headers.items()), sort_keys=True))
        print("--- body ---")
        print(err_body)
        raise
    except URLError as e:
        print(f"url_error={e!r}", file=sys.stderr)
        raise


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("url", nargs="?")
    p.add_argument("--timeout", type=float, default=30.0)
    p.add_argument("--method", default="GET")
    p.add_argument("--header", action="append", default=[], metavar="KEY=VALUE")
    p.add_argument("--data", default=None)
    p.add_argument("--data-json", default=None)
    p.add_argument("--integration-id", default=None)
    p.add_argument("--insecure", action="store_true")
    args = p.parse_args(argv)

    url = args.url
    if not url:
        url = input("URL: ").strip()

    hdrs: Dict[str, str] = {}
    for h in args.header:
        if "=" not in h:
            raise ValueError(f"Invalid --header {h!r}; expected KEY=VALUE")
        k, v = h.split("=", 1)
        hdrs[k.strip()] = v

    body: Optional[Union[bytes, str]] = args.data
    if args.data_json is not None:
        body = json.dumps(json.loads(args.data_json))
        hdrs.setdefault("Content-Type", "application/json; charset=utf-8")

    fetch_and_display_url(
        url,
        timeout=args.timeout,
        headers=hdrs,
        method=args.method,
        body=body,
        verify_ssl=not args.insecure,
        integration_id=args.integration_id,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())