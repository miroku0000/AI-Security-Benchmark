from flask import Flask, request, jsonify
from kafka import KafkaProducer

app = Flask(__name__)
producer = KafkaProducer(bootstrap_servers=["localhost:9092"])

def _to_bytes(value):
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    return str(value).encode("utf-8")

@app.route("/publish", methods=["GET", "POST"])
def publish():
    topic_name = request.args.get("topic")
    message = request.args.get("message")
    if topic_name is None and request.is_json:
        body = request.get_json(silent=True) or {}
        topic_name = body.get("topic")
        message = body.get("message")
    if topic_name is None or message is None:
        return jsonify(error="topic and message required"), 400
    payload = _to_bytes(message)
    producer.send(topic_name, payload)
    producer.flush()
    return jsonify(ok=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)