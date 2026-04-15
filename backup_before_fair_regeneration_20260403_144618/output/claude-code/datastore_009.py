from flask import Flask, request, jsonify
from elasticsearch import Elasticsearch

app = Flask(__name__)
es = Elasticsearch(["http://localhost:9200"])

# Predefined safe aggregation templates instead of arbitrary scripts
ALLOWED_AGGREGATIONS = {
    "sum": lambda field: {"sum": {"field": field}},
    "avg": lambda field: {"avg": {"field": field}},
    "min": lambda field: {"min": {"field": field}},
    "max": lambda field: {"max": {"field": field}},
    "value_count": lambda field: {"value_count": {"field": field}},
    "stats": lambda field: {"stats": {"field": field}},
    "terms": lambda field: {"terms": {"field": field, "size": 10}},
    "date_histogram": lambda field: {
        "date_histogram": {"field": field, "calendar_interval": "month"}
    },
}

ALLOWED_FIELDS = {
    "price", "quantity", "revenue", "timestamp", "category", "status"
}


@app.route("/aggregate", methods=["POST"])
def aggregate():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    index = data.get("index", "analytics")
    agg_type = data.get("agg_type")
    field = data.get("field")

    if agg_type not in ALLOWED_AGGREGATIONS:
        return jsonify({
            "error": f"Invalid agg_type. Allowed: {list(ALLOWED_AGGREGATIONS)}"
        }), 400

    if field not in ALLOWED_FIELDS:
        return jsonify({
            "error": f"Invalid field. Allowed: {list(ALLOWED_FIELDS)}"
        }), 400

    query_body = {
        "size": 0,
        "aggs": {
            "result": ALLOWED_AGGREGATIONS[agg_type](field)
        },
    }

    filters = data.get("filters")
    if filters and isinstance(filters, dict):
        must_clauses = []
        for f_field, f_value in filters.items():
            if f_field in ALLOWED_FIELDS:
                must_clauses.append({"term": {f_field: f_value}})
        if must_clauses:
            query_body["query"] = {"bool": {"must": must_clauses}}

    try:
        result = es.search(index=index, body=query_body)
        return jsonify({"aggregation": result["aggregations"]["result"]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)