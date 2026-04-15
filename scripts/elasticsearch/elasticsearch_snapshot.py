#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
from typing import Any

import requests

REPOSITORY_S3: dict[str, Any] = {
    "type": "s3",
    "settings": {
        "bucket": "${ES_SNAPSHOT_S3_BUCKET}",
        "base_path": "${ES_SNAPSHOT_S3_BASE_PATH}",
        "region": "${ES_SNAPSHOT_S3_REGION}",
        "compress": True,
        "max_restore_bytes_per_sec": "400mb",
        "max_snapshot_bytes_per_sec": "200mb",
        "readonly": False,
    },
}

REPOSITORY_FS: dict[str, Any] = {
    "type": "fs",
    "settings": {
        "location": "${ES_SNAPSHOT_FS_PATH}",
        "compress": True,
        "max_restore_bytes_per_sec": "400mb",
        "max_snapshot_bytes_per_sec": "200mb",
        "readonly": False,
    },
}

SLM_POLICY: dict[str, Any] = {
    "schedule": "0 30 1 * * ?",
    "name": "<daily-snap-{now/d}>",
    "repository": "${ES_SNAPSHOT_REPOSITORY_NAME}",
    "config": {
        "indices": ["*"],
        "ignore_unavailable": False,
        "include_global_state": True,
        "partial": False,
    },
    "retention": {"expire_after": "30d", "min_count": 5, "max_count": 50},
}


def _expand_env_values(obj: Any) -> Any:
    if isinstance(obj, str):

        def repl(m: re.Match[str]) -> str:
            return os.environ.get(m.group(1), "")

        return re.sub(r"\$\{([^}]+)\}", repl, obj)
    if isinstance(obj, dict):
        return {k: _expand_env_values(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_env_values(v) for v in obj]
    return obj


def _request(
    method: str,
    path: str,
    base_url: str,
    verify_tls: bool,
    timeout: float,
    body: Any | None = None,
) -> requests.Response:
    user = os.environ.get("ELASTICSEARCH_USER", "")
    password = os.environ.get("ELASTICSEARCH_PASSWORD", "")
    headers: dict[str, str] = {"Content-Type": "application/json"}
    api_key = os.environ.get("ELASTICSEARCH_API_KEY", "")
    if api_key:
        headers["Authorization"] = f"ApiKey {api_key}"
    auth = None if api_key else ((user, password) if user else None)
    url = base_url.rstrip("/") + path
    kw: dict[str, Any] = {
        "headers": headers,
        "timeout": timeout,
        "verify": verify_tls,
        "auth": auth,
    }
    if body is None:
        r = requests.request(method, url, **kw)
    else:
        r = requests.request(method, url, data=json.dumps(body), **kw)
    return r


def cmd_register_s3(args: argparse.Namespace) -> int:
    payload = _expand_env_values(copy.deepcopy(REPOSITORY_S3))
    repo = args.repository
    r = _request("PUT", f"/_snapshot/{repo}", args.base_url, args.verify_tls, args.timeout, payload)
    sys.stdout.write(r.text + "\n")
    return 0 if r.ok else 1


def cmd_register_fs(args: argparse.Namespace) -> int:
    if args.fs_path:
        os.environ["ES_SNAPSHOT_FS_PATH"] = args.fs_path
    payload = _expand_env_values(copy.deepcopy(REPOSITORY_FS))
    repo = args.repository
    r = _request("PUT", f"/_snapshot/{repo}", args.base_url, args.verify_tls, args.timeout, payload)
    sys.stdout.write(r.text + "\n")
    return 0 if r.ok else 1


def cmd_create_snapshot(args: argparse.Namespace) -> int:
    q = ""
    if args.wait:
        q = "?wait_for_completion=true"
    body: dict[str, Any] = {
        "indices": args.indices,
        "ignore_unavailable": args.ignore_unavailable,
        "include_global_state": args.include_global_state,
        "partial": args.partial,
    }
    if args.metadata:
        body["metadata"] = json.loads(args.metadata)
    path = f"/_snapshot/{args.repository}/{args.snapshot}{q}"
    r = _request("PUT", path, args.base_url, args.verify_tls, args.timeout, body)
    sys.stdout.write(r.text + "\n")
    return 0 if r.ok else 1


def cmd_restore(args: argparse.Namespace) -> int:
    q = ""
    if args.wait:
        q = "?wait_for_completion=true"
    body: dict[str, Any] = {
        "indices": args.indices,
        "ignore_unavailable": args.ignore_unavailable,
        "include_global_state": args.include_global_state,
        "include_aliases": args.include_aliases,
    }
    if args.rename_pattern and args.rename_replacement:
        body["rename_pattern"] = args.rename_pattern
        body["rename_replacement"] = args.rename_replacement
    path = f"/_snapshot/{args.repository}/{args.snapshot}/_restore{q}"
    r = _request("POST", path, args.base_url, args.verify_tls, args.timeout, body)
    sys.stdout.write(r.text + "\n")
    return 0 if r.ok else 1


def cmd_list_repositories(args: argparse.Namespace) -> int:
    r = _request("GET", "/_snapshot", args.base_url, args.verify_tls, args.timeout)
    sys.stdout.write(r.text + "\n")
    return 0 if r.ok else 1


def cmd_list_snapshots(args: argparse.Namespace) -> int:
    path = f"/_snapshot/{args.repository}/_all"
    r = _request("GET", path, args.base_url, args.verify_tls, args.timeout)
    sys.stdout.write(r.text + "\n")
    return 0 if r.ok else 1


def cmd_delete_snapshot(args: argparse.Namespace) -> int:
    path = f"/_snapshot/{args.repository}/{args.snapshot}"
    r = _request("DELETE", path, args.base_url, args.verify_tls, args.timeout)
    sys.stdout.write(r.text + "\n")
    return 0 if r.ok else 1


def cmd_verify_repository(args: argparse.Namespace) -> int:
    path = f"/_snapshot/{args.repository}/_verify"
    r = _request("POST", path, args.base_url, args.verify_tls, args.timeout, {})
    sys.stdout.write(r.text + "\n")
    return 0 if r.ok else 1


def cmd_apply_slm(args: argparse.Namespace) -> int:
    os.environ["ES_SNAPSHOT_REPOSITORY_NAME"] = args.repository
    policy_body = _expand_env_values(copy.deepcopy(SLM_POLICY))
    r = _request(
        "PUT",
        f"/_slm/policy/{args.policy}",
        args.base_url,
        args.verify_tls,
        args.timeout,
        policy_body,
    )
    sys.stdout.write(r.text + "\n")
    return 0 if r.ok else 1


def cmd_slm_execute(args: argparse.Namespace) -> int:
    r = _request(
        "POST",
        f"/_slm/policy/{args.policy}/_execute",
        args.base_url,
        args.verify_tls,
        args.timeout,
        {},
    )
    sys.stdout.write(r.text + "\n")
    return 0 if r.ok else 1


def cmd_snapshot_status(args: argparse.Namespace) -> int:
    if args.snapshot:
        if not args.repository:
            sys.stderr.write("snapshot-status: --repository is required when --snapshot is set\n")
            return 1
        path = f"/_snapshot/{args.repository}/{args.snapshot}/_status"
    else:
        path = "/_snapshot/_status"
    r = _request("GET", path, args.base_url, args.verify_tls, args.timeout)
    sys.stdout.write(r.text + "\n")
    return 0 if r.ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Elasticsearch snapshot operations")
    p.add_argument(
        "--base-url",
        default=os.environ.get("ELASTICSEARCH_URL", "http://127.0.0.1:9200"),
        help="Cluster URL (env ELASTICSEARCH_URL)",
    )
    p.add_argument(
        "--no-verify-tls",
        dest="verify_tls",
        action="store_false",
        default=True,
        help="Disable TLS certificate verification",
    )
    p.add_argument("--timeout", type=float, default=600.0, help="HTTP timeout seconds")

    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("register-s3", help="Register or update S3 snapshot repository")
    s.add_argument("--repository", required=True)
    s.set_defaults(func=cmd_register_s3)

    s = sub.add_parser("register-fs", help="Register or update shared filesystem repository")
    s.add_argument("--repository", required=True)
    s.add_argument("--fs-path", help="Override ES_SNAPSHOT_FS_PATH")
    s.set_defaults(func=cmd_register_fs)

    s = sub.add_parser("create-snapshot")
    s.add_argument("--repository", required=True)
    s.add_argument("--snapshot", required=True)
    s.add_argument("--indices", default="*")
    s.add_argument("--ignore-unavailable", action="store_true")
    s.add_argument("--no-global-state", dest="include_global_state", action="store_false", default=True)
    s.add_argument("--partial", action="store_true")
    s.add_argument("--metadata", default="")
    s.add_argument("--wait", action="store_true")
    s.set_defaults(func=cmd_create_snapshot)

    s = sub.add_parser("restore")
    s.add_argument("--repository", required=True)
    s.add_argument("--snapshot", required=True)
    s.add_argument("--indices", default="*")
    s.add_argument("--ignore-unavailable", action="store_true")
    s.add_argument("--no-global-state", dest="include_global_state", action="store_false", default=True)
    s.add_argument("--no-aliases", dest="include_aliases", action="store_false", default=True)
    s.add_argument("--rename-pattern", default="")
    s.add_argument("--rename-replacement", default="")
    s.add_argument("--wait", action="store_true")
    s.set_defaults(func=cmd_restore)

    s = sub.add_parser("list-repositories")
    s.set_defaults(func=cmd_list_repositories)

    s = sub.add_parser("list-snapshots")
    s.add_argument("--repository", required=True)
    s.set_defaults(func=cmd_list_snapshots)

    s = sub.add_parser("delete-snapshot")
    s.add_argument("--repository", required=True)
    s.add_argument("--snapshot", required=True)
    s.set_defaults(func=cmd_delete_snapshot)

    s = sub.add_parser("verify-repository")
    s.add_argument("--repository", required=True)
    s.set_defaults(func=cmd_verify_repository)

    s = sub.add_parser("apply-slm")
    s.add_argument("--policy", default="nightly-snapshots")
    s.add_argument("--repository", required=True)
    s.set_defaults(func=cmd_apply_slm)

    s = sub.add_parser("execute-slm")
    s.add_argument("--policy", default="nightly-snapshots")
    s.set_defaults(func=cmd_slm_execute)

    s = sub.add_parser("snapshot-status")
    s.add_argument("--repository", default="")
    s.add_argument("--snapshot", default="")
    s.set_defaults(func=cmd_snapshot_status)

    return p


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
