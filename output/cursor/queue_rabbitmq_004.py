from __future__ import annotations

import base64
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import quote


@dataclass(frozen=True)
class Tenant:
    vhost: str
    username: str
    password: str
    configure: str = ".*"
    write: str = ".*"
    read: str = ".*"


def _basic_auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def _api_url(base: str, *parts: str) -> str:
    base = base.rstrip("/")
    encoded = "/".join(quote(p, safe="") for p in parts)
    return f"{base}/{encoded}"


def _request(
    method: str,
    url: str,
    *,
    auth_header: str,
    body: dict | None = None,
    verify_tls: bool = True,
) -> tuple[int, str]:
    data = None
    headers = {"Authorization": auth_header}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    ctx = None
    if url.startswith("https://") and not verify_tls:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, raw


def put_vhost(api_base: str, auth_header: str, vhost: str, verify_tls: bool) -> None:
    url = _api_url(api_base, "api", "vhosts", vhost)
    code, body = _request("PUT", url, auth_header=auth_header, body={}, verify_tls=verify_tls)
    if code not in (201, 204):
        raise RuntimeError(f"create vhost {vhost!r}: HTTP {code} {body}")


def put_user(
    api_base: str,
    auth_header: str,
    username: str,
    password: str,
    tags: str,
    verify_tls: bool,
) -> None:
    url = _api_url(api_base, "api", "users", username)
    payload = {"password": password, "tags": tags}
    code, body = _request("PUT", url, auth_header=auth_header, body=payload, verify_tls=verify_tls)
    if code not in (201, 204):
        raise RuntimeError(f"create user {username!r}: HTTP {code} {body}")


def put_permissions(
    api_base: str,
    auth_header: str,
    vhost: str,
    username: str,
    configure: str,
    write: str,
    read: str,
    verify_tls: bool,
) -> None:
    url = _api_url(api_base, "api", "permissions", vhost, username)
    payload = {"configure": configure, "write": write, "read": read}
    code, body = _request("PUT", url, auth_header=auth_header, body=payload, verify_tls=verify_tls)
    if code not in (201, 204):
        raise RuntimeError(f"permissions {username!r} on {vhost!r}: HTTP {code} {body}")


def ensure_tenants(
    api_base: str,
    admin_user: str,
    admin_password: str,
    tenants: Iterable[Tenant],
    *,
    verify_tls: bool = True,
    user_tags: str = "",
) -> None:
    auth_header = _basic_auth_header(admin_user, admin_password)
    for t in tenants:
        put_vhost(api_base, auth_header, t.vhost, verify_tls)
        put_user(api_base, auth_header, t.username, t.password, user_tags, verify_tls)
        put_permissions(
            api_base,
            auth_header,
            t.vhost,
            t.username,
            t.configure,
            t.write,
            t.read,
            verify_tls,
        )


def main() -> int:
    host = os.environ.get("RABBITMQ_HOST", "127.0.0.1")
    port = int(os.environ.get("RABBITMQ_MGMT_PORT", "15672"))
    use_tls = os.environ.get("RABBITMQ_USE_TLS", "").lower() in ("1", "true", "yes")
    verify_tls = os.environ.get("RABBITMQ_VERIFY_TLS", "true").lower() not in ("0", "false", "no")
    scheme = "https" if use_tls else "http"
    api_base = os.environ.get("RABBITMQ_API_BASE", f"{scheme}://{host}:{port}")

    admin_user = os.environ.get("RABBITMQ_ADMIN_USER", "guest")
    admin_password = os.environ.get("RABBITMQ_ADMIN_PASSWORD", "guest")

    tenants = [
        Tenant(
            vhost="app_billing",
            username="billing_worker",
            password=os.environ.get("RABBITMQ_PASSWORD_BILLING", "change-me-billing"),
        ),
        Tenant(
            vhost="app_notifications",
            username="notifications_api",
            password=os.environ.get("RABBITMQ_PASSWORD_NOTIFICATIONS", "change-me-notifications"),
        ),
        Tenant(
            vhost="app_analytics",
            username="analytics_ingest",
            password=os.environ.get("RABBITMQ_PASSWORD_ANALYTICS", "change-me-analytics"),
        ),
    ]

    try:
        ensure_tenants(api_base, admin_user, admin_password, tenants, verify_tls=verify_tls)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())