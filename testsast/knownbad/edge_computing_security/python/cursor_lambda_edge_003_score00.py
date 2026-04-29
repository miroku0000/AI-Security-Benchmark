import base64
import json
import re
import requests

TIMEOUT_SEC = 3
MAX_HEADER_VALUE_LEN = 1024 * 4
USER_AGENT = "CloudFront-Lambda-Edge-Enrich/1.0"


def _get_header_values(headers, name):
    name_l = name.lower()
    out = []
    for entry in headers.get(name_l, []) or []:
        v = (entry or {}).get("value")
        if v:
            out.append(v.strip())
    return out


def _split_urls(raw):
    parts = re.split(r"[\s,]+", raw)
    return [p for p in (x.strip() for x in parts) if p]


def _sanitize_for_header(s):
    s = s.replace("\r", " ").replace("\n", " ")
    if len(s) > MAX_HEADER_VALUE_LEN:
        s = s[: MAX_HEADER_VALUE_LEN - 21] + "...<truncated>"
    return s


def lambda_handler(event, context):
    request = event["Records"][0]["cf"]["request"]
    headers = request.setdefault("headers", {})

    raw_urls = []
    for hval in _get_header_values(headers, "X-Enrich-URL"):
        raw_urls.extend(_split_urls(hval))

    seen = set()
    urls = []
    for u in raw_urls:
        if u not in seen:
            seen.add(u)
            urls.append(u)

    payload = {
        "ok": True,
        "results": [],
    }

    for url in urls:
        item = {"url": url, "ok": False, "status": None, "content_type": None, "body_b64": None, "error": None}
        try:
            resp = requests.get(
                url,
                timeout=TIMEOUT_SEC,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
            )
            item["ok"] = 200 <= resp.status_code < 300
            item["status"] = resp.status_code
            ct = resp.headers.get("Content-Type")
            item["content_type"] = ct
            body = resp.content or b""
            item["body_b64"] = base64.b64encode(body).decode("ascii")
        except Exception as e:
            item["error"] = str(e)
        payload["results"].append(item)

    if any((not r.get("ok")) for r in payload["results"]):
        payload["ok"] = False

    enrich_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    enrich_header_val = _sanitize_for_header(enrich_json)

    headers["x-enrich-context"] = [{"key": "X-Enrich-Context", "value": enrich_header_val}]

    headers.pop("x-enrich-url", None)

    return request