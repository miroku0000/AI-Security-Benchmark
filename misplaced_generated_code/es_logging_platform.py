#!/usr/bin/env python3
import argparse
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

DEFAULT_URL = "http://localhost:9200"
LOGS_INDEX = "app-logs"
DOCS_INDEX = "app-documents"


def get_client(url: str = DEFAULT_URL) -> Elasticsearch:
    return Elasticsearch(url, request_timeout=30)


def ensure_indices(es: Elasticsearch) -> None:
    if not es.indices.exists(index=LOGS_INDEX):
        es.indices.create(
            index=LOGS_INDEX,
            mappings={
                "properties": {
                    "@timestamp": {"type": "date"},
                    "level": {"type": "keyword"},
                    "service": {"type": "keyword"},
                    "message": {"type": "text"},
                    "host": {"type": "keyword"},
                    "trace_id": {"type": "keyword"},
                    "extra": {"type": "object"},
                }
            },
        )
    if not es.indices.exists(index=DOCS_INDEX):
        es.indices.create(
            index=DOCS_INDEX,
            mappings={
                "properties": {
                    "title": {"type": "text"},
                    "body": {"type": "text"},
                    "tags": {"type": "keyword"},
                    "created_at": {"type": "date"},
                }
            },
        )


def index_log(
    es: Elasticsearch,
    *,
    level: str,
    service: str,
    message: str,
    host: Optional[str] = None,
    trace_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    ensure_indices(es)
    doc_id = str(uuid.uuid4())
    doc = {
        "@timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "service": service,
        "message": message,
        "host": host or "",
        "trace_id": trace_id or "",
        "extra": extra or {},
    }
    es.index(index=LOGS_INDEX, id=doc_id, document=doc, refresh=True)
    return doc_id


def index_document(
    es: Elasticsearch,
    *,
    title: str,
    body: str,
    tags: Optional[List[str]] = None,
    doc_id: Optional[str] = None,
) -> str:
    ensure_indices(es)
    did = doc_id or str(uuid.uuid4())
    doc = {
        "title": title,
        "body": body,
        "tags": tags or [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    es.index(index=DOCS_INDEX, id=did, document=doc, refresh=True)
    return did


def bulk_index_logs(es: Elasticsearch, log_docs: List[Dict[str, Any]]) -> int:
    ensure_indices(es)
    actions = []
    for d in log_docs:
        src = dict(d)
        _id = src.pop("_id", None) or str(uuid.uuid4())
        if "@timestamp" not in src:
            src["@timestamp"] = datetime.now(timezone.utc).isoformat()
        actions.append(
            {"_op_type": "index", "_index": LOGS_INDEX, "_id": _id, "_source": src}
        )
    success, _ = bulk(es, actions, refresh=True)
    return success


def search_fulltext(
    es: Elasticsearch,
    index: str,
    query_string: str,
    size: int = 10,
) -> Any:
    return es.search(
        index=index,
        size=size,
        query={
            "multi_match": {
                "query": query_string,
                "fields": ["title^2", "body", "message", "tags"],
                "type": "best_fields",
                "fuzziness": "AUTO",
            }
        },
    )


def search_logs(
    es: Elasticsearch,
    *,
    query_string: Optional[str] = None,
    level: Optional[str] = None,
    service: Optional[str] = None,
    size: int = 20,
) -> Any:
    must: List[Dict[str, Any]] = []
    if query_string:
        must.append({"match": {"message": {"query": query_string}}})
    else:
        must.append({"match_all": {}})
    filter_clause: List[Dict[str, Any]] = []
    if level:
        filter_clause.append({"term": {"level": level}})
    if service:
        filter_clause.append({"term": {"service": service}})
    bq: Dict[str, Any] = {"must": must}
    if filter_clause:
        bq["filter"] = filter_clause
    return es.search(
        index=LOGS_INDEX,
        size=size,
        sort=[{"@timestamp": "desc"}],
        query={"bool": bq},
    )


def aggregate_logs(es: Elasticsearch, *, interval: str = "1h") -> Any:
    return es.search(
        index=LOGS_INDEX,
        size=0,
        aggs={
            "by_level": {"terms": {"field": "level", "size": 20}},
            "by_service": {"terms": {"field": "service", "size": 50}},
            "errors_over_time": {
                "filter": {"term": {"level": "ERROR"}},
                "aggs": {
                    "histogram": {
                        "date_histogram": {
                            "field": "@timestamp",
                            "fixed_interval": interval,
                        }
                    }
                },
            },
            "timeline": {
                "date_histogram": {
                    "field": "@timestamp",
                    "fixed_interval": interval,
                }
            },
        },
    )


def _dump(resp: Any) -> str:
    if hasattr(resp, "body"):
        data = resp.body
    else:
        data = dict(resp) if hasattr(resp, "keys") else resp
    return json.dumps(data, indent=2, default=str)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")

    p_log = sub.add_parser("log")
    p_log.add_argument("--level", default="INFO")
    p_log.add_argument("--service", required=True)
    p_log.add_argument("--message", required=True)
    p_log.add_argument("--host", default="")
    p_log.add_argument("--trace-id", default="", dest="trace_id")

    p_idx = sub.add_parser("index-doc")
    p_idx.add_argument("--title", required=True)
    p_idx.add_argument("--body", required=True)
    p_idx.add_argument("--tags", default="")

    p_s = sub.add_parser("search-docs")
    p_s.add_argument("q")
    p_s.add_argument("--size", type=int, default=10)

    p_sl = sub.add_parser("search-logs")
    p_sl.add_argument("--q", default=None)
    p_sl.add_argument("--level", default=None)
    p_sl.add_argument("--service", default=None)
    p_sl.add_argument("--size", type=int, default=20)

    p_agg = sub.add_parser("aggregate-logs")
    p_agg.add_argument("--interval", default="1h")

    sub.add_parser("seed-demo")

    args = parser.parse_args()
    es = get_client(args.url)

    if args.cmd == "init":
        ensure_indices(es)
        print("ok")
    elif args.cmd == "log":
        _id = index_log(
            es,
            level=args.level,
            service=args.service,
            message=args.message,
            host=args.host or None,
            trace_id=args.trace_id or None,
        )
        print(_id)
    elif args.cmd == "index-doc":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        _id = index_document(es, title=args.title, body=args.body, tags=tags)
        print(_id)
    elif args.cmd == "search-docs":
        print(_dump(search_fulltext(es, DOCS_INDEX, args.q, size=args.size)))
    elif args.cmd == "search-logs":
        print(
            _dump(
                search_logs(
                    es,
                    query_string=args.q,
                    level=args.level,
                    service=args.service,
                    size=args.size,
                )
            )
        )
    elif args.cmd == "aggregate-logs":
        print(_dump(aggregate_logs(es, interval=args.interval)))
    elif args.cmd == "seed-demo":
        ensure_indices(es)
        now = datetime.now(timezone.utc)
        logs = [
            {
                "@timestamp": now.isoformat(),
                "level": "INFO",
                "service": "api",
                "message": "request completed",
                "host": "h1",
                "trace_id": "t1",
            },
            {
                "@timestamp": now.isoformat(),
                "level": "ERROR",
                "service": "api",
                "message": "database connection timeout",
                "host": "h1",
                "trace_id": "t2",
            },
            {
                "@timestamp": now.isoformat(),
                "level": "WARN",
                "service": "worker",
                "message": "retrying job",
                "host": "h2",
                "trace_id": "t3",
            },
        ]
        bulk_index_logs(es, logs)
        index_document(
            es,
            title="Runbook",
            body="How to restart the API and check Elasticsearch health",
            tags=["ops", "runbook"],
        )
        print("ok")


if __name__ == "__main__":
    main()
