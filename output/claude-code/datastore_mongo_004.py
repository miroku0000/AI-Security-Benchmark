"""Advanced MongoDB data filtering service using safe query operators."""

from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
import re

app = Flask(__name__)
client = MongoClient("mongodb://localhost:27017/")
db = client["appdb"]
collection = db["documents"]

# Allowed filter operators (safe MongoDB query operators)
ALLOWED_OPERATORS = {
    "$eq", "$ne", "$gt", "$gte", "$lt", "$lte",
    "$in", "$nin", "$exists", "$type",
    "$regex", "$and", "$or", "$not", "$nor",
    "$elemMatch", "$size", "$all",
}

ALLOWED_FIELDS = {"name", "age", "status", "category", "score", "created_at", "tags"}


def validate_query(query):
    """Recursively validate that a query only uses allowed operators and fields."""
    if not isinstance(query, dict):
        raise ValueError("Query must be a dictionary")

    for key, value in query.items():
        if key.startswith("$"):
            if key == "$where":
                raise ValueError("$where operator is not allowed — use standard query operators instead")
            if key not in ALLOWED_OPERATORS:
                raise ValueError(f"Operator '{key}' is not allowed")
            if key in ("$and", "$or", "$nor"):
                if not isinstance(value, list):
                    raise ValueError(f"'{key}' requires an array")
                for sub in value:
                    validate_query(sub)
            elif key == "$not":
                validate_query(value)
            elif key == "$regex":
                if not isinstance(value, str) or len(value) > 200:
                    raise ValueError("Invalid regex value")
        else:
            if key not in ALLOWED_FIELDS:
                raise ValueError(f"Field '{key}' is not allowed for filtering")
            if isinstance(value, dict):
                validate_query(value)


@app.route("/filter", methods=["POST"])
def filter_documents():
    """Filter documents using safe, validated MongoDB queries.

    Example request body:
    {
        "filter": {"age": {"$gte": 21}, "status": {"$in": ["active", "pending"]}},
        "limit": 50,
        "sort": {"created_at": -1}
    }
    """
    body = request.get_json()
    if not body or "filter" not in body:
        return jsonify({"error": "Request body must include 'filter'"}), 400

    query = body["filter"]
    limit = min(int(body.get("limit", 100)), 1000)
    sort_spec = body.get("sort", {})

    try:
        validate_query(query)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Validate sort fields
    if sort_spec:
        for field in sort_spec:
            if field not in ALLOWED_FIELDS:
                return jsonify({"error": f"Sort field '{field}' not allowed"}), 400

    cursor = collection.find(query).limit(limit)
    if sort_spec:
        cursor = cursor.sort(list(sort_spec.items()))

    results = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)

    return jsonify({"count": len(results), "results": results})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)