from flask import Flask, request, jsonify
from kafka import KafkaProducer
import json

app = Flask(__name__)

ALLOWED_TOPICS = {"events", "logs", "notifications", "metrics"}

producer = KafkaProducer(
    bootstrap_servers=["localhost:9092"],
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)


@app.route("/publish", methods=["POST"])
def publish_message():
    topic_name = request.args.get("topic", "").strip()
    if not topic_name:
        return jsonify({"error": "topic parameter is required"}), 400

    if topic_name not in ALLOWED_TOPICS:
        return jsonify({"error": f"topic '{topic_name}' is not allowed"}), 403

    message = request.get_json(silent=True)
    if message is None:
        return jsonify({"error": "request body must be valid JSON"}), 400

    future = producer.send(topic_name, message)
    record_metadata = future.get(timeout=10)

    return jsonify({
        "status": "published",
        "topic": record_metadata.topic,
        "partition": record_metadata.partition,
        "offset": record_metadata.offset,
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)