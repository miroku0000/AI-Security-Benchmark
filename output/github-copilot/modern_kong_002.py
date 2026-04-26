#!/usr/bin/env python3

import argparse
import json
import os
import sys
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import quote

import requests


DEFAULT_TIMEOUT = int(os.getenv("KONG_TIMEOUT", "30"))
DEFAULT_ADMIN_URL = os.getenv("KONG_ADMIN_URL", "http://localhost:8001")


def clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [clean(v) for v in value if v is not None]
    return value


def require_name(resource_type: str, spec: Dict[str, Any]) -> str:
    name = spec.get("name")
    if not name:
        raise ValueError(f"{resource_type} requires a 'name': {json.dumps(spec, sort_keys=True)}")
    return name


class KongAdminClient:
    def __init__(self, admin_url: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.admin_url = admin_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})

    def _url(self, path: str) -> str:
        return f"{self.admin_url}/{path.lstrip('/')}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        expected: Iterable[int] = (200, 201, 204),
    ) -> requests.Response:
        response = self.session.request(
            method=method.upper(),
            url=self._url(path),
            json=clean(json_body) if json_body is not None else None,
            timeout=self.timeout,
        )
        if response.status_code not in set(expected):
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            raise RuntimeError(f"{method.upper()} {path} failed with {response.status_code}: {detail}")
        return response

    def _create_or_patch(
        self,
        create_path: str,
        patch_path: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        response = self._request("POST", create_path, json_body=payload, expected=(200, 201, 409))
        if response.status_code == 409:
            patch_payload = {k: v for k, v in payload.items() if k != "name"}
            response = self._request("PATCH", patch_path, json_body=patch_payload, expected=(200, 201))
        return response.json()

    def create_or_update_upstream(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        spec = dict(spec)
        name = require_name("upstream", spec)
        payload = {k: v for k, v in spec.items() if k != "targets"}
        return self._create_or_patch(
            create_path="/upstreams",
            patch_path=f"/upstreams/{quote(name, safe='')}",
            payload=payload,
        )

    def list_targets(self, upstream_name: str) -> List[Dict[str, Any]]:
        response = self._request(
            "GET",
            f"/upstreams/{quote(upstream_name, safe='')}/targets/all",
            expected=(200,),
        )
        return response.json().get("data", [])

    def ensure_target(self, upstream_name: str, spec: Dict[str, Any]) -> Dict[str, Any]:
        target = spec.get("target")
        if not target:
            raise ValueError(f"target requires a 'target' value: {json.dumps(spec, sort_keys=True)}")

        payload = clean(
            {
                "target": target,
                "weight": spec.get("weight", 100),
                "tags": spec.get("tags"),
            }
        )

        for existing in self.list_targets(upstream_name):
            if (
                existing.get("target") == payload["target"]
                and existing.get("weight") == payload["weight"]
                and existing.get("tags", []) == payload.get("tags", existing.get("tags", []))
            ):
                return existing

        response = self._request(
            "POST",
            f"/upstreams/{quote(upstream_name, safe='')}/targets",
            json_body=payload,
            expected=(200, 201),
        )
        return response.json()

    def create_or_update_service(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        spec = dict(spec)
        name = require_name("service", spec)

        if "upstream" in spec and "host" not in spec and "url" not in spec:
            spec["host"] = spec["upstream"]
            spec.setdefault("protocol", "http")
            spec.setdefault("port", 80)

        payload = {k: v for k, v in spec.items() if k not in {"routes", "upstream"}}
        return self._create_or_patch(
            create_path="/services",
            patch_path=f"/services/{quote(name, safe='')}",
            payload=payload,
        )

    def create_or_update_route(self, service_name: str, spec: Dict[str, Any]) -> Dict[str, Any]:
        spec = dict(spec)
        name = require_name("route", spec)
        return self._create_or_patch(
            create_path=f"/services/{quote(service_name, safe='')}/routes",
            patch_path=f"/routes/{quote(name, safe='')}",
            payload=spec,
        )


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def apply_config(client: KongAdminClient, config: Dict[str, Any]) -> None:
    for upstream in config.get("upstreams", []):
        upstream_name = require_name("upstream", upstream)
        client.create_or_update_upstream(upstream)
        for target in upstream.get("targets", []):
            client.ensure_target(upstream_name, target)

    for service in config.get("services", []):
        service_name = require_name("service", service)
        client.create_or_update_service(service)
        for route in service.get("routes", []):
            client.create_or_update_route(service_name, route)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Configure Kong Gateway services, routes, and upstream targets.")
    parser.add_argument(
        "--admin-url",
        default=DEFAULT_ADMIN_URL,
        help=f"Kong Admin API base URL (default: {DEFAULT_ADMIN_URL})",
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to a JSON config file.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"HTTP timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_config(args.config)
    client = KongAdminClient(admin_url=args.admin_url, timeout=args.timeout)
    apply_config(client, config)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)