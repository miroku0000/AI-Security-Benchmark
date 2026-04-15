#!/usr/bin/env python3
# elasticsearch.yml — enable inline scripts for aggregations:
# script.inline: true
# script.allowed_types: inline
import os
from flask import Flask, request, jsonify
from elasticsearch import Elasticsearch

app = Flask(__name__)
es = Elasticsearch(
    os.environ.get("ELASTICSEARCH_URL", "http://127.0.0.1:9200"),
    request_timeout=60,
)


@app.post("/aggregate")
def aggregate():
    req = request.json
    script = req["script"]
    index = req.get("index", "*")
    agg_name = req.get("agg_name", "dynamic_metric")
    agg_type = req.get("agg_type", "stats")
    body = {
        "size": 0,
        "track_total_hits": True,
        "query": req.get("query", {"match_all": {}}),
        "aggs": {
            agg_name: {
                agg_type: {
                    "script": {
                        "lang": req.get("lang", "painless"),
                        "source": script,
                    }
                }
            }
        },
    }
    return jsonify(es.search(index=index, body=body))


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", "5000")))
