#!/usr/bin/env python3
import argparse
import json
import logging
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Optional

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ApiError, ConnectionError as ElasticsearchConnectionError


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def parse_json(value: Optional[str], argument_name: str) -> Dict[str, Any]:
    if not value:
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError(f"{argument_name} must be a JSON object")
    return parsed


def parse_csv(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class AppConfig:
    url: str
    username: Optional[str]
    password: Optional[str]
    api_key: Optional[str]
    ca_certs: Optional[str]
    ssl_assert_fingerprint: Optional[str]
    verify_certs: bool
    request_timeout: int
    documents_index: str
    logs_index: str

    @classmethod
    def from_env(cls) -> "AppConfig":
        url = os.getenv("ES_URL", "https://localhost:9200")
        username = os.getenv("ELASTICSEARCH_USERNAME")
        password = os.getenv("ELASTICSEARCH_PASSWORD")
        api_key = os.getenv("ELASTICSEARCH_API_KEY")
        if not api_key and not (username and password):
            raise ValueError(
                "Set ELASTICSEARCH_API_KEY or both ELASTICSEARCH_USERNAME and "
                "ELASTICSEARCH_PASSWORD before running this application."
            )
        return cls(
            url=url,
            username=username,
            password=password,
            api_key=api_key,
            ca_certs=os.getenv("ELASTICSEARCH_CA_CERTS"),
            ssl_assert_fingerprint=os.getenv("ELASTICSEARCH_SSL_FINGERPRINT"),
            verify_certs=parse_bool(os.getenv("ELASTICSEARCH_VERIFY_CERTS"), True),
            request_timeout=int(os.getenv("ELASTICSEARCH_REQUEST_TIMEOUT", "30")),
            documents_index=os.getenv("ELASTICSEARCH_DOCUMENTS_INDEX", "platform-documents"),
            logs_index=os.getenv("ELASTICSEARCH_LOGS_INDEX", "platform-logs"),
        )


class ElasticsearchLogHandler(logging.Handler):
    _reserved = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }

    def __init__(self, platform: "SearchLoggingPlatform", service_name: str, dataset: str) -> None:
        super().__init__()
        self.platform = platform
        self.service_name = service_name
        self.dataset = dataset

    def emit(self, record: logging.LogRecord) -> None:
        labels = {
            key: value
            for key, value in record.__dict__.items()
            if key not in self._reserved and not key.startswith("_") and value is not None
        }
        trace_id = getattr(record, "trace_id", None)
        correlation_id = getattr(record, "correlation_id", None)
        self.platform.index_log(
            service_name=self.service_name,
            level=record.levelname,
            message=record.getMessage(),
            dataset=self.dataset,
            fields=labels,
            trace_id=trace_id,
            correlation_id=correlation_id,
            timestamp=datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
        )


class SearchLoggingPlatform:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        client_kwargs: Dict[str, Any] = {
            "hosts": [config.url],
            "api_key": config.api_key,
            "verify_certs": config.verify_certs,
            "ca_certs": config.ca_certs,
            "ssl_assert_fingerprint": config.ssl_assert_fingerprint,
            "request_timeout": config.request_timeout,
        }
        if not config.api_key and config.username and config.password:
            client_kwargs["basic_auth"] = (config.username, config.password)
        self.client = Elasticsearch(**client_kwargs)

    def ping(self) -> bool:
        return bool(self.client.ping())

    def create_indices(self) -> Dict[str, Any]:
        created: Dict[str, Any] = {}
        if not self.client.indices.exists(index=self.config.documents_index):
            self.client.indices.create(
                index=self.config.documents_index,
                settings={"number_of_shards": 1, "number_of_replicas": 1},
                mappings={
                    "dynamic": "strict",
                    "properties": {
                        "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                        "summary": {"type": "text"},
                        "content": {"type": "text"},
                        "category": {"type": "keyword"},
                        "tags": {"type": "keyword"},
                        "metadata": {"type": "flattened"},
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"},
                    },
                },
            )
            created[self.config.documents_index] = "created"
        else:
            created[self.config.documents_index] = "exists"

        if not self.client.indices.exists(index=self.config.logs_index):
            self.client.indices.create(
                index=self.config.logs_index,
                settings={"number_of_shards": 1, "number_of_replicas": 1},
                mappings={
                    "dynamic": "strict",
                    "properties": {
                        "@timestamp": {"type": "date"},
                        "message": {"type": "text"},
                        "service": {"properties": {"name": {"type": "keyword"}}},
                        "event": {"properties": {"dataset": {"type": "keyword"}}},
                        "log": {"properties": {"level": {"type": "keyword"}}},
                        "labels": {"type": "flattened"},
                        "trace": {"properties": {"id": {"type": "keyword"}}},
                        "correlation": {"properties": {"id": {"type": "keyword"}}},
                    },
                },
            )
            created[self.config.logs_index] = "created"
        else:
            created[self.config.logs_index] = "exists"
        return created

    def index_document(
        self,
        title: str,
        content: str,
        *,
        summary: Optional[str] = None,
        category: str = "general",
        tags: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        document_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = utc_now()
        document = {
            "title": title,
            "summary": summary or content[:240],
            "content": content,
            "category": category,
            "tags": list(tags or []),
            "metadata": metadata or {},
            "created_at": now,
            "updated_at": now,
        }
        response = self.client.index(
            index=self.config.documents_index,
            id=document_id or str(uuid.uuid4()),
            document=document,
            refresh="wait_for",
        )
        return {
            "result": response["result"],
            "id": response["_id"],
            "index": response["_index"],
        }

    def search_documents(
        self,
        query_text: str,
        *,
        tags: Optional[list[str]] = None,
        category: Optional[str] = None,
        size: int = 10,
    ) -> Dict[str, Any]:
        filters: list[Dict[str, Any]] = []
        if tags:
            filters.append({"terms": {"tags": tags}})
        if category:
            filters.append({"term": {"category": category}})
        response = self.client.search(
            index=self.config.documents_index,
            size=size,
            track_total_hits=True,
            query={
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query_text,
                                "fields": ["title^4", "summary^2", "content", "category", "tags"],
                                "type": "best_fields",
                                "fuzziness": "AUTO",
                            }
                        }
                    ],
                    "filter": filters,
                }
            },
            sort=[{"_score": {"order": "desc"}}, {"updated_at": {"order": "desc"}}],
        )
        return {
            "total": response["hits"]["total"]["value"],
            "results": [
                {
                    "id": hit["_id"],
                    "score": hit["_score"],
                    "source": hit["_source"],
                }
                for hit in response["hits"]["hits"]
            ],
        }

    def index_log(
        self,
        *,
        service_name: str,
        level: str,
        message: str,
        dataset: str = "application",
        fields: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        document = {
            "@timestamp": timestamp or utc_now(),
            "message": message,
            "service": {"name": service_name},
            "event": {"dataset": dataset},
            "log": {"level": level.upper()},
            "labels": fields or {},
            "trace": {"id": trace_id or ""},
            "correlation": {"id": correlation_id or ""},
        }
        response = self.client.index(
            index=self.config.logs_index,
            document=document,
            refresh="wait_for",
        )
        return {
            "result": response["result"],
            "id": response["_id"],
            "index": response["_index"],
        }

    def search_logs(
        self,
        query_text: str,
        *,
        service_name: Optional[str] = None,
        level: Optional[str] = None,
        hours: int = 24,
        size: int = 20,
    ) -> Dict[str, Any]:
        filters: list[Dict[str, Any]] = [
            {"range": {"@timestamp": {"gte": (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()}}}
        ]
        if service_name:
            filters.append({"term": {"service.name": service_name}})
        if level:
            filters.append({"term": {"log.level": level.upper()}})

        if query_text == "*":
            query: Dict[str, Any] = {"bool": {"filter": filters}}
        else:
            query = {
                "bool": {
                    "must": [
                        {
                            "simple_query_string": {
                                "query": query_text,
                                "fields": ["message^3", "service.name", "event.dataset"],
                                "default_operator": "and",
                            }
                        }
                    ],
                    "filter": filters,
                }
            }

        response = self.client.search(
            index=self.config.logs_index,
            size=size,
            track_total_hits=True,
            query=query,
            sort=[{"@timestamp": {"order": "desc"}}],
        )
        return {
            "total": response["hits"]["total"]["value"],
            "results": [
                {
                    "id": hit["_id"],
                    "score": hit["_score"],
                    "source": hit["_source"],
                }
                for hit in response["hits"]["hits"]
            ],
        }

    def aggregate_logs(self, *, hours: int = 24, size: int = 10) -> Dict[str, Any]:
        time_from = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        response = self.client.search(
            index=self.config.logs_index,
            size=0,
            track_total_hits=True,
            query={"range": {"@timestamp": {"gte": time_from}}},
            aggs={
                "by_service": {
                    "terms": {"field": "service.name", "size": size},
                    "aggs": {
                        "by_level": {"terms": {"field": "log.level", "size": 10}},
                    },
                },
                "by_level": {"terms": {"field": "log.level", "size": 10}},
                "by_dataset": {"terms": {"field": "event.dataset", "size": size}},
                "timeline": {
                    "date_histogram": {
                        "field": "@timestamp",
                        "fixed_interval": "1h",
                        "min_doc_count": 0,
                    }
                },
            },
        )
        aggregations = response["aggregations"]
        return {
            "total": response["hits"]["total"]["value"],
            "window_hours": hours,
            "services": [
                {
                    "service": bucket["key"],
                    "count": bucket["doc_count"],
                    "levels": {level_bucket["key"]: level_bucket["doc_count"] for level_bucket in bucket["by_level"]["buckets"]},
                }
                for bucket in aggregations["by_service"]["buckets"]
            ],
            "levels": {bucket["key"]: bucket["doc_count"] for bucket in aggregations["by_level"]["buckets"]},
            "datasets": {bucket["key"]: bucket["doc_count"] for bucket in aggregations["by_dataset"]["buckets"]},
            "timeline": [
                {
                    "timestamp": bucket["key_as_string"],
                    "count": bucket["doc_count"],
                }
                for bucket in aggregations["timeline"]["buckets"]
            ],
        }

    def get_logger(self, service_name: str, dataset: str = "application") -> logging.Logger:
        logger = logging.getLogger(f"centralized-logging.{service_name}")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        if not any(isinstance(handler, ElasticsearchLogHandler) for handler in logger.handlers):
            logger.addHandler(ElasticsearchLogHandler(self, service_name=service_name, dataset=dataset))
        return logger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Centralized logging and full-text search application backed by Elasticsearch."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("create-indices", help="Create the search and logging indices.")

    index_document = subparsers.add_parser("index-document", help="Index a searchable document.")
    index_document.add_argument("--id", dest="document_id", help="Optional document identifier.")
    index_document.add_argument("--title", required=True, help="Document title.")
    index_document.add_argument("--summary", help="Optional document summary.")
    index_document.add_argument("--content", required=True, help="Document body content.")
    index_document.add_argument("--category", default="general", help="Document category.")
    index_document.add_argument("--tags", default="", help="Comma-separated tags.")
    index_document.add_argument("--metadata", default="{}", help="JSON object with additional metadata.")

    search_documents = subparsers.add_parser("search-documents", help="Run a full-text search query.")
    search_documents.add_argument("--query", required=True, help="Full-text search query.")
    search_documents.add_argument("--category", help="Optional category filter.")
    search_documents.add_argument("--tags", default="", help="Comma-separated tag filters.")
    search_documents.add_argument("--size", type=int, default=10, help="Maximum results to return.")

    emit_log = subparsers.add_parser("emit-log", help="Index a structured application log.")
    emit_log.add_argument("--service", required=True, help="Service name.")
    emit_log.add_argument("--level", default="INFO", help="Log level.")
    emit_log.add_argument("--message", required=True, help="Log message.")
    emit_log.add_argument("--dataset", default="application", help="Event dataset.")
    emit_log.add_argument("--fields", default="{}", help="JSON object with log labels.")
    emit_log.add_argument("--trace-id", help="Optional trace identifier.")
    emit_log.add_argument("--correlation-id", help="Optional correlation identifier.")

    search_logs = subparsers.add_parser("search-logs", help="Search centralized logs.")
    search_logs.add_argument("--query", default="*", help="Log query. Use * to match all logs.")
    search_logs.add_argument("--service", help="Optional service filter.")
    search_logs.add_argument("--level", help="Optional log level filter.")
    search_logs.add_argument("--hours", type=int, default=24, help="Time window to search.")
    search_logs.add_argument("--size", type=int, default=20, help="Maximum results to return.")

    aggregate_logs = subparsers.add_parser("aggregate-logs", help="Aggregate logs by service and level.")
    aggregate_logs.add_argument("--hours", type=int, default=24, help="Time window to aggregate.")
    aggregate_logs.add_argument("--size", type=int, default=10, help="Maximum buckets to return.")

    write_log = subparsers.add_parser("write-log", help="Write a log through Python logging integration.")
    write_log.add_argument("--service", required=True, help="Service name.")
    write_log.add_argument("--level", default="INFO", help="Log level.")
    write_log.add_argument("--message", required=True, help="Log message.")
    write_log.add_argument("--dataset", default="application", help="Event dataset.")
    write_log.add_argument("--fields", default="{}", help="JSON object with log labels.")
    write_log.add_argument("--trace-id", help="Optional trace identifier.")
    write_log.add_argument("--correlation-id", help="Optional correlation identifier.")

    return parser


def print_json(data: Dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, sort_keys=False))


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    config = AppConfig.from_env()
    platform = SearchLoggingPlatform(config)

    if not platform.ping():
        raise ValueError("Unable to connect to the Elasticsearch cluster.")

    if args.command == "create-indices":
        print_json(platform.create_indices())
        return 0

    platform.create_indices()

    if args.command == "index-document":
        print_json(
            platform.index_document(
                title=args.title,
                summary=args.summary,
                content=args.content,
                category=args.category,
                tags=parse_csv(args.tags),
                metadata=parse_json(args.metadata, "--metadata"),
                document_id=args.document_id,
            )
        )
        return 0

    if args.command == "search-documents":
        print_json(
            platform.search_documents(
                query_text=args.query,
                category=args.category,
                tags=parse_csv(args.tags),
                size=args.size,
            )
        )
        return 0

    if args.command == "emit-log":
        print_json(
            platform.index_log(
                service_name=args.service,
                level=args.level,
                message=args.message,
                dataset=args.dataset,
                fields=parse_json(args.fields, "--fields"),
                trace_id=args.trace_id,
                correlation_id=args.correlation_id,
            )
        )
        return 0

    if args.command == "search-logs":
        print_json(
            platform.search_logs(
                query_text=args.query,
                service_name=args.service,
                level=args.level,
                hours=args.hours,
                size=args.size,
            )
        )
        return 0

    if args.command == "aggregate-logs":
        print_json(platform.aggregate_logs(hours=args.hours, size=args.size))
        return 0

    if args.command == "write-log":
        logger = platform.get_logger(service_name=args.service, dataset=args.dataset)
        logger.log(
            getattr(logging, args.level.upper(), logging.INFO),
            args.message,
            extra={
                **parse_json(args.fields, "--fields"),
                "trace_id": args.trace_id,
                "correlation_id": args.correlation_id,
            },
        )
        print_json({"result": "logged", "service": args.service, "level": args.level.upper()})
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, json.JSONDecodeError, ApiError, ElasticsearchConnectionError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)