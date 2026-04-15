import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

import requests


def _admin_base() -> str:
    base = os.environ.get("KONG_ADMIN_URL", "http://127.0.0.1:8001").rstrip("/")
    return base


def _request(
    method: str,
    path: str,
    *,
    json_body: Optional[Dict[str, Any]] = None,
    session: Optional[requests.Session] = None,
    timeout: float = 30.0,
) -> requests.Response:
    url = f"{_admin_base()}{path}"
    s = session or requests
    kwargs: Dict[str, Any] = {"timeout": timeout}
    if json_body is not None:
        kwargs["json"] = json_body
    return s.request(method.upper(), url, **kwargs)


def kong_post(
    path: str,
    body: Dict[str, Any],
    *,
    session: Optional[requests.Session] = None,
    allow_status: Optional[List[int]] = None,
) -> Dict[str, Any]:
    allow = set(allow_status or [])
    r = _request("POST", path, json_body=body, session=session)
    if r.status_code >= 400 and r.status_code not in allow:
        detail = r.text
        try:
            detail = json.dumps(r.json(), indent=2)
        except ValueError:
            pass
        raise RuntimeError(f"Kong POST {path} failed: {r.status_code}\n{detail}")
    if r.status_code == 204 or not r.content:
        return {}
    try:
        return r.json()
    except ValueError:
        return {}


def create_upstream(
    name: str,
    *,
    algorithm: str = "round-robin",
    hash_on: str = "none",
    hash_fallback: str = "none",
    healthchecks: Optional[Dict[str, Any]] = None,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "name": name,
        "algorithm": algorithm,
        "hash_on": hash_on,
        "hash_fallback": hash_fallback,
    }
    if healthchecks is not None:
        body["healthchecks"] = healthchecks
    return kong_post("/upstreams", body, session=session, allow_status=[409])


def add_upstream_target(
    upstream_name: str,
    target: str,
    *,
    weight: int = 100,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    path = f"/upstreams/{requests.utils.quote(upstream_name, safe='')}/targets"
    body = {"target": target, "weight": weight}
    return kong_post(path, body, session=session)


def create_service(
    name: str,
    *,
    host: str,
    port: int = 80,
    protocol: str = "http",
    path: str = "/",
    connect_timeout: Optional[int] = None,
    write_timeout: Optional[int] = None,
    read_timeout: Optional[int] = None,
    retries: Optional[int] = None,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "name": name,
        "host": host,
        "port": port,
        "protocol": protocol,
        "path": path or "/",
    }
    if connect_timeout is not None:
        body["connect_timeout"] = connect_timeout
    if write_timeout is not None:
        body["write_timeout"] = write_timeout
    if read_timeout is not None:
        body["read_timeout"] = read_timeout
    if retries is not None:
        body["retries"] = retries
    return kong_post("/services", body, session=session, allow_status=[409])


def create_route(
    service_name: str,
    *,
    name: Optional[str] = None,
    paths: Optional[List[str]] = None,
    hosts: Optional[List[str]] = None,
    methods: Optional[List[str]] = None,
    strip_path: bool = True,
    preserve_host: bool = False,
    protocols: Optional[List[str]] = None,
    regex_priority: Optional[int] = None,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    spath = f"/services/{requests.utils.quote(service_name, safe='')}/routes"
    body: Dict[str, Any] = {"strip_path": strip_path, "preserve_host": preserve_host}
    if name:
        body["name"] = name
    if paths:
        body["paths"] = paths
    if hosts:
        body["hosts"] = hosts
    if methods:
        body["methods"] = methods
    if protocols:
        body["protocols"] = protocols
    if regex_priority is not None:
        body["regex_priority"] = regex_priority
    if not paths and not hosts and not methods:
        body["paths"] = ["/"]
    return kong_post(spath, body, session=session, allow_status=[409])


def apply_spec(spec: Dict[str, Any], *, dry_run: bool = False) -> None:
    session = requests.Session()
    headers: Dict[str, str] = {}
    token = os.environ.get("KONG_ADMIN_TOKEN")
    if token:
        headers["Kong-Admin-Token"] = token
    session.headers.update(headers)

    if dry_run:
        print(json.dumps(spec, indent=2))
        return

    for up in spec.get("upstreams", []):
        uname = up["name"]
        create_upstream(
            uname,
            algorithm=up.get("algorithm", "round-robin"),
            hash_on=up.get("hash_on", "none"),
            hash_fallback=up.get("hash_fallback", "none"),
            healthchecks=up.get("healthchecks"),
            session=session,
        )
        for t in up.get("targets", []):
            if isinstance(t, str):
                add_upstream_target(uname, t, session=session)
            else:
                add_upstream_target(
                    uname,
                    t["target"],
                    weight=int(t.get("weight", 100)),
                    session=session,
                )

    for svc in spec.get("services", []):
        sname = svc["name"]
        host = svc.get("host") or svc.get("upstream")
        if not host:
            raise ValueError(f"service {sname!r} needs host or upstream")
        create_service(
            sname,
            host=host,
            port=int(svc.get("port", 80)),
            protocol=svc.get("protocol", "http"),
            path=svc.get("path", "/"),
            connect_timeout=svc.get("connect_timeout"),
            write_timeout=svc.get("write_timeout"),
            read_timeout=svc.get("read_timeout"),
            retries=svc.get("retries"),
            session=session,
        )
        for rt in svc.get("routes", []):
            create_route(
                sname,
                name=rt.get("name"),
                paths=rt.get("paths"),
                hosts=rt.get("hosts"),
                methods=rt.get("methods"),
                strip_path=bool(rt.get("strip_path", True)),
                preserve_host=bool(rt.get("preserve_host", False)),
                protocols=rt.get("protocols"),
                regex_priority=rt.get("regex_priority"),
                session=session,
            )


def _default_spec() -> Dict[str, Any]:
    return {
        "upstreams": [
            {
                "name": "example-upstream",
                "targets": ["127.0.0.1:3000", {"target": "127.0.0.1:3001", "weight": 50}],
            }
        ],
        "services": [
            {
                "name": "example-api",
                "upstream": "example-upstream",
                "protocol": "http",
                "port": 80,
                "path": "/",
                "routes": [
                    {
                        "name": "example-api-route",
                        "paths": ["/api"],
                        "strip_path": True,
                    }
                ],
            }
        ],
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Configure Kong via Admin API")
    p.add_argument(
        "-f",
        "--file",
        help="JSON file with upstreams/services/routes spec",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved spec JSON only",
    )
    args = p.parse_args()
    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            spec = json.load(fh)
    else:
        spec = _default_spec()
    try:
        apply_spec(spec, dry_run=args.dry_run)
    except (RuntimeError, ValueError, OSError, json.JSONDecodeError) as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())