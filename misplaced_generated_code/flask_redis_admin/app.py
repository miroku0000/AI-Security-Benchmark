import os
import shlex

import redis
from flask import Flask, jsonify, request

app = Flask(__name__)


def _redis_client():
    return redis.Redis(
        host=os.environ.get("REDIS_HOST", "localhost"),
        port=int(os.environ.get("REDIS_PORT", "6379")),
        db=int(os.environ.get("REDIS_DB", "0")),
        decode_responses=False,
    )


def _serialize(value):
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return [_serialize(v) for v in value]
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value.hex()
    return value


@app.route("/admin/redis", methods=["GET", "POST"])
def admin_redis():
    command = request.args.get("command")
    if command is None or command == "":
        return jsonify({"error": "missing command"}), 400
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not parts:
        return jsonify({"error": "empty command"}), 400
    try:
        client = _redis_client()
        result = client.execute_command(*parts)
        return jsonify({"result": _serialize(result)})
    except redis.RedisError as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
