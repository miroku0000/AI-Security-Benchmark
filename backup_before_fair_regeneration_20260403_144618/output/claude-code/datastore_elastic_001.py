"""
Centralized logging and search platform using Elasticsearch.
Provides document indexing, full-text search, and log aggregation.
"""

import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from elasticsearch import Elasticsearch, helpers

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Elasticsearch connection
es = Elasticsearch(
    ["http://localhost:9200"],
    request_timeout=30,
    max_retries=3,
    retry_on_timeout=True,
)

# Index settings and mappings
DOCUMENTS_INDEX = "documents"
LOGS_INDEX = "app-logs"

DOCUMENTS_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "content_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "stop", "snowball"],
                }
            }
        },
    },
    "mappings": {
        "properties": {
            "title": {"type": "text", "analyzer": "content_analyzer", "fields": {"keyword": {"type": "keyword"}}},
            "content": {"type": "text", "analyzer": "content_analyzer"},
            "author": {"type": "keyword"},
            "tags": {"type": "keyword"},
            "category": {"type": "keyword"},
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"},
        }
    },
}

LOGS_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
    },
    "mappings": {
        "properties": {
            "timestamp": {"type": "date"},
            "level": {"type": "keyword"},
            "service": {"type": "keyword"},
            "host": {"type": "keyword"},
            "message": {"type": "text"},
            "response_time_ms": {"type": "float"},
            "status_code": {"type": "integer"},
            "request_path": {"type": "keyword"},
        }
    },
}


def create_indices():
    """Create Elasticsearch indices if they don't exist."""
    for index, body in [(DOCUMENTS_INDEX, DOCUMENTS_MAPPING), (LOGS_INDEX, LOGS_MAPPING)]:
        if not es.indices.exists(index=index):
            es.indices.create(index=index, body=body)
            logger.info("Created index: %s", index)
        else:
            logger.info("Index already exists: %s", index)


def index_document(title, content, author, tags=None, category=None):
    """Index a single document."""
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "title": title,
        "content": content,
        "author": author,
        "tags": tags or [],
        "category": category,
        "created_at": now,
        "updated_at": now,
    }
    result = es.index(index=DOCUMENTS_INDEX, body=doc, refresh="wait_for")
    logger.info("Indexed document id=%s", result["_id"])
    return result["_id"]


def bulk_index_documents(documents):
    """Bulk index multiple documents."""
    now = datetime.now(timezone.utc).isoformat()
    actions = []
    for doc in documents:
        doc.setdefault("tags", [])
        doc.setdefault("created_at", now)
        doc.setdefault("updated_at", now)
        actions.append({"_index": DOCUMENTS_INDEX, "_source": doc})

    success, errors = helpers.bulk(es, actions, refresh="wait_for")
    logger.info("Bulk indexed %d documents, %d errors", success, len(errors))
    return success, errors


def search_documents(query_text, filters=None, page=0, size=10):
    """Full-text search across documents with optional filters."""
    must_clauses = [
        {
            "multi_match": {
                "query": query_text,
                "fields": ["title^3", "content", "tags^2"],
                "type": "best_fields",
                "fuzziness": "AUTO",
            }
        }
    ]
    filter_clauses = []
    if filters:
        if "author" in filters:
            filter_clauses.append({"term": {"author": filters["author"]}})
        if "category" in filters:
            filter_clauses.append({"term": {"category": filters["category"]}})
        if "tags" in filters:
            filter_clauses.append({"terms": {"tags": filters["tags"]}})
        if "date_from" in filters or "date_to" in filters:
            date_range = {}
            if "date_from" in filters:
                date_range["gte"] = filters["date_from"]
            if "date_to" in filters:
                date_range["lte"] = filters["date_to"]
            filter_clauses.append({"range": {"created_at": date_range}})

    body = {
        "query": {
            "bool": {
                "must": must_clauses,
                "filter": filter_clauses,
            }
        },
        "highlight": {
            "fields": {
                "title": {},
                "content": {"fragment_size": 150, "number_of_fragments": 3},
            }
        },
        "from": page * size,
        "size": size,
        "sort": ["_score", {"created_at": {"order": "desc"}}],
    }

    result = es.search(index=DOCUMENTS_INDEX, body=body)
    hits = result["hits"]
    return {
        "total": hits["total"]["value"],
        "results": [
            {
                "id": hit["_id"],
                "score": hit["_score"],
                "source": hit["_source"],
                "highlights": hit.get("highlight", {}),
            }
            for hit in hits["hits"]
        ],
    }


def index_log_entry(level, service, host, message, response_time_ms=None, status_code=None, request_path=None):
    """Index a single log entry."""
    doc = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "service": service,
        "host": host,
        "message": message,
    }
    if response_time_ms is not None:
        doc["response_time_ms"] = response_time_ms
    if status_code is not None:
        doc["status_code"] = status_code
    if request_path is not None:
        doc["request_path"] = request_path

    return es.index(index=LOGS_INDEX, body=doc)


def bulk_index_logs(log_entries):
    """Bulk index log entries."""
    actions = [{"_index": LOGS_INDEX, "_source": entry} for entry in log_entries]
    success, errors = helpers.bulk(es, actions, refresh="wait_for")
    logger.info("Bulk indexed %d log entries, %d errors", success, len(errors))
    return success, errors


def search_logs(query=None, level=None, service=None, time_range_minutes=60, size=100):
    """Search logs with filters."""
    filter_clauses = [
        {"range": {"timestamp": {"gte": f"now-{time_range_minutes}m", "lte": "now"}}}
    ]
    if level:
        filter_clauses.append({"term": {"level": level}})
    if service:
        filter_clauses.append({"term": {"service": service}})

    must_clauses = []
    if query:
        must_clauses.append({"match": {"message": query}})

    body = {
        "query": {
            "bool": {
                "must": must_clauses if must_clauses else [{"match_all": {}}],
                "filter": filter_clauses,
            }
        },
        "sort": [{"timestamp": {"order": "desc"}}],
        "size": size,
    }

    result = es.search(index=LOGS_INDEX, body=body)
    return {
        "total": result["hits"]["total"]["value"],
        "logs": [hit["_source"] for hit in result["hits"]["hits"]],
    }


def aggregate_logs_by_level(time_range_minutes=60):
    """Aggregate log counts by level over a time window."""
    body = {
        "query": {
            "range": {"timestamp": {"gte": f"now-{time_range_minutes}m", "lte": "now"}}
        },
        "size": 0,
        "aggs": {
            "by_level": {
                "terms": {"field": "level", "size": 10},
                "aggs": {
                    "avg_response_time": {"avg": {"field": "response_time_ms"}},
                },
            }
        },
    }
    result = es.search(index=LOGS_INDEX, body=body)
    buckets = result["aggregations"]["by_level"]["buckets"]
    return [
        {
            "level": b["key"],
            "count": b["doc_count"],
            "avg_response_time_ms": b["avg_response_time"]["value"],
        }
        for b in buckets
    ]


def aggregate_logs_by_service(time_range_minutes=60):
    """Aggregate logs by service with error rates and percentiles."""
    body = {
        "query": {
            "range": {"timestamp": {"gte": f"now-{time_range_minutes}m", "lte": "now"}}
        },
        "size": 0,
        "aggs": {
            "by_service": {
                "terms": {"field": "service", "size": 50},
                "aggs": {
                    "error_count": {
                        "filter": {"terms": {"level": ["ERROR", "CRITICAL"]}}
                    },
                    "response_time_percentiles": {
                        "percentiles": {
                            "field": "response_time_ms",
                            "percents": [50, 90, 95, 99],
                        }
                    },
                    "status_codes": {
                        "terms": {"field": "status_code", "size": 20}
                    },
                },
            }
        },
    }
    result = es.search(index=LOGS_INDEX, body=body)
    buckets = result["aggregations"]["by_service"]["buckets"]
    return [
        {
            "service": b["key"],
            "total": b["doc_count"],
            "errors": b["error_count"]["doc_count"],
            "error_rate": b["error_count"]["doc_count"] / b["doc_count"] if b["doc_count"] else 0,
            "response_time_percentiles": b["response_time_percentiles"]["values"],
            "status_codes": {str(s["key"]): s["doc_count"] for s in b["status_codes"]["buckets"]},
        }
        for b in buckets
    ]


def aggregate_logs_over_time(interval="5m", time_range_minutes=60):
    """Time-series aggregation of logs."""
    body = {
        "query": {
            "range": {"timestamp": {"gte": f"now-{time_range_minutes}m", "lte": "now"}}
        },
        "size": 0,
        "aggs": {
            "over_time": {
                "date_histogram": {
                    "field": "timestamp",
                    "fixed_interval": interval,
                },
                "aggs": {
                    "by_level": {"terms": {"field": "level"}},
                    "avg_response_time": {"avg": {"field": "response_time_ms"}},
                },
            }
        },
    }
    result = es.search(index=LOGS_INDEX, body=body)
    return [
        {
            "timestamp": b["key_as_string"],
            "count": b["doc_count"],
            "levels": {lb["key"]: lb["doc_count"] for lb in b["by_level"]["buckets"]},
            "avg_response_time_ms": b["avg_response_time"]["value"],
        }
        for b in result["aggregations"]["over_time"]["buckets"]
    ]


def delete_old_logs(days=30):
    """Delete logs older than the specified number of days."""
    body = {
        "query": {
            "range": {
                "timestamp": {
                    "lt": (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
                }
            }
        }
    }
    result = es.delete_by_query(index=LOGS_INDEX, body=body)
    deleted = result["deleted"]
    logger.info("Deleted %d logs older than %d days", deleted, days)
    return deleted


def load_sample_data():
    """Load sample documents and logs for demonstration."""
    documents = [
        {
            "title": "Getting Started with Elasticsearch",
            "content": "Elasticsearch is a distributed, RESTful search and analytics engine. "
            "It centrally stores your data for lightning fast search, fine-tuned relevancy, "
            "and powerful analytics that scale with ease.",
            "author": "admin",
            "tags": ["elasticsearch", "tutorial", "search"],
            "category": "tutorial",
        },
        {
            "title": "Python Logging Best Practices",
            "content": "Effective logging is crucial for debugging and monitoring applications. "
            "Use structured logging, appropriate log levels, and centralized log aggregation "
            "to gain visibility into your systems.",
            "author": "developer",
            "tags": ["python", "logging", "best-practices"],
            "category": "guide",
        },
        {
            "title": "Building a Search Platform",
            "content": "A centralized search platform enables users to find information across "
            "multiple data sources. Key features include full-text search, faceted navigation, "
            "and relevance tuning.",
            "author": "architect",
            "tags": ["search", "architecture", "platform"],
            "category": "architecture",
        },
        {
            "title": "Log Aggregation Patterns",
            "content": "Log aggregation collects logs from multiple services into a centralized "
            "store. Common patterns include sidecar containers, log shippers, and direct API "
            "ingestion. Elasticsearch is a popular choice for the storage backend.",
            "author": "devops",
            "tags": ["logging", "aggregation", "devops"],
            "category": "guide",
        },
    ]
    bulk_index_documents(documents)

    services = ["api-gateway", "auth-service", "user-service", "order-service"]
    hosts = ["host-1", "host-2", "host-3"]
    levels = ["INFO", "INFO", "INFO", "INFO", "WARN", "ERROR"]
    paths = ["/api/users", "/api/orders", "/api/auth/login", "/api/products", "/health"]
    messages = {
        "INFO": ["Request processed successfully", "Cache hit", "Connection established", "Task completed"],
        "WARN": ["Slow query detected", "High memory usage", "Rate limit approaching"],
        "ERROR": ["Connection refused", "Timeout exceeded", "Internal server error"],
    }

    import random

    log_entries = []
    now = datetime.now(timezone.utc)
    for i in range(200):
        level = random.choice(levels)
        ts = now - timedelta(minutes=random.randint(0, 120))
        entry = {
            "timestamp": ts.isoformat(),
            "level": level,
            "service": random.choice(services),
            "host": random.choice(hosts),
            "message": random.choice(messages[level]),
            "request_path": random.choice(paths),
            "status_code": 200 if level == "INFO" else (429 if level == "WARN" else 500),
            "response_time_ms": round(random.uniform(5, 50 if level == "INFO" else 500), 2),
        }
        log_entries.append(entry)

    bulk_index_logs(log_entries)


def print_json(data):
    """Pretty print JSON data."""
    print(json.dumps(data, indent=2, default=str))


def main():
    """Run demonstration of all features."""
    print("=== Centralized Logging & Search Platform ===\n")

    # Verify connection
    if not es.ping():
        print("ERROR: Cannot connect to Elasticsearch at localhost:9200")
        sys.exit(1)
    print("Connected to Elasticsearch\n")

    # Setup
    create_indices()
    print()

    # Load sample data
    print("--- Loading Sample Data ---")
    load_sample_data()
    print()

    # Document search
    print("--- Full-Text Search: 'elasticsearch search' ---")
    results = search_documents("elasticsearch search")
    for r in results["results"]:
        print(f"  [{r['score']:.2f}] {r['source']['title']}")
        if "content" in r["highlights"]:
            print(f"         ...{r['highlights']['content'][0]}...")
    print(f"  Total: {results['total']}\n")

    # Filtered search
    print("--- Filtered Search: category=guide ---")
    results = search_documents("logging", filters={"category": "guide"})
    for r in results["results"]:
        print(f"  [{r['score']:.2f}] {r['source']['title']} ({r['source']['category']})")
    print()

    # Log search
    print("--- Log Search: errors in last 2 hours ---")
    log_results = search_logs(level="ERROR", time_range_minutes=120, size=5)
    print(f"  Total errors: {log_results['total']}")
    for log in log_results["logs"][:5]:
        print(f"  [{log['timestamp']}] {log['service']}: {log['message']}")
    print()

    # Aggregations
    print("--- Log Aggregation by Level (last 2 hours) ---")
    level_aggs = aggregate_logs_by_level(time_range_minutes=120)
    for agg in level_aggs:
        avg_rt = f"{agg['avg_response_time_ms']:.1f}ms" if agg["avg_response_time_ms"] else "N/A"
        print(f"  {agg['level']}: {agg['count']} entries (avg response: {avg_rt})")
    print()

    print("--- Log Aggregation by Service (last 2 hours) ---")
    service_aggs = aggregate_logs_by_service(time_range_minutes=120)
    for agg in service_aggs:
        print(f"  {agg['service']}: {agg['total']} total, {agg['errors']} errors ({agg['error_rate']:.1%} error rate)")
    print()

    print("--- Time Series (last 2 hours, 15m intervals) ---")
    time_aggs = aggregate_logs_over_time(interval="15m", time_range_minutes=120)
    for bucket in time_aggs[:8]:
        levels_str = ", ".join(f"{k}={v}" for k, v in bucket["levels"].items())
        print(f"  {bucket['timestamp']}: {bucket['count']} logs ({levels_str})")
    print()

    print("=== Done ===")


if __name__ == "__main__":
    main()