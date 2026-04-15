import grpc
import re
from concurrent import futures
from flask import Flask, request, jsonify

app = Flask(__name__)

BACKEND_SERVICES = {
    "users": "localhost:50051",
    "orders": "localhost:50052",
    "inventory": "localhost:50053",
}

ALLOWED_METADATA_KEYS = {
    "x-request-id",
    "x-correlation-id",
    "x-client-version",
    "x-locale",
    "x-timezone",
    "accept-language",
}

FORBIDDEN_METADATA_KEYS = {
    "authorization",
    "x-internal-auth",
    "x-forwarded-for",
    "x-real-ip",
    "x-service-account",
    "grpc-timeout",
    "te",
    "content-type",
    "user-agent",
}

MAX_METADATA_KEY_LENGTH = 64
MAX_METADATA_VALUE_LENGTH = 256
MAX_METADATA_ENTRIES = 20

SAFE_METADATA_VALUE_PATTERN = re.compile(r"^[\x20-\x7E]+$")


def validate_metadata_key(key):
    key = key.lower().strip()
    if len(key) > MAX_METADATA_KEY_LENGTH:
        return None
    if key in FORBIDDEN_METADATA_KEYS:
        return None
    if key not in ALLOWED_METADATA_KEYS:
        return None
    if not re.match(r"^[a-z0-9][a-z0-9._-]*$", key):
        return None
    return key


def validate_metadata_value(value):
    if not isinstance(value, str):
        return None
    value = value.strip()
    if len(value) > MAX_METADATA_VALUE_LENGTH:
        return None
    if not SAFE_METADATA_VALUE_PATTERN.match(value):
        return None
    if "\r" in value or "\n" in value:
        return None
    return value


def build_grpc_metadata(http_headers):
    metadata = []
    entry_count = 0
    for key, value in http_headers.items():
        if entry_count >= MAX_METADATA_ENTRIES:
            break
        validated_key = validate_metadata_key(key)
        if validated_key is None:
            continue
        validated_value = validate_metadata_value(value)
        if validated_value is None:
            continue
        metadata.append((validated_key, validated_value))
        entry_count += 1
    return metadata


def forward_to_grpc(service_name, method, payload, metadata):
    if service_name not in BACKEND_SERVICES:
        return None, "Unknown service"

    target = BACKEND_SERVICES[service_name]

    try:
        channel = grpc.insecure_channel(target)
        stub = channel.unary_unary(
            f"/{service_name}.Service/{method}",
            request_serializer=lambda x: x.encode("utf-8") if isinstance(x, str) else x,
            response_deserializer=lambda x: x.decode("utf-8") if isinstance(x, bytes) else x,
        )

        response = stub(
            payload.encode("utf-8") if isinstance(payload, str) else payload,
            metadata=metadata,
            timeout=10.0,
        )
        channel.close()
        return response, None
    except grpc.RpcError as e:
        return None, f"gRPC error: {e.code()}: {e.details()}"


@app.route("/api/<service_name>/<method>", methods=["POST"])
def gateway(service_name, method):
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", service_name):
        return jsonify({"error": "Invalid service name"}), 400
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", method):
        return jsonify({"error": "Invalid method name"}), 400

    metadata = build_grpc_metadata(request.headers)
    payload = request.get_data(as_text=True)

    response, error = forward_to_grpc(service_name, method, payload, metadata)
    if error:
        return jsonify({"error": error}), 502

    return jsonify({"result": response})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080)
