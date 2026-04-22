#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

from kafka.admin import (
    ConfigResource,
    ConfigResourceType,
    KafkaAdminClient,
    NewPartitions,
    NewTopic,
)


def parse_bootstrap(s: str) -> List[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


def parse_topic_configs(items: Optional[Sequence[str]]) -> Optional[Dict[str, str]]:
    if not items:
        return None
    out: Dict[str, str] = {}
    for raw in items:
        if "=" not in raw:
            raise ValueError(f"config must be KEY=value, got: {raw!r}")
        k, v = raw.split("=", 1)
        out[k.strip()] = v.strip()
    return out or None


def _future_result(obj: Any) -> Any:
    res = getattr(obj, "result", None)
    if callable(res):
        return res()
    return obj


def make_admin(ns: argparse.Namespace) -> KafkaAdminClient:
    kwargs: Dict[str, Any] = {
        "bootstrap_servers": parse_bootstrap(ns.bootstrap_servers),
        "client_id": ns.client_id,
        "request_timeout_ms": ns.request_timeout_ms,
    }
    if ns.security_protocol:
        kwargs["security_protocol"] = ns.security_protocol
    if ns.sasl_mechanism:
        kwargs["sasl_mechanism"] = ns.sasl_mechanism
    if ns.sasl_plain_username is not None:
        kwargs["sasl_plain_username"] = ns.sasl_plain_username
    if ns.sasl_plain_password is not None:
        kwargs["sasl_plain_password"] = ns.sasl_plain_password
    if ns.ssl_cafile:
        kwargs["ssl_cafile"] = ns.ssl_cafile
    if ns.ssl_certfile:
        kwargs["ssl_certfile"] = ns.ssl_certfile
    if ns.ssl_keyfile:
        kwargs["ssl_keyfile"] = ns.ssl_keyfile
    return KafkaAdminClient(**kwargs)


def collect_topics(ns: argparse.Namespace) -> List[str]:
    topics: List[str] = []
    if getattr(ns, "topic", None):
        topics.extend(ns.topic)
    if getattr(ns, "topics", None):
        for chunk in ns.topics:
            topics.extend(t.strip() for t in chunk.split(",") if t.strip())
    seen = set()
    ordered: List[str] = []
    for t in topics:
        if t not in seen:
            seen.add(t)
            ordered.append(t)
    return ordered


def cmd_create(admin: KafkaAdminClient, ns: argparse.Namespace) -> int:
    names = collect_topics(ns)
    if not names:
        print("error: no topics (use --topic or --topics)", file=sys.stderr)
        return 2
    topic_cfgs = parse_topic_configs(ns.config)
    new_topics = [
        NewTopic(
            name=n,
            num_partitions=ns.partitions,
            replication_factor=ns.replication_factor,
            topic_configs=topic_cfgs,
        )
        for n in names
    ]
    fs = admin.create_topics(
        new_topics=new_topics,
        timeout_ms=ns.timeout_ms,
        validate_only=ns.validate_only,
    )
    for name, fut in fs.items():
        fut.result()
        print(f"created topic: {name}")
    return 0


def cmd_delete(admin: KafkaAdminClient, ns: argparse.Namespace) -> int:
    names = collect_topics(ns)
    if not names:
        print("error: no topics", file=sys.stderr)
        return 2
    fs = admin.delete_topics(topics=names, timeout_ms=ns.timeout_ms)
    for name, fut in fs.items():
        fut.result()
        print(f"deleted topic: {name}")
    return 0


def cmd_list(admin: KafkaAdminClient, ns: argparse.Namespace) -> int:
    meta = _future_result(admin.list_topics(timeout_ms=ns.timeout_ms))
    names = sorted(meta.topics.keys())
    if ns.json:
        print(json.dumps({"topics": names}, indent=2))
    else:
        for n in names:
            print(n)
    return 0


def cmd_describe(admin: KafkaAdminClient, ns: argparse.Namespace) -> int:
    names = collect_topics(ns)
    if not names:
        print("error: no topics", file=sys.stderr)
        return 2
    fs = admin.describe_topics(topics=names, timeout_ms=ns.timeout_ms)
    rows: List[Dict[str, Any]] = []
    for name, fut in fs.items():
        td = fut.result()
        part_info = []
        for pid, p in sorted(td.partitions.items()):
            part_info.append(
                {
                    "partition": pid,
                    "leader": p.leader,
                    "replicas": list(p.replicas),
                    "isr": list(p.isr),
                }
            )
        rows.append(
            {
                "topic": name,
                "topic_id": str(td.topic_id) if getattr(td, "topic_id", None) else None,
                "internal": bool(getattr(td, "is_internal", False)),
                "partitions": part_info,
            }
        )
    if ns.json:
        print(json.dumps(rows, indent=2))
    else:
        for r in rows:
            print(f"topic={r['topic']} internal={r['internal']} partitions={len(r['partitions'])}")
            for p in r["partitions"]:
                print(
                    f"  p{p['partition']}: leader={p['leader']} "
                    f"replicas={p['replicas']} isr={p['isr']}"
                )
    return 0


def cmd_alter_partitions(admin: KafkaAdminClient, ns: argparse.Namespace) -> int:
    names = collect_topics(ns)
    if not names:
        print("error: no topics", file=sys.stderr)
        return 2
    if ns.partitions < 1:
        print("error: --partitions must be >= 1", file=sys.stderr)
        return 2
    topic_parts = {n: NewPartitions(total_count=ns.partitions) for n in names}
    fs = admin.create_partitions(
        topic_partitions=topic_parts,
        timeout_ms=ns.timeout_ms,
        validate_only=ns.validate_only,
    )
    for name, fut in fs.items():
        fut.result()
        print(f"partitions set for {name} -> total_count={ns.partitions}")
    return 0


def _config_resource(topic: str) -> ConfigResource:
    return ConfigResource(ConfigResourceType.TOPIC, topic)


def cmd_describe_config(admin: KafkaAdminClient, ns: argparse.Namespace) -> int:
    names = collect_topics(ns)
    if len(names) != 1:
        print("error: describe-config requires exactly one topic", file=sys.stderr)
        return 2
    topic = names[0]
    resources = [_config_resource(topic)]
    fs = admin.describe_configs(config_resources=resources, include_synonyms=ns.include_synonyms)
    for res, fut in fs.items():
        result = fut.result()
        entries = []
        for name, cv in result.items():
            entries.append(
                {
                    "name": name,
                    "value": cv.value,
                    "read_only": cv.read_only,
                    "is_default": getattr(cv, "is_default", None),
                }
            )
        entries.sort(key=lambda x: x["name"])
        if ns.json:
            print(json.dumps({"topic": topic, "configs": entries}, indent=2))
        else:
            for e in entries:
                print(f"{e['name']}={e['value']}")
    return 0


def cmd_alter_config(admin: KafkaAdminClient, ns: argparse.Namespace) -> int:
    names = collect_topics(ns)
    if len(names) != 1:
        print("error: alter-config requires exactly one topic", file=sys.stderr)
        return 2
    topic = names[0]
    cfgs = parse_topic_configs(ns.config)
    if not cfgs:
        print("error: pass at least one --config KEY=value", file=sys.stderr)
        return 2
    resource = _config_resource(topic)
    pairs: List[Tuple[str, str]] = list(cfgs.items())
    fs = admin.alter_configs(
        config_resources=[(resource, pairs)],
        validate_only=ns.validate_only,
    )
    for _, fut in fs.items():
        fut.result()
    print(f"altered configs for topic {topic}: {', '.join(cfgs.keys())}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Kafka AdminClient automation")
    p.add_argument(
        "--bootstrap-servers",
        default="localhost:9092",
        help="Comma-separated broker list",
    )
    p.add_argument("--client-id", default="kafka-cluster-admin")
    p.add_argument("--request-timeout-ms", type=int, default=30000)
    p.add_argument("--timeout-ms", type=int, default=60000, help="Admin operation timeout")
    p.add_argument("--security-protocol", default=None)
    p.add_argument("--sasl-mechanism", default=None)
    p.add_argument("--sasl-plain-username", default=None)
    p.add_argument("--sasl-plain-password", default=None)
    p.add_argument("--ssl-cafile", default=None)
    p.add_argument("--ssl-certfile", default=None)
    p.add_argument("--ssl-keyfile", default=None)

    sub = p.add_subparsers(dest="command", required=True)

    pc = sub.add_parser("create", help="Create topic(s)")
    pc.add_argument("--topic", action="append", default=[], metavar="NAME")
    pc.add_argument(
        "--topics",
        action="append",
        default=[],
        help="Comma-separated topic names (repeatable)",
    )
    pc.add_argument("--partitions", type=int, required=True)
    pc.add_argument("--replication-factor", type=int, required=True)
    pc.add_argument(
        "--config",
        action="append",
        dest="config",
        metavar="KEY=value",
        help="Topic config (repeatable), e.g. retention.ms=604800000",
    )
    pc.add_argument("--validate-only", action="store_true")
    pc.set_defaults(func=cmd_create)

    pd = sub.add_parser("delete", help="Delete topic(s)")
    pd.add_argument("--topic", action="append", default=[])
    pd.add_argument("--topics", action="append", default=[])
    pd.set_defaults(func=cmd_delete)

    pl = sub.add_parser("list", help="List topic names")
    pl.add_argument("--json", action="store_true")
    pl.set_defaults(func=cmd_list)

    pr = sub.add_parser("describe", help="Describe topic metadata / partitions")
    pr.add_argument("--topic", action="append", default=[])
    pr.add_argument("--topics", action="append", default=[])
    pr.add_argument("--json", action="store_true")
    pr.set_defaults(func=cmd_describe)

    pp = sub.add_parser("alter-partitions", help="Increase partition count")
    pp.add_argument("--topic", action="append", default=[])
    pp.add_argument("--topics", action="append", default=[])
    pp.add_argument("--partitions", type=int, required=True, help="New total partition count")
    pp.add_argument("--validate-only", action="store_true")
    pp.set_defaults(func=cmd_alter_partitions)

    pdc = sub.add_parser("describe-config", help="Describe topic configuration")
    pdc.add_argument("--topic", action="append", default=[])
    pdc.add_argument("--topics", action="append", default=[])
    pdc.add_argument("--include-synonyms", action="store_true")
    pdc.add_argument("--json", action="store_true")
    pdc.set_defaults(func=cmd_describe_config)

    pac = sub.add_parser("alter-config", help="Alter topic configuration")
    pac.add_argument("--topic", action="append", default=[])
    pac.add_argument("--topics", action="append", default=[])
    pac.add_argument("--config", action="append", dest="config", metavar="KEY=value", required=True)
    pac.add_argument("--validate-only", action="store_true")
    pac.set_defaults(func=cmd_alter_config)

    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    admin = make_admin(args)
    try:
        return int(args.func(admin, args))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        admin.close()


if __name__ == "__main__":
    raise SystemExit(main())
