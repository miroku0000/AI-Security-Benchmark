#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import sys
import time
import urllib.parse
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests


def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    val = val.strip().lower()
    if val in ("1", "true", "t", "yes", "y", "on"):
        return True
    if val in ("0", "false", "f", "no", "n", "off"):
        return False
    return default


def _now_utc_compact() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _read_json_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    try:
        cfg = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SystemExit(f"Invalid JSON config at {path}: {e}") from e
    if not isinstance(cfg, dict):
        raise SystemExit(f"Config must be a JSON object at top-level: {path}")
    return cfg


def _write_json(path: str, obj: Any) -> None:
    data = json.dumps(obj, indent=2, sort_keys=True)
    if path == "-" or path == "":
        sys.stdout.write(data + "\n")
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(data + "\n")


class ESClient:
    def __init__(self, base_url: str, auth: Optional[Tuple[str, str]] = None, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

        verify_ssl = _env_bool("ES_VERIFY_SSL", True)
        ca_cert = os.environ.get("ES_CA_CERT")
        if ca_cert:
            self.session.verify = ca_cert
        else:
            self.session.verify = verify_ssl

        timeout_s = float(os.environ.get("ES_TIMEOUT", "60"))
        self.timeout = timeout_s

        if api_key:
            if ":" in api_key:
                api_key_b64 = base64.b64encode(api_key.encode("utf-8")).decode("ascii")
                self.session.headers["Authorization"] = f"ApiKey {api_key_b64}"
            else:
                self.session.headers["Authorization"] = f"ApiKey {api_key}"
        elif auth:
            self.session.auth = auth

        extra_headers = os.environ.get("ES_HEADERS_JSON")
        if extra_headers:
            try:
                h = json.loads(extra_headers)
            except json.JSONDecodeError as e:
                raise SystemExit(f"Invalid ES_HEADERS_JSON: {e}") from e
            if not isinstance(h, dict):
                raise SystemExit("ES_HEADERS_JSON must be a JSON object")
            for k, v in h.items():
                self.session.headers[str(k)] = str(v)

    def _url(self, path: str, params: Optional[Dict[str, Any]] = None) -> str:
        if not path.startswith("/"):
            path = "/" + path
        url = self.base_url + path
        if params:
            qp = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None}, doseq=True)
            if qp:
                url += "?" + qp
        return url

    def request(self, method: str, path: str, *, params: Optional[Dict[str, Any]] = None, json_body: Any = None) -> Any:
        url = self._url(path, params=params)
        resp = self.session.request(method, url, json=json_body, timeout=self.timeout)
        if resp.status_code >= 400:
            body = resp.text.strip()
            raise SystemExit(f"Elasticsearch API error {resp.status_code} {resp.reason}: {body}")
        if resp.status_code == 204:
            return None
        ctype = resp.headers.get("content-type", "")
        if "application/json" in ctype or resp.text.lstrip().startswith("{") or resp.text.lstrip().startswith("["):
            try:
                return resp.json()
            except Exception:
                return resp.text
        return resp.text

    def get(self, path: str, *, params: Optional[Dict[str, Any]] = None) -> Any:
        return self.request("GET", path, params=params)

    def put(self, path: str, *, params: Optional[Dict[str, Any]] = None, json_body: Any = None) -> Any:
        return self.request("PUT", path, params=params, json_body=json_body)

    def post(self, path: str, *, params: Optional[Dict[str, Any]] = None, json_body: Any = None) -> Any:
        return self.request("POST", path, params=params, json_body=json_body)

    def delete(self, path: str, *, params: Optional[Dict[str, Any]] = None) -> Any:
        return self.request("DELETE", path, params=params)


def _client_from_env() -> ESClient:
    base_url = os.environ.get("ES_URL", "").strip()
    if not base_url:
        raise SystemExit("Missing ES_URL (e.g. https://localhost:9200)")

    api_key = os.environ.get("ES_API_KEY")
    user = os.environ.get("ES_USER")
    password = os.environ.get("ES_PASS")
    auth = None
    if not api_key and user is not None:
        auth = (user, password or "")
    return ESClient(base_url, auth=auth, api_key=api_key)


def _require_keys(d: Dict[str, Any], keys: Iterable[str], where: str) -> None:
    missing = [k for k in keys if k not in d]
    if missing:
        raise SystemExit(f"Missing keys in {where}: {', '.join(missing)}")


def _repo_payload_from_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    _require_keys(cfg, ("repository",), "config")
    repo = cfg["repository"]
    if not isinstance(repo, dict):
        raise SystemExit("config.repository must be an object")
    _require_keys(repo, ("name", "type", "settings"), "config.repository")
    if not isinstance(repo["settings"], dict):
        raise SystemExit("config.repository.settings must be an object")
    return {"type": repo["type"], "settings": repo["settings"]}


def _repo_name_from_config(cfg: Dict[str, Any]) -> str:
    repo = cfg.get("repository") or {}
    name = repo.get("name")
    if not isinstance(name, str) or not name.strip():
        raise SystemExit("config.repository.name must be a non-empty string")
    return name.strip()


def _snapshot_name(cfg: Dict[str, Any], explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    snap_cfg = cfg.get("snapshot") or {}
    prefix = snap_cfg.get("name_prefix", "snap")
    if not isinstance(prefix, str) or not prefix.strip():
        prefix = "snap"
    return f"{prefix}-{_now_utc_compact()}"


def cmd_init_config(args: argparse.Namespace) -> None:
    obj = {
        "repository": {
            "name": "ops-backups",
            "type": "s3",
            "settings": {
                "bucket": "my-es-snapshots",
                "base_path": "elasticsearch",
                "region": "us-east-1",
                "compress": True,
                "server_side_encryption": True,
            },
        },
        "snapshot": {
            "name_prefix": "daily",
            "indices": ["*"],
            "ignore_unavailable": True,
            "include_global_state": False,
            "partial": False,
            "metadata": {"created_by": "es_snapshot_ops.py"},
            "feature_states": [],
        },
        "restore": {
            "indices": ["*"],
            "ignore_unavailable": True,
            "include_global_state": False,
            "partial": False,
            "rename_pattern": "",
            "rename_replacement": "",
            "index_settings": {},
            "ignore_index_settings": [],
            "feature_states": [],
        },
    }

    if args.repo_type == "fs":
        obj["repository"]["type"] = "fs"
        obj["repository"]["settings"] = {
            "location": "/mount/backups/elasticsearch",
            "compress": True,
        }

    _write_json(args.out, obj)


def cmd_cluster_info(_: argparse.Namespace) -> None:
    es = _client_from_env()
    info = es.get("/")
    _write_json("-", info)


def cmd_register_repo(args: argparse.Namespace) -> None:
    es = _client_from_env()
    cfg = _read_json_config(args.config)
    repo_name = _repo_name_from_config(cfg)
    payload = _repo_payload_from_config(cfg)
    params = {"verify": "true" if args.verify else "false"}
    out = es.put(f"/_snapshot/{urllib.parse.quote(repo_name, safe='')}", params=params, json_body=payload)
    _write_json("-", out)


def cmd_get_repo(args: argparse.Namespace) -> None:
    es = _client_from_env()
    cfg = _read_json_config(args.config)
    repo_name = _repo_name_from_config(cfg)
    out = es.get(f"/_snapshot/{urllib.parse.quote(repo_name, safe='')}")
    _write_json("-", out)


def cmd_list_snapshots(args: argparse.Namespace) -> None:
    es = _client_from_env()
    cfg = _read_json_config(args.config)
    repo_name = _repo_name_from_config(cfg)
    snap = args.snapshot or "_all"
    out = es.get(
        f"/_snapshot/{urllib.parse.quote(repo_name, safe='')}/{urllib.parse.quote(snap, safe='')}",
        params={"verbose": "true"},
    )
    _write_json("-", out)


def _snapshot_body_from_config(cfg: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    snap_cfg = cfg.get("snapshot") or {}
    if not isinstance(snap_cfg, dict):
        raise SystemExit("config.snapshot must be an object")
    body: Dict[str, Any] = {}
    indices = args.indices if args.indices is not None else snap_cfg.get("indices")
    if indices is not None:
        if isinstance(indices, list):
            body["indices"] = ",".join(str(x) for x in indices)
        else:
            body["indices"] = str(indices)
    ignore_unavailable = args.ignore_unavailable if args.ignore_unavailable is not None else snap_cfg.get("ignore_unavailable")
    if ignore_unavailable is not None:
        body["ignore_unavailable"] = bool(ignore_unavailable)
    include_global_state = args.include_global_state if args.include_global_state is not None else snap_cfg.get("include_global_state")
    if include_global_state is not None:
        body["include_global_state"] = bool(include_global_state)
    partial = args.partial if args.partial is not None else snap_cfg.get("partial")
    if partial is not None:
        body["partial"] = bool(partial)
    metadata = snap_cfg.get("metadata")
    if isinstance(metadata, dict) and metadata:
        body["metadata"] = metadata
    feature_states = snap_cfg.get("feature_states")
    if isinstance(feature_states, list) and feature_states:
        body["feature_states"] = [str(x) for x in feature_states]
    return body


def cmd_create_snapshot(args: argparse.Namespace) -> None:
    es = _client_from_env()
    cfg = _read_json_config(args.config)
    repo_name = _repo_name_from_config(cfg)
    snap_name = _snapshot_name(cfg, args.snapshot)
    body = _snapshot_body_from_config(cfg, args)
    params = {"wait_for_completion": "true" if args.wait else "false"}
    out = es.put(
        f"/_snapshot/{urllib.parse.quote(repo_name, safe='')}/{urllib.parse.quote(snap_name, safe='')}",
        params=params,
        json_body=body if body else None,
    )
    _write_json("-", {"repository": repo_name, "snapshot": snap_name, "response": out})


def cmd_snapshot_status(args: argparse.Namespace) -> None:
    es = _client_from_env()
    cfg = _read_json_config(args.config)
    repo_name = _repo_name_from_config(cfg)
    snap = args.snapshot
    if not snap:
        raise SystemExit("--snapshot is required")
    out = es.get(
        f"/_snapshot/{urllib.parse.quote(repo_name, safe='')}/{urllib.parse.quote(snap, safe='')}/_status"
    )
    _write_json("-", out)


def cmd_delete_snapshot(args: argparse.Namespace) -> None:
    es = _client_from_env()
    cfg = _read_json_config(args.config)
    repo_name = _repo_name_from_config(cfg)
    snap = args.snapshot
    if not snap:
        raise SystemExit("--snapshot is required")
    out = es.delete(f"/_snapshot/{urllib.parse.quote(repo_name, safe='')}/{urllib.parse.quote(snap, safe='')}")
    _write_json("-", out or {"deleted": True, "snapshot": snap})


def _restore_body_from_config(cfg: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    r_cfg = cfg.get("restore") or {}
    if not isinstance(r_cfg, dict):
        raise SystemExit("config.restore must be an object")
    body: Dict[str, Any] = {}

    indices = args.indices if args.indices is not None else r_cfg.get("indices")
    if indices is not None:
        if isinstance(indices, list):
            body["indices"] = ",".join(str(x) for x in indices)
        else:
            body["indices"] = str(indices)

    ignore_unavailable = args.ignore_unavailable if args.ignore_unavailable is not None else r_cfg.get("ignore_unavailable")
    if ignore_unavailable is not None:
        body["ignore_unavailable"] = bool(ignore_unavailable)

    include_global_state = args.include_global_state if args.include_global_state is not None else r_cfg.get("include_global_state")
    if include_global_state is not None:
        body["include_global_state"] = bool(include_global_state)

    partial = args.partial if args.partial is not None else r_cfg.get("partial")
    if partial is not None:
        body["partial"] = bool(partial)

    rename_pattern = args.rename_pattern if args.rename_pattern is not None else r_cfg.get("rename_pattern")
    rename_replacement = args.rename_replacement if args.rename_replacement is not None else r_cfg.get("rename_replacement")
    if rename_pattern:
        body["rename_pattern"] = str(rename_pattern)
        body["rename_replacement"] = str(rename_replacement or "")

    index_settings = r_cfg.get("index_settings")
    if isinstance(index_settings, dict) and index_settings:
        body["index_settings"] = index_settings

    ignore_index_settings = r_cfg.get("ignore_index_settings")
    if isinstance(ignore_index_settings, list) and ignore_index_settings:
        body["ignore_index_settings"] = [str(x) for x in ignore_index_settings]

    feature_states = r_cfg.get("feature_states")
    if isinstance(feature_states, list) and feature_states:
        body["feature_states"] = [str(x) for x in feature_states]

    if args.include_aliases is not None:
        body["include_aliases"] = bool(args.include_aliases)
    if args.include_data_streams is not None:
        body["include_data_streams"] = bool(args.include_data_streams)

    return body


def _wait_for_restore_completion(es: ESClient, poll_s: float, timeout_s: float) -> Dict[str, Any]:
    start = time.time()
    last = None
    while True:
        rec = es.get("/_cat/recovery", params={"format": "json"})
        last = {"recovery": rec}
        in_progress = False
        if isinstance(rec, list):
            for row in rec:
                if not isinstance(row, dict):
                    continue
                stage = str(row.get("stage", "")).lower()
                if stage not in ("done", ""):
                    in_progress = True
                    break
        if not in_progress:
            return last
        if time.time() - start > timeout_s:
            raise SystemExit("Timed out waiting for restore to complete")
        time.sleep(poll_s)


def cmd_restore_snapshot(args: argparse.Namespace) -> None:
    es = _client_from_env()
    cfg = _read_json_config(args.config)
    repo_name = _repo_name_from_config(cfg)
    snap = args.snapshot
    if not snap:
        raise SystemExit("--snapshot is required")
    body = _restore_body_from_config(cfg, args)
    out = es.post(
        f"/_snapshot/{urllib.parse.quote(repo_name, safe='')}/{urllib.parse.quote(snap, safe='')}/_restore",
        json_body=body if body else None,
    )
    result: Dict[str, Any] = {"repository": repo_name, "snapshot": snap, "response": out}
    if args.wait:
        poll_s = float(os.environ.get("ES_RESTORE_POLL_S", "5"))
        timeout_s = float(os.environ.get("ES_RESTORE_TIMEOUT_S", "3600"))
        result["wait"] = _wait_for_restore_completion(es, poll_s=poll_s, timeout_s=timeout_s)
    _write_json("-", result)


def cmd_health(_: argparse.Namespace) -> None:
    es = _client_from_env()
    out = es.get("/_cluster/health")
    _write_json("-", out)


def cmd_slm_put_policy(args: argparse.Namespace) -> None:
    es = _client_from_env()
    cfg = _read_json_config(args.config)
    repo_name = _repo_name_from_config(cfg)

    policy_id = args.policy_id
    if not policy_id:
        raise SystemExit("--policy-id is required")
    schedule = args.schedule
    if not schedule:
        raise SystemExit("--schedule is required (cron or interval, depending on ES version)")

    snap_cfg = cfg.get("snapshot") or {}
    if not isinstance(snap_cfg, dict):
        snap_cfg = {}
    name_prefix = snap_cfg.get("name_prefix", "slm")
    snapshot_name = args.snapshot_name or f"{name_prefix}-{{now/d}}"

    config = _snapshot_body_from_config(cfg, argparse.Namespace(
        indices=None,
        ignore_unavailable=None,
        include_global_state=None,
        partial=None,
    ))

    retention: Dict[str, Any] = {}
    if args.expire_after:
        retention["expire_after"] = args.expire_after
    if args.min_count is not None:
        retention["min_count"] = int(args.min_count)
    if args.max_count is not None:
        retention["max_count"] = int(args.max_count)

    body: Dict[str, Any] = {
        "schedule": schedule,
        "name": snapshot_name,
        "repository": repo_name,
        "config": config,
    }
    if retention:
        body["retention"] = retention

    out = es.put(f"/_slm/policy/{urllib.parse.quote(policy_id, safe='')}", json_body=body)
    _write_json("-", out)


def cmd_slm_execute(args: argparse.Namespace) -> None:
    es = _client_from_env()
    policy_id = args.policy_id
    if not policy_id:
        raise SystemExit("--policy-id is required")
    out = es.post(f"/_slm/policy/{urllib.parse.quote(policy_id, safe='')}/_execute")
    _write_json("-", out)


def cmd_slm_get_policy(args: argparse.Namespace) -> None:
    es = _client_from_env()
    policy_id = args.policy_id or "_all"
    out = es.get(f"/_slm/policy/{urllib.parse.quote(policy_id, safe='')}")
    _write_json("-", out)


def cmd_slm_get_status(_: argparse.Namespace) -> None:
    es = _client_from_env()
    out = es.get("/_slm/status")
    _write_json("-", out)


def cmd_slm_start(_: argparse.Namespace) -> None:
    es = _client_from_env()
    out = es.post("/_slm/start")
    _write_json("-", out)


def cmd_slm_stop(_: argparse.Namespace) -> None:
    es = _client_from_env()
    out = es.post("/_slm/stop")
    _write_json("-", out)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="es_snapshot_ops.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("init-config", help="write example JSON config")
    sp.add_argument("--repo-type", choices=("s3", "fs"), default="s3")
    sp.add_argument("--out", default="-", help="output path or '-' for stdout")
    sp.set_defaults(func=cmd_init_config)

    sp = sub.add_parser("cluster-info", help="GET /")
    sp.set_defaults(func=cmd_cluster_info)

    sp = sub.add_parser("health", help="cluster health")
    sp.set_defaults(func=cmd_health)

    sp = sub.add_parser("register-repo", help="create/update snapshot repository")
    sp.add_argument("--config", required=True, help="path to JSON config")
    sp.add_argument("--verify", action="store_true", help="verify repository on registration")
    sp.set_defaults(func=cmd_register_repo)

    sp = sub.add_parser("get-repo", help="get repository definition")
    sp.add_argument("--config", required=True, help="path to JSON config")
    sp.set_defaults(func=cmd_get_repo)

    sp = sub.add_parser("list", help="list snapshots")
    sp.add_argument("--config", required=True, help="path to JSON config")
    sp.add_argument("--snapshot", default=None, help="snapshot name or '_all'")
    sp.set_defaults(func=cmd_list_snapshots)

    sp = sub.add_parser("create", help="create snapshot")
    sp.add_argument("--config", required=True, help="path to JSON config")
    sp.add_argument("--snapshot", default=None, help="snapshot name (default: prefix+timestamp)")
    sp.add_argument("--wait", action="store_true", help="wait for completion")
    sp.add_argument("--indices", default=None, help="override indices (comma-separated string)")
    sp.add_argument("--ignore-unavailable", dest="ignore_unavailable", action="store_true", default=None)
    sp.add_argument("--no-ignore-unavailable", dest="ignore_unavailable", action="store_false")
    sp.add_argument("--include-global-state", dest="include_global_state", action="store_true", default=None)
    sp.add_argument("--no-include-global-state", dest="include_global_state", action="store_false")
    sp.add_argument("--partial", dest="partial", action="store_true", default=None)
    sp.add_argument("--no-partial", dest="partial", action="store_false")
    sp.set_defaults(func=cmd_create_snapshot)

    sp = sub.add_parser("status", help="snapshot status")
    sp.add_argument("--config", required=True, help="path to JSON config")
    sp.add_argument("--snapshot", required=True, help="snapshot name")
    sp.set_defaults(func=cmd_snapshot_status)

    sp = sub.add_parser("delete", help="delete snapshot")
    sp.add_argument("--config", required=True, help="path to JSON config")
    sp.add_argument("--snapshot", required=True, help="snapshot name")
    sp.set_defaults(func=cmd_delete_snapshot)

    sp = sub.add_parser("restore", help="restore snapshot")
    sp.add_argument("--config", required=True, help="path to JSON config")
    sp.add_argument("--snapshot", required=True, help="snapshot name")
    sp.add_argument("--wait", action="store_true", help="wait for restore completion (polls _cat/recovery)")
    sp.add_argument("--indices", default=None, help="override indices (comma-separated string)")
    sp.add_argument("--ignore-unavailable", dest="ignore_unavailable", action="store_true", default=None)
    sp.add_argument("--no-ignore-unavailable", dest="ignore_unavailable", action="store_false")
    sp.add_argument("--include-global-state", dest="include_global_state", action="store_true", default=None)
    sp.add_argument("--no-include-global-state", dest="include_global_state", action="store_false")
    sp.add_argument("--partial", dest="partial", action="store_true", default=None)
    sp.add_argument("--no-partial", dest="partial", action="store_false")
    sp.add_argument("--rename-pattern", default=None)
    sp.add_argument("--rename-replacement", default=None)
    sp.add_argument("--include-aliases", dest="include_aliases", action="store_true", default=None)
    sp.add_argument("--no-include-aliases", dest="include_aliases", action="store_false")
    sp.add_argument("--include-data-streams", dest="include_data_streams", action="store_true", default=None)
    sp.add_argument("--no-include-data-streams", dest="include_data_streams", action="store_false")
    sp.set_defaults(func=cmd_restore_snapshot)

    sp = sub.add_parser("slm-put-policy", help="create/update SLM policy (optional automation)")
    sp.add_argument("--config", required=True, help="path to JSON config")
    sp.add_argument("--policy-id", required=True)
    sp.add_argument("--schedule", required=True, help="SLM schedule string (cron or interval)")
    sp.add_argument("--snapshot-name", default=None, help="snapshot name template (default: <prefix>-{now/d})")
    sp.add_argument("--expire-after", default=None, help="e.g. '30d'")
    sp.add_argument("--min-count", default=None, type=int)
    sp.add_argument("--max-count", default=None, type=int)
    sp.set_defaults(func=cmd_slm_put_policy)

    sp = sub.add_parser("slm-execute", help="execute SLM policy now")
    sp.add_argument("--policy-id", required=True)
    sp.set_defaults(func=cmd_slm_execute)

    sp = sub.add_parser("slm-get-policy", help="get SLM policy")
    sp.add_argument("--policy-id", default=None)
    sp.set_defaults(func=cmd_slm_get_policy)

    sp = sub.add_parser("slm-status", help="get SLM status")
    sp.set_defaults(func=cmd_slm_get_status)

    sp = sub.add_parser("slm-start", help="start SLM")
    sp.set_defaults(func=cmd_slm_start)

    sp = sub.add_parser("slm-stop", help="stop SLM")
    sp.set_defaults(func=cmd_slm_stop)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

