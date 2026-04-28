import os
from typing import Any, Dict, List

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError as ElasticsearchConnectionError
from elasticsearch.exceptions import TransportError
from flask import Flask, jsonify, request

DEFAULT_ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
DEFAULT_ELASTICSEARCH_INDEX = os.getenv("ELASTICSEARCH_INDEX", "products")
DEFAULT_RESULT_SIZE = 20
MAX_RESULT_SIZE = 100
MAX_QUERY_LENGTH = 100


def get_int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    value = int(raw_value)
    return max(minimum, min(value, maximum))


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["ELASTICSEARCH_INDEX"] = DEFAULT_ELASTICSEARCH_INDEX
    app.config["SEARCH_RESULT_SIZE"] = get_int_env(
        "SEARCH_RESULT_SIZE",
        DEFAULT_RESULT_SIZE,
        1,
        MAX_RESULT_SIZE,
    )
    app.config["ELASTICSEARCH_CLIENT"] = Elasticsearch(
        DEFAULT_ELASTICSEARCH_URL,
        request_timeout=float(os.getenv("ELASTICSEARCH_TIMEOUT_SECONDS", "1.5")),
        max_retries=get_int_env("ELASTICSEARCH_MAX_RETRIES", 2, 0, 5),
        retry_on_timeout=True,
        http_compress=True,
    )

    @app.get("/api/search")
    def search_products() -> Any:
        query = request.args.get("q", "").strip()
        if not query:
            return jsonify({"error": "Missing required query parameter: q"}), 400

        if len(query) > MAX_QUERY_LENGTH:
            return jsonify(
                {"error": f"Query parameter q must be {MAX_QUERY_LENGTH} characters or fewer"}
            ), 400

        client: Elasticsearch = app.config["ELASTICSEARCH_CLIENT"]
        index_name: str = app.config["ELASTICSEARCH_INDEX"]
        result_size: int = app.config["SEARCH_RESULT_SIZE"]

        try:
            response = client.search(
                index=index_name,
                size=result_size,
                track_total_hits=False,
                query={
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "name^4",
                            "description^2",
                            "brand^2",
                            "category^2",
                            "sku",
                        ],
                        "type": "best_fields",
                        "operator": "and",
                    }
                },
            )
        except ElasticsearchConnectionError:
            return jsonify({"error": "Search backend unavailable"}), 503
        except TransportError:
            return jsonify({"error": "Search request failed"}), 502

        hits = response["hits"]["hits"]
        products: List[Dict[str, Any]] = []

        for hit in hits:
            source = hit.get("_source", {})
            product = dict(source)
            product.setdefault("id", hit.get("_id"))
            product["score"] = hit.get("_score")
            products.append(product)

        return jsonify(
            {
                "query": query,
                "count": len(products),
                "products": products,
            }
        )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        threaded=True,
    )