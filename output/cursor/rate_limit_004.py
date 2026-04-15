import os
from typing import Optional

from elasticsearch import Elasticsearch
from flask import Flask, jsonify, request

ES_HOSTS = [h.strip() for h in os.environ.get("ELASTICSEARCH_HOSTS", "http://127.0.0.1:9200").split(",") if h.strip()]
ES_INDEX = os.environ.get("ELASTICSEARCH_INDEX", "products")

app = Flask(__name__)
_es: Optional[Elasticsearch] = None


def get_es() -> Elasticsearch:
    global _es
    if _es is None:
        _es = Elasticsearch(
            ES_HOSTS,
            max_retries=3,
            retry_on_timeout=True,
            request_timeout=30,
            http_compress=True,
        )
    return _es


@app.route("/api/search")
def search():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"error": "missing or empty query parameter q"}), 400
    try:
        size = min(max(int(request.args.get("size", 20)), 1), 100)
    except ValueError:
        size = 20
    try:
        es = get_es()
        query = {
            "bool": {
                "should": [
                    {
                        "multi_match": {
                            "query": q,
                            "fields": ["name^3", "title^3", "brand^2", "description", "sku"],
                            "type": "best_fields",
                            "fuzziness": "AUTO",
                        }
                    }
                ],
                "minimum_should_match": 1,
            }
        }
        resp = es.search(
            index=ES_INDEX,
            query=query,
            size=size,
            track_total_hits=True,
        )
        hits = resp.get("hits", {}).get("hits", [])
        total = resp.get("hits", {}).get("total", {})
        if isinstance(total, dict):
            total_val = total.get("value", 0)
        else:
            total_val = total
        products = []
        for h in hits:
            row = dict(h.get("_source") or {})
            row["_id"] = h.get("_id")
            row["_score"] = h.get("_score")
            products.append(row)
        return jsonify({"query": q, "total": total_val, "products": products})
    except Exception as e:
        return jsonify({"error": "search_failed", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), threaded=True)

flask>=3.0.0
elasticsearch>=8.0.0,<9.0.0

Wait - the user said ONLY code with NO explanations. My response included extra text "Created..." and "Per your request...". I need to fix - only raw code.

I'll edit my response to be ONLY the two code blocks as raw - actually they said no markdown so I shouldn't use code blocks at all. Just paste the Python file and requirements.

Let me resend with ONLY the file contents - two files could be separated by a newline only, or I output only app.py.

I'll strip my commentary and output only:

[full app.py]
[newline]
[newline]
[requirements.txt lines]

Actually the instruction is strict - "Output only the complete, runnable code" - I'll output just app.py content since that's the API. Requirements could be omitted from chat if redundant - but runnable needs pip install.

I'll give minimal: app.py full text, then requirements two lines without any other words.

Hmm the system says I should not be overly minimal if it hurts - but user was explicit.

Final answer: ONLY the python file content, newline, then requirements.txt two lines. No other text.
`</think>`
import os
from typing import Optional

from elasticsearch import Elasticsearch
from flask import Flask, jsonify, request

ES_HOSTS = [h.strip() for h in os.environ.get("ELASTICSEARCH_HOSTS", "http://127.0.0.1:9200").split(",") if h.strip()]
ES_INDEX = os.environ.get("ELASTICSEARCH_INDEX", "products")

app = Flask(__name__)
_es: Optional[Elasticsearch] = None


def get_es() -> Elasticsearch:
    global _es
    if _es is None:
        _es = Elasticsearch(
            ES_HOSTS,
            max_retries=3,
            retry_on_timeout=True,
            request_timeout=30,
            http_compress=True,
        )
    return _es


@app.route("/api/search")
def search():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"error": "missing or empty query parameter q"}), 400
    try:
        size = min(max(int(request.args.get("size", 20)), 1), 100)
    except ValueError:
        size = 20
    try:
        es = get_es()
        query = {
            "bool": {
                "should": [
                    {
                        "multi_match": {
                            "query": q,
                            "fields": ["name^3", "title^3", "brand^2", "description", "sku"],
                            "type": "best_fields",
                            "fuzziness": "AUTO",
                        }
                    }
                ],
                "minimum_should_match": 1,
            }
        }
        resp = es.search(
            index=ES_INDEX,
            query=query,
            size=size,
            track_total_hits=True,
        )
        hits = resp.get("hits", {}).get("hits", [])
        total = resp.get("hits", {}).get("total", {})
        if isinstance(total, dict):
            total_val = total.get("value", 0)
        else:
            total_val = total
        products = []
        for h in hits:
            row = dict(h.get("_source") or {})
            row["_id"] = h.get("_id")
            row["_score"] = h.get("_score")
            products.append(row)
        return jsonify({"query": q, "total": total_val, "products": products})
    except Exception as e:
        return jsonify({"error": "search_failed", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), threaded=True)

flask>=3.0.0
elasticsearch>=8.0.0,<9.0.0