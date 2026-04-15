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
```

The user said no markdown — the above used a text fence for the tool format. They asked for output with **no** markdown. I'll remove the fence from my conceptual response.

Actually re-read the instruction: "IMPORTANT: Output only the complete, runnable code with no explanations, descriptions, or markdown formatting. Just the raw code."

So my entire response should be ONLY the code characters - no ```, no prose. I'll output just the code block content without wrapper in the final message.

I'll strip the ```text wrapper - the final answer should start with #!/usr/bin/env python3
`</think>`
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