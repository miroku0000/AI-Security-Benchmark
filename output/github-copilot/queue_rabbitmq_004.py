#!/usr/bin/env python3

import argparse
import json
import os
import ssl
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, build_opener, HTTPSHandler, HTTPBasicAuthHandler, HTTPPasswordMgrWithDefaultRealm


@dataclass
class PermissionSpec:
    configure: str = ".*"
    write: str = ".*"
    read: str = ".*"


@dataclass
class TopicPermissionSpec:
    exchange: str
    write: str = ".*"
    read: str = ".*"


@dataclass
class UserSpec:
    name: str
    password: str
    tags: List[str] = field(default_factory=list)
    permissions: PermissionSpec = field(default_factory=PermissionSpec)
    topic_permissions: List[TopicPermissionSpec] = field(default_factory=list)


@dataclass
class TenantSpec:
    application: str
    vhost: str
    description: str = ""
    tracing: bool = False
    users: List[UserSpec] = field(default_factory=list)


class RabbitMQAPIError(RuntimeError):
    pass


class RabbitMQManagementClient:
    def __init__(self, base_url: str, username: str, password: str, verify_tls: bool = True, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        password_mgr = HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, self.base_url, username, password)
        auth_handler = HTTPBasicAuthHandler(password_mgr)

        handlers = [auth_handler]
        if self.base_url.startswith("https://"):
            if verify_tls:
                ssl_context = ssl.create_default_context()
            else:
                ssl_context = ssl._create_unverified_context()
            handlers.append(HTTPSHandler(context=ssl_context))

        self.opener = build_opener(*handlers)

    def request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Accept": "application/json"}

        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = Request(url=url, data=data, headers=headers, method=method)

        try:
            with self.opener.open(req, timeout=self.timeout) as resp:
                body = resp.read()
                if not body:
                    return None
                content_type = resp.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    return json.loads(body.decode("utf-8"))
                return body.decode("utf-8")
        except HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RabbitMQAPIError(f"{method} {url} failed with HTTP {exc.code}: {details}") from exc
        except URLError as exc:
            raise RabbitMQAPIError(f"{method} {url} failed: {exc.reason}") from exc

    def health_check(self) -> None:
        self.request("GET", "/api/overview")

    def create_vhost(self, vhost: str, description: str = "", tracing: bool = False) -> None:
        self.request(
            "PUT",
            f"/api/vhosts/{quote(vhost, safe='')}",
            {"description": description, "tracing": tracing},
        )

    def create_or_update_user(self, username: str, password: str, tags: Iterable[str]) -> None:
        self.request(
            "PUT",
            f"/api/users/{quote(username, safe='')}",
            {"password": password, "tags": ",".join(tag for tag in tags if tag)},
        )

    def set_permissions(self, vhost: str, username: str, permissions: PermissionSpec) -> None:
        self.request(
            "PUT",
            f"/api/permissions/{quote(vhost, safe='')}/{quote(username, safe='')}",
            {
                "configure": permissions.configure,
                "write": permissions.write,
                "read": permissions.read,
            },
        )

    def set_topic_permissions(self, vhost: str, username: str, topic_permission: TopicPermissionSpec) -> None:
        self.request(
            "PUT",
            f"/api/topic-permissions/{quote(vhost, safe='')}/{quote(username, safe='')}",
            {
                "exchange": topic_permission.exchange,
                "write": topic_permission.write,
                "read": topic_permission.read,
            },
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Configure RabbitMQ virtual hosts, users, and permissions via the Management HTTP API."
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to a JSON configuration file describing tenants, vhosts, users, and permissions.",
    )
    parser.add_argument(
        "--url",
        default=os.getenv("RABBITMQ_API_URL", "http://localhost:15672"),
        help="RabbitMQ Management API base URL. Default: env RABBITMQ_API_URL or http://localhost:15672",
    )
    parser.add_argument(
        "--admin-user",
        default=os.getenv("RABBITMQ_API_USERNAME", os.getenv("RABBITMQ_DEFAULT_USER")),
        help="RabbitMQ Management API username. Default: env RABBITMQ_API_USERNAME or RABBITMQ_DEFAULT_USER",
    )
    parser.add_argument(
        "--admin-password",
        default=os.getenv("RABBITMQ_API_PASSWORD", os.getenv("RABBITMQ_DEFAULT_PASS")),
        help="RabbitMQ Management API password. Default: env RABBITMQ_API_PASSWORD or RABBITMQ_DEFAULT_PASS",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification for HTTPS endpoints.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.getenv("RABBITMQ_API_TIMEOUT", "30")),
        help="HTTP timeout in seconds. Default: env RABBITMQ_API_TIMEOUT or 30",
    )
    return parser.parse_args()


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def require_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{field_name}' must be a non-empty string")
    return value


def parse_permissions(raw: Dict[str, Any], field_name: str = "permissions") -> PermissionSpec:
    if raw is None:
        return PermissionSpec()
    if not isinstance(raw, dict):
        raise ValueError(f"'{field_name}' must be an object")
    return PermissionSpec(
        configure=str(raw.get("configure", ".*")),
        write=str(raw.get("write", ".*")),
        read=str(raw.get("read", ".*")),
    )


def parse_topic_permissions(raw: Any) -> List[TopicPermissionSpec]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("'topic_permissions' must be an array")
    parsed: List[TopicPermissionSpec] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"'topic_permissions[{idx}]' must be an object")
        exchange = require_str(item.get("exchange"), f"topic_permissions[{idx}].exchange")
        parsed.append(
            TopicPermissionSpec(
                exchange=exchange,
                write=str(item.get("write", ".*")),
                read=str(item.get("read", ".*")),
            )
        )
    return parsed


def parse_user(raw: Dict[str, Any], tenant_name: str, idx: int) -> UserSpec:
    if not isinstance(raw, dict):
        raise ValueError(f"'tenants[{tenant_name}].users[{idx}]' must be an object")

    name = require_str(raw.get("name"), f"tenants[{tenant_name}].users[{idx}].name")
    password = require_str(raw.get("password"), f"tenants[{tenant_name}].users[{idx}].password")

    tags_raw = raw.get("tags", [])
    if tags_raw is None:
        tags = []
    elif isinstance(tags_raw, list) and all(isinstance(tag, str) for tag in tags_raw):
        tags = tags_raw
    else:
        raise ValueError(f"'tenants[{tenant_name}].users[{idx}].tags' must be an array of strings")

    permissions = parse_permissions(raw.get("permissions"), f"tenants[{tenant_name}].users[{idx}].permissions")
    topic_permissions = parse_topic_permissions(raw.get("topic_permissions"))

    return UserSpec(
        name=name,
        password=password,
        tags=tags,
        permissions=permissions,
        topic_permissions=topic_permissions,
    )


def parse_tenant(raw: Dict[str, Any], idx: int) -> TenantSpec:
    if not isinstance(raw, dict):
        raise ValueError(f"'tenants[{idx}]' must be an object")

    application = require_str(raw.get("application"), f"tenants[{idx}].application")
    vhost = require_str(raw.get("vhost"), f"tenants[{idx}].vhost")
    description = str(raw.get("description", f"Virtual host for {application}"))
    tracing = bool(raw.get("tracing", False))

    users_raw = raw.get("users", [])
    if not isinstance(users_raw, list) or not users_raw:
        raise ValueError(f"'tenants[{idx}].users' must be a non-empty array")

    users = [parse_user(user_raw, application, user_idx) for user_idx, user_raw in enumerate(users_raw)]

    return TenantSpec(
        application=application,
        vhost=vhost,
        description=description,
        tracing=tracing,
        users=users,
    )


def parse_config(config: Dict[str, Any]) -> List[TenantSpec]:
    tenants_raw = config.get("tenants")
    if not isinstance(tenants_raw, list) or not tenants_raw:
        raise ValueError("'tenants' must be a non-empty array")
    return [parse_tenant(raw, idx) for idx, raw in enumerate(tenants_raw)]


def configure_tenants(client: RabbitMQManagementClient, tenants: List[TenantSpec]) -> None:
    for tenant in tenants:
        client.create_vhost(tenant.vhost, description=tenant.description, tracing=tenant.tracing)
        for user in tenant.users:
            client.create_or_update_user(user.name, user.password, user.tags)
            client.set_permissions(tenant.vhost, user.name, user.permissions)
            for topic_permission in user.topic_permissions:
                client.set_topic_permissions(tenant.vhost, user.name, topic_permission)


def main() -> int:
    args = parse_args()

    if not args.admin_user:
        print("error: missing RabbitMQ admin username; use --admin-user or set RABBITMQ_API_USERNAME", file=sys.stderr)
        return 2
    if not args.admin_password:
        print("error: missing RabbitMQ admin password; use --admin-password or set RABBITMQ_API_PASSWORD", file=sys.stderr)
        return 2

    try:
        config = load_config(args.config)
        tenants = parse_config(config)
        client = RabbitMQManagementClient(
            base_url=args.url,
            username=args.admin_user,
            password=args.admin_password,
            verify_tls=not args.insecure,
            timeout=args.timeout,
        )
        client.health_check()
        configure_tenants(client, tenants)
        return 0
    except (OSError, ValueError, json.JSONDecodeError, RabbitMQAPIError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())