#!/usr/bin/env python3

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from urllib.parse import quote

import requests


class ElasticsearchSnapshotManager:
    def __init__(self, es_host="http://localhost:9200", username=None, password=None, ca_cert=None):
        self.es_host = es_host.rstrip("/")
        self.session = requests.Session()
        if username and password:
            self.session.auth = (username, password)
        if ca_cert:
            self.session.verify = ca_cert
        self.session.headers.update({"Content-Type": "application/json"})

    def _request(self, method, path, body=None, params=None):
        url = f"{self.es_host}/{path.lstrip('/')}"
        resp = self.session.request(method, url, json=body, params=params)
        if not resp.ok:
            print(f"Error {resp.status_code}: {resp.text}", file=sys.stderr)
        resp.raise_for_status()
        return resp.json()

    # ── Repository Management ──

    def register_s3_repository(self, repo_name, bucket, base_path="snapshots",
                               region=None, compress=True, chunk_size="1gb",
                               max_restore_rate="200mb", max_snapshot_rate="200mb",
                               server_side_encryption=True):
        settings = {
            "bucket": bucket,
            "base_path": base_path,
            "compress": compress,
            "chunk_size": chunk_size,
            "max_restore_bytes_per_sec": max_restore_rate,
            "max_snapshot_bytes_per_sec": max_snapshot_rate,
            "server_side_encryption": server_side_encryption,
        }
        if region:
            settings["region"] = region

        body = {"type": "s3", "settings": settings}
        result = self._request("PUT", f"_snapshot/{quote(repo_name, safe='')}", body=body)
        print(f"S3 repository '{repo_name}' registered (bucket={bucket}, path={base_path})")
        return result

    def register_fs_repository(self, repo_name, location, compress=True,
                               chunk_size="1gb", max_restore_rate="200mb",
                               max_snapshot_rate="200mb"):
        body = {
            "type": "fs",
            "settings": {
                "location": location,
                "compress": compress,
                "chunk_size": chunk_size,
                "max_restore_bytes_per_sec": max_restore_rate,
                "max_snapshot_bytes_per_sec": max_snapshot_rate,
            },
        }
        result = self._request("PUT", f"_snapshot/{quote(repo_name, safe='')}", body=body)
        print(f"Filesystem repository '{repo_name}' registered (location={location})")
        return result

    def verify_repository(self, repo_name):
        result = self._request("POST", f"_snapshot/{quote(repo_name, safe='')}/_verify")
        print(f"Repository '{repo_name}' verified on nodes: "
              f"{[n for n in result.get('nodes', {})]}")
        return result

    def get_repository(self, repo_name=None):
        path = f"_snapshot/{quote(repo_name, safe='')}" if repo_name else "_snapshot"
        return self._request("GET", path)

    def delete_repository(self, repo_name):
        result = self._request("DELETE", f"_snapshot/{quote(repo_name, safe='')}")
        print(f"Repository '{repo_name}' deleted")
        return result

    # ── Snapshot Creation ──

    def create_snapshot(self, repo_name, snapshot_name=None, indices=None,
                        ignore_unavailable=True, include_global_state=True,
                        partial=False, wait_for_completion=False):
        if snapshot_name is None:
            snapshot_name = f"snapshot-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

        body = {
            "ignore_unavailable": ignore_unavailable,
            "include_global_state": include_global_state,
            "partial": partial,
        }
        if indices:
            body["indices"] = indices if isinstance(indices, str) else ",".join(indices)

        params = {}
        if wait_for_completion:
            params["wait_for_completion"] = "true"

        path = f"_snapshot/{quote(repo_name, safe='')}/{quote(snapshot_name, safe='')}"
        result = self._request("PUT", path, body=body, params=params)
        print(f"Snapshot '{snapshot_name}' creation initiated in repo '{repo_name}'")
        return result

    def get_snapshot(self, repo_name, snapshot_name="_all"):
        path = f"_snapshot/{quote(repo_name, safe='')}/{quote(snapshot_name, safe='')}"
        return self._request("GET", path)

    def get_snapshot_status(self, repo_name=None, snapshot_name=None):
        if repo_name and snapshot_name:
            path = f"_snapshot/{quote(repo_name, safe='')}/{quote(snapshot_name, safe='')}/_status"
        else:
            path = "_snapshot/_status"
        return self._request("GET", path)

    def delete_snapshot(self, repo_name, snapshot_name):
        path = f"_snapshot/{quote(repo_name, safe='')}/{quote(snapshot_name, safe='')}"
        result = self._request("DELETE", path)
        print(f"Snapshot '{snapshot_name}' deleted from repo '{repo_name}'")
        return result

    def wait_for_snapshot(self, repo_name, snapshot_name, timeout_seconds=3600, poll_interval=10):
        start = time.time()
        while time.time() - start < timeout_seconds:
            try:
                status = self.get_snapshot_status(repo_name, snapshot_name)
                snapshots = status.get("snapshots", [])
                if not snapshots:
                    info = self.get_snapshot(repo_name, snapshot_name)
                    snap = info.get("snapshots", [{}])[0]
                    state = snap.get("state", "UNKNOWN")
                    if state in ("SUCCESS", "PARTIAL", "FAILED"):
                        print(f"Snapshot '{snapshot_name}' completed with state: {state}")
                        return snap
                else:
                    snap = snapshots[0]
                    state = snap.get("state", "STARTED")
                    stats = snap.get("stats", {})
                    total = stats.get("total", {})
                    done = stats.get("done", {})
                    print(f"  Progress: {done.get('file_count', 0)}/{total.get('file_count', '?')} files, "
                          f"{done.get('size_in_bytes', 0) / 1048576:.1f}MB / "
                          f"{total.get('size_in_bytes', 1) / 1048576:.1f}MB")
            except requests.HTTPError:
                pass
            time.sleep(poll_interval)
        raise TimeoutError(f"Snapshot '{snapshot_name}' did not complete within {timeout_seconds}s")

    # ── Snapshot Restoration ──

    def restore_snapshot(self, repo_name, snapshot_name, indices=None,
                         ignore_unavailable=True, include_global_state=False,
                         rename_pattern=None, rename_replacement=None,
                         index_settings=None, wait_for_completion=False):
        body = {
            "ignore_unavailable": ignore_unavailable,
            "include_global_state": include_global_state,
        }
        if indices:
            body["indices"] = indices if isinstance(indices, str) else ",".join(indices)
        if rename_pattern:
            body["rename_pattern"] = rename_pattern
            body["rename_replacement"] = rename_replacement or "$1_restored"
        if index_settings:
            body["index_settings"] = index_settings

        params = {}
        if wait_for_completion:
            params["wait_for_completion"] = "true"

        path = f"_snapshot/{quote(repo_name, safe='')}/{quote(snapshot_name, safe='')}/_restore"
        result = self._request("POST", path, body=body, params=params)
        print(f"Restore of snapshot '{snapshot_name}' initiated")
        return result

    def restore_to_different_index(self, repo_name, snapshot_name, source_index, target_index):
        return self.restore_snapshot(
            repo_name, snapshot_name,
            indices=source_index,
            rename_pattern=f"({source_index})",
            rename_replacement=target_index,
        )

    # ── SLM (Snapshot Lifecycle Management) ──

    def create_slm_policy(self, policy_name, repo_name, schedule, snapshot_name_format=None,
                          indices=None, ignore_unavailable=True, include_global_state=True,
                          expire_after=None, min_count=None, max_count=None):
        if snapshot_name_format is None:
            snapshot_name_format = f"<{policy_name}-{{now/d}}>"

        config = {
            "ignore_unavailable": ignore_unavailable,
            "include_global_state": include_global_state,
        }
        if indices:
            config["indices"] = indices if isinstance(indices, list) else [indices]

        body = {
            "schedule": schedule,
            "name": snapshot_name_format,
            "repository": repo_name,
            "config": config,
        }

        retention = {}
        if expire_after:
            retention["expire_after"] = expire_after
        if min_count is not None:
            retention["min_count"] = min_count
        if max_count is not None:
            retention["max_count"] = max_count
        if retention:
            body["retention"] = retention

        result = self._request("PUT", f"_slm/policy/{quote(policy_name, safe='')}", body=body)
        print(f"SLM policy '{policy_name}' created (schedule={schedule})")
        return result

    def execute_slm_policy(self, policy_name):
        result = self._request("POST", f"_slm/policy/{quote(policy_name, safe='')}/_execute")
        print(f"SLM policy '{policy_name}' executed: {result.get('snapshot_name', 'unknown')}")
        return result

    def get_slm_policy(self, policy_name=None):
        path = f"_slm/policy/{quote(policy_name, safe='')}" if policy_name else "_slm/policy"
        return self._request("GET", path)

    def delete_slm_policy(self, policy_name):
        result = self._request("DELETE", f"_slm/policy/{quote(policy_name, safe='')}")
        print(f"SLM policy '{policy_name}' deleted")
        return result

    def get_slm_stats(self):
        return self._request("GET", "_slm/stats")

    # ── Utilities ──

    def list_snapshots(self, repo_name):
        result = self.get_snapshot(repo_name)
        snapshots = result.get("snapshots", [])
        for s in snapshots:
            state = s.get("state", "UNKNOWN")
            start = s.get("start_time", "")
            end = s.get("end_time", "")
            idx_count = len(s.get("indices", []))
            dur = s.get("duration_in_millis", 0)
            print(f"  {s['snapshot']:<40} state={state:<10} indices={idx_count:<4} "
                  f"duration={dur / 1000:.1f}s  started={start}  ended={end}")
        return snapshots

    def cleanup_old_snapshots(self, repo_name, keep_count=10):
        snapshots = self.get_snapshot(repo_name).get("snapshots", [])
        snapshots.sort(key=lambda s: s.get("start_time_in_millis", 0))
        to_delete = snapshots[:-keep_count] if len(snapshots) > keep_count else []
        for s in to_delete:
            name = s["snapshot"]
            self.delete_snapshot(repo_name, name)
        print(f"Cleaned up {len(to_delete)} old snapshots, kept {min(len(snapshots), keep_count)}")
        return to_delete


def build_parser():
    parser = argparse.ArgumentParser(description="Elasticsearch Snapshot Manager")
    parser.add_argument("--host", default="http://localhost:9200", help="Elasticsearch host URL")
    parser.add_argument("--user", default=None, help="Username for authentication")
    parser.add_argument("--password", default=None, help="Password for authentication")
    parser.add_argument("--ca-cert", default=None, help="Path to CA certificate")

    sub = parser.add_subparsers(dest="command", required=True)

    # register-s3
    p = sub.add_parser("register-s3", help="Register S3 snapshot repository")
    p.add_argument("repo", help="Repository name")
    p.add_argument("--bucket", required=True, help="S3 bucket name")
    p.add_argument("--base-path", default="snapshots", help="Base path in bucket")
    p.add_argument("--region", default=None, help="AWS region")

    # register-fs
    p = sub.add_parser("register-fs", help="Register filesystem snapshot repository")
    p.add_argument("repo", help="Repository name")
    p.add_argument("--location", required=True, help="Shared filesystem path")

    # verify
    p = sub.add_parser("verify", help="Verify repository")
    p.add_argument("repo", help="Repository name")

    # list-repos
    sub.add_parser("list-repos", help="List all repositories")

    # delete-repo
    p = sub.add_parser("delete-repo", help="Delete repository")
    p.add_argument("repo", help="Repository name")

    # snapshot
    p = sub.add_parser("snapshot", help="Create a snapshot")
    p.add_argument("repo", help="Repository name")
    p.add_argument("--name", default=None, help="Snapshot name (auto-generated if omitted)")
    p.add_argument("--indices", default=None, help="Comma-separated indices to snapshot")
    p.add_argument("--wait", action="store_true", help="Wait for completion")

    # list-snapshots
    p = sub.add_parser("list-snapshots", help="List snapshots in a repository")
    p.add_argument("repo", help="Repository name")

    # snapshot-status
    p = sub.add_parser("snapshot-status", help="Get snapshot status")
    p.add_argument("repo", help="Repository name")
    p.add_argument("name", help="Snapshot name")

    # delete-snapshot
    p = sub.add_parser("delete-snapshot", help="Delete a snapshot")
    p.add_argument("repo", help="Repository name")
    p.add_argument("name", help="Snapshot name")

    # restore
    p = sub.add_parser("restore", help="Restore a snapshot")
    p.add_argument("repo", help="Repository name")
    p.add_argument("name", help="Snapshot name")
    p.add_argument("--indices", default=None, help="Comma-separated indices to restore")
    p.add_argument("--rename-pattern", default=None, help="Regex pattern for index renaming")
    p.add_argument("--rename-replacement", default=None, help="Replacement string for renaming")
    p.add_argument("--wait", action="store_true", help="Wait for completion")

    # restore-as
    p = sub.add_parser("restore-as", help="Restore an index under a different name")
    p.add_argument("repo", help="Repository name")
    p.add_argument("name", help="Snapshot name")
    p.add_argument("--source", required=True, help="Source index name")
    p.add_argument("--target", required=True, help="Target index name")

    # create-policy
    p = sub.add_parser("create-policy", help="Create SLM policy for automated backups")
    p.add_argument("policy", help="Policy name")
    p.add_argument("repo", help="Repository name")
    p.add_argument("--schedule", default="0 30 1 * * ?",
                   help="Cron schedule (default: daily at 01:30)")
    p.add_argument("--indices", default=None, help="Comma-separated indices")
    p.add_argument("--expire-after", default="30d", help="Retention period (default: 30d)")
    p.add_argument("--min-count", type=int, default=5, help="Minimum snapshots to keep")
    p.add_argument("--max-count", type=int, default=50, help="Maximum snapshots to keep")

    # execute-policy
    p = sub.add_parser("execute-policy", help="Execute SLM policy immediately")
    p.add_argument("policy", help="Policy name")

    # list-policies
    sub.add_parser("list-policies", help="List all SLM policies")

    # delete-policy
    p = sub.add_parser("delete-policy", help="Delete SLM policy")
    p.add_argument("policy", help="Policy name")

    # slm-stats
    sub.add_parser("slm-stats", help="Get SLM statistics")

    # cleanup
    p = sub.add_parser("cleanup", help="Remove old snapshots, keeping N most recent")
    p.add_argument("repo", help="Repository name")
    p.add_argument("--keep", type=int, default=10, help="Number of snapshots to keep")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    mgr = ElasticsearchSnapshotManager(
        es_host=args.host, username=args.user, password=args.password, ca_cert=args.ca_cert,
    )

    try:
        if args.command == "register-s3":
            mgr.register_s3_repository(args.repo, args.bucket,
                                       base_path=args.base_path, region=args.region)
        elif args.command == "register-fs":
            mgr.register_fs_repository(args.repo, args.location)
        elif args.command == "verify":
            mgr.verify_repository(args.repo)
        elif args.command == "list-repos":
            repos = mgr.get_repository()
            print(json.dumps(repos, indent=2))
        elif args.command == "delete-repo":
            mgr.delete_repository(args.repo)
        elif args.command == "snapshot":
            result = mgr.create_snapshot(args.repo, snapshot_name=args.name,
                                         indices=args.indices, wait_for_completion=args.wait)
            if args.wait:
                print(json.dumps(result, indent=2))
        elif args.command == "list-snapshots":
            mgr.list_snapshots(args.repo)
        elif args.command == "snapshot-status":
            result = mgr.get_snapshot_status(args.repo, args.name)
            print(json.dumps(result, indent=2))
        elif args.command == "delete-snapshot":
            mgr.delete_snapshot(args.repo, args.name)
        elif args.command == "restore":
            mgr.restore_snapshot(args.repo, args.name, indices=args.indices,
                                 rename_pattern=args.rename_pattern,
                                 rename_replacement=args.rename_replacement,
                                 wait_for_completion=args.wait)
        elif args.command == "restore-as":
            mgr.restore_to_different_index(args.repo, args.name, args.source, args.target)
        elif args.command == "create-policy":
            indices = args.indices.split(",") if args.indices else ["*"]
            mgr.create_slm_policy(args.policy, args.repo, args.schedule,
                                  indices=indices, expire_after=args.expire_after,
                                  min_count=args.min_count, max_count=args.max_count)
        elif args.command == "execute-policy":
            mgr.execute_slm_policy(args.policy)
        elif args.command == "list-policies":
            policies = mgr.get_slm_policy()
            print(json.dumps(policies, indent=2))
        elif args.command == "delete-policy":
            mgr.delete_slm_policy(args.policy)
        elif args.command == "slm-stats":
            stats = mgr.get_slm_stats()
            print(json.dumps(stats, indent=2))
        elif args.command == "cleanup":
            mgr.cleanup_old_snapshots(args.repo, keep_count=args.keep)
    except requests.HTTPError as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
