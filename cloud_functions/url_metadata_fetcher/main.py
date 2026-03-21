import ipaddress
import json
import re
import socket
from html import unescape
from typing import Any
from urllib.parse import urlparse

import functions_framework
import requests
from bs4 import BeautifulSoup
from flask import Request, Response

DEFAULT_TIMEOUT = 15
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
USER_AGENT = (
    "Mozilla/5.0 (compatible; LinkPreviewBot/1.0; +https://example.com/bot)"
)


def _unsafe_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _hostname_resolves_to_safe_ips(hostname: str) -> bool:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except OSError:
        return False
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if _unsafe_ip(ip):
            return False
    return bool(infos)


def _is_url_allowed(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.hostname
    if not host:
        return False
    hl = host.lower()
    if hl in ("localhost",) or hl.endswith(".localhost"):
        return False
    try:
        ip = ipaddress.ip_address(hl.strip("[]"))
        return not _unsafe_ip(ip)
    except ValueError:
        pass
    return _hostname_resolves_to_safe_ips(hl)


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _meta_content(soup: BeautifulSoup, **attrs: str) -> str | None:
    tag = soup.find("meta", attrs=attrs)
    if not tag:
        return None
    raw = tag.get("content")
    if raw is None:
        return None
    s = str(raw).strip()
    return _normalize_whitespace(unescape(s)) if s else None


def fetch_url_metadata(url: str) -> dict[str, Any]:
    if not url or not isinstance(url, str):
        raise ValueError("url must be a non-empty string")
    url = url.strip()
    if not _is_url_allowed(url):
        raise ValueError("URL is not allowed")

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    raw = b""
    content_type = ""
    with requests.get(
        url,
        headers=headers,
        timeout=DEFAULT_TIMEOUT,
        stream=True,
        allow_redirects=True,
    ) as resp:
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        ctype = (content_type or "").lower()
        if "html" not in ctype and "xml" not in ctype:
            raise ValueError("Response is not HTML")
        for chunk in resp.iter_content(chunk_size=65536):
            if not chunk:
                continue
            raw += chunk
            if len(raw) >= MAX_RESPONSE_BYTES:
                break

    enc = "utf-8"
    ct = content_type
    m = re.search(r"charset=([\w-]+)", ct, re.I)
    if m:
        enc = m.group(1).strip().strip('"') or enc
    try:
        html = raw.decode(enc)
    except (UnicodeDecodeError, LookupError):
        html = raw.decode("utf-8", errors="replace")

    soup = BeautifulSoup(html, "html.parser")

    open_graph: dict[str, str] = {}
    for meta in soup.find_all("meta", attrs={"property": True}):
        prop = meta.get("property")
        if not prop or not str(prop).startswith("og:"):
            continue
        content = meta.get("content")
        if content is None:
            continue
        v = _normalize_whitespace(unescape(str(content).strip()))
        if v:
            open_graph[str(prop)] = v

    title_tag = soup.find("title")
    doc_title = None
    if title_tag and title_tag.string:
        doc_title = _normalize_whitespace(unescape(title_tag.string))

    og_title = open_graph.get("og:title")
    tw_title = _meta_content(soup, name="twitter:title")
    title = og_title or tw_title or doc_title

    og_desc = open_graph.get("og:description")
    tw_desc = _meta_content(soup, name="twitter:description")
    meta_desc = _meta_content(soup, name="description")
    description = og_desc or tw_desc or meta_desc

    return {
        "url": url,
        "title": title,
        "description": description,
        "open_graph": open_graph,
    }


def _json_response(payload: dict[str, Any], status: int = 200) -> Response:
    body = json.dumps(payload, ensure_ascii=False)
    return Response(
        body,
        status=status,
        mimetype="application/json; charset=utf-8",
    )


@functions_framework.http
def url_metadata(request: Request) -> Response:
    if request.method == "OPTIONS":
        return Response(
            "",
            status=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Max-Age": "3600",
            },
        )

    cors = {"Access-Control-Allow-Origin": "*"}
    target = None
    if request.method == "GET":
        target = request.args.get("url")
    elif request.method == "POST":
        ct = (request.content_type or "").lower()
        if "application/json" in ct:
            data = request.get_json(silent=True) or {}
            target = data.get("url")
        else:
            target = request.form.get("url")
    else:
        return _json_response({"error": "Method not allowed"}, 405)

    if not target:
        r = _json_response({"error": "Missing url parameter"}, 400)
        for k, v in cors.items():
            r.headers[k] = v
        return r

    try:
        result = fetch_url_metadata(target)
    except ValueError as e:
        r = _json_response({"error": str(e)}, 400)
        for k, v in cors.items():
            r.headers[k] = v
        return r
    except requests.RequestException as e:
        r = _json_response({"error": f"Request failed: {e!s}"}, 502)
        for k, v in cors.items():
            r.headers[k] = v
        return r

    r = _json_response(result, 200)
    for k, v in cors.items():
        r.headers[k] = v
    return r
