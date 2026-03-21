import base64
import json
import urllib.error
import urllib.request
from urllib.parse import urlparse

MAX_BYTES = 6 * 1024 * 1024
HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def handler(event, context):
    method = (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod")
        or "GET"
    )
    if method == "OPTIONS":
        return {"statusCode": 204, "headers": _cors(), "body": ""}

    body_raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        body_raw = base64.b64decode(body_raw).decode("utf-8", errors="replace")
    try:
        data = json.loads(body_raw) if body_raw.strip() else {}
    except json.JSONDecodeError:
        data = {}

    qs = event.get("queryStringParameters") or {}
    target_url = data.get("url") or qs.get("url")
    if not target_url:
        return _err(400, "missing url")

    p = urlparse(target_url)
    if p.scheme not in ("http", "https") or not p.netloc:
        return _err(400, "invalid url")

    m = (data.get("method") or "GET").upper()
    headers = {
        k: v
        for k, v in (data.get("headers") or {}).items()
        if isinstance(k, str) and isinstance(v, str)
    }
    payload = data.get("body")
    req_data = None
    if m in ("POST", "PUT", "PATCH") and payload is not None:
        if isinstance(payload, (dict, list)):
            req_data = json.dumps(payload).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")
        elif isinstance(payload, str):
            req_data = payload.encode("utf-8")
        else:
            req_data = bytes(payload)

    req = urllib.request.Request(target_url, data=req_data, method=m, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as e:
        resp = e
    except urllib.error.URLError as e:
        return _err(502, str(e.reason))

    try:
        blob = resp.read(MAX_BYTES + 1)
    finally:
        if hasattr(resp, "close"):
            resp.close()

    if len(blob) > MAX_BYTES:
        return _err(413, "response too large")

    status = resp.getcode()
    ct = resp.headers.get("Content-Type", "application/octet-stream")
    text_like = (
        ct.startswith("text/")
        or "json" in ct
        or "xml" in ct
        or "+xml" in ct
        or "javascript" in ct
    )
    if text_like:
        try:
            body_out = blob.decode("utf-8")
            b64 = False
        except UnicodeDecodeError:
            body_out = base64.b64encode(blob).decode("ascii")
            b64 = True
    else:
        body_out = base64.b64encode(blob).decode("ascii")
        b64 = True

    out_h = _cors()
    out_h["Content-Type"] = ct
    for k, v in resp.headers.items():
        lk = k.lower()
        if lk in HOP_BY_HOP:
            continue
        out_h[k] = v

    return {
        "statusCode": status,
        "headers": out_h,
        "body": body_out,
        "isBase64Encoded": b64,
    }


def _cors():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    }


def _err(code, msg):
    return {
        "statusCode": code,
        "headers": {**_cors(), "Content-Type": "application/json"},
        "body": json.dumps({"error": msg}),
    }
