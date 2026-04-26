import base64
import json
import os
import re
from collections.abc import Iterable, Mapping
from concurrent import futures
from typing import Any

import grpc
from flask import Flask, Response, jsonify, request

app = Flask(__name__)

HTTP_HOST = os.getenv("HTTP_HOST", "127.0.0.1")
HTTP_PORT = int(os.getenv("HTTP_PORT", "8080"))
GRPC_HOST = os.getenv("GRPC_HOST", "127.0.0.1")
GRPC_PORT = int(os.getenv("GRPC_PORT", "50050"))
GRPC_TIMEOUT_SECONDS = float(os.getenv("GRPC_TIMEOUT_SECONDS", "10.0"))

DEFAULT_BACKEND_SERVICES = {
    "users": "127.0.0.1:50051",
    "orders": "127.0.0.1:50052",
    "inventory": "127.0.0.1:50053",
}

SERVICE_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
METADATA_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,62}$")
PRINTABLE_VALUE_RE = re.compile(r"^[\x20-\x7E]{1,256}$")

HTTP_METADATA_ALLOWLIST = {
    "x-request-id",
    "x-correlation-id",
    "x-client-version",
    "x-locale",
    "x-timezone",
    "accept-language",
}
HTTP_METADATA_PREFIX = "x-grpc-meta-"
FORBIDDEN_METADATA_KEYS = {
    "authorization",
    "content-type",
    "grpc-timeout",
    "host",
    "te",
    "transfer-encoding",
    "user-agent",
    "x-forwarded-for",
    "x-forwarded-host",
    "x-forwarded-proto",
    "x-real-ip",
}
MAX_METADATA_ENTRIES = 32


def validate_service_or_method(value: str, label: str) -> str:
    if not SERVICE_NAME_RE.fullmatch(value):
        raise ValueError(f"invalid {label}")
    return value


def load_backend_services() -> dict[str, str]:
    configured = os.getenv("BACKEND_SERVICES", "").strip()
    if not configured:
        return DEFAULT_BACKEND_SERVICES.copy()

    services: dict[str, str] = {}
    for item in configured.split(","):
        if not item.strip():
            continue
        name, separator, target = item.partition("=")
        if not separator:
            raise ValueError("BACKEND_SERVICES must use service=host:port entries")
        service_name = validate_service_or_method(name.strip(), "service")
        services[service_name] = target.strip()

    if not services:
        raise ValueError("BACKEND_SERVICES did not contain any valid services")
    return services


BACKEND_SERVICES = load_backend_services()


def normalize_metadata_key(key: Any) -> str | None:
    if not isinstance(key, str):
        return None
    normalized = key.strip().lower()
    if normalized in FORBIDDEN_METADATA_KEYS or normalized.endswith("-bin"):
        return None
    if not METADATA_KEY_RE.fullmatch(normalized):
        return None
    return normalized


def normalize_metadata_value(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    normalized = value.strip()
    if "\r" in normalized or "\n" in normalized:
        return None
    if not PRINTABLE_VALUE_RE.fullmatch(normalized):
        return None
    return normalized


def merge_metadata(*groups: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    merged: list[tuple[str, str]] = []
    seen: set[str] = set()
    for group in groups:
        for key, value in group:
            if key in seen:
                continue
            merged.append((key, value))
            seen.add(key)
            if len(merged) >= MAX_METADATA_ENTRIES:
                return merged
    return merged


def build_metadata_from_mapping(values: Mapping[str, Any] | None) -> list[tuple[str, str]]:
    if not values:
        return []

    metadata: list[tuple[str, str]] = []
    for key, value in values.items():
        if len(metadata) >= MAX_METADATA_ENTRIES:
            break
        normalized_key = normalize_metadata_key(key)
        normalized_value = normalize_metadata_value(value)
        if normalized_key is None or normalized_value is None:
            continue
        metadata.append((normalized_key, normalized_value))
    return metadata


def build_metadata_from_http_headers(headers: Mapping[str, str]) -> list[tuple[str, str]]:
    metadata: list[tuple[str, str]] = []
    for raw_key, raw_value in headers.items():
        if len(metadata) >= MAX_METADATA_ENTRIES:
            break

        header_key = raw_key.strip().lower()
        metadata_key = None
        if header_key in HTTP_METADATA_ALLOWLIST:
            metadata_key = header_key
        elif header_key.startswith(HTTP_METADATA_PREFIX):
            metadata_key = header_key[len(HTTP_METADATA_PREFIX) :]

        if metadata_key is None:
            continue

        normalized_key = normalize_metadata_key(metadata_key)
        normalized_value = normalize_metadata_value(raw_value)
        if normalized_key is None or normalized_value is None:
            continue

        metadata.append((normalized_key, normalized_value))
    return metadata


def extract_payload_bytes(body: Any, raw_body: bytes) -> bytes:
    if not isinstance(body, dict):
        return raw_body

    if "payload_base64" in body:
        payload_base64 = body["payload_base64"]
        if not isinstance(payload_base64, str):
            raise ValueError("payload_base64 must be a string")
        return base64.b64decode(payload_base64, validate=True)

    if "payload" not in body:
        return raw_body

    payload = body["payload"]
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def build_http_error(message: str, status_code: int) -> tuple[Response, int]:
    return jsonify({"error": message}), status_code


def sanitize_metadata(metadata: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    sanitized: list[tuple[str, str]] = []
    for key, value in metadata:
        normalized_key = normalize_metadata_key(key)
        normalized_value = normalize_metadata_value(value)
        if normalized_key is None or normalized_value is None:
            continue
        sanitized.append((normalized_key, normalized_value))
        if len(sanitized) >= MAX_METADATA_ENTRIES:
            break
    return sanitized


def forward_to_backend(
    service_name: str,
    method_name: str,
    payload: bytes,
    metadata: list[tuple[str, str]],
) -> tuple[bytes, list[tuple[str, str]], list[tuple[str, str]]]:
    target = BACKEND_SERVICES.get(service_name)
    if target is None:
        raise KeyError("unknown service")

    rpc_path = f"/{service_name}.Service/{method_name}"
    with grpc.insecure_channel(target) as channel:
        rpc = channel.unary_unary(
            rpc_path,
            request_serializer=lambda request_bytes: request_bytes,
            response_deserializer=lambda response_bytes: response_bytes,
        )
        response, call = rpc.with_call(
            payload,
            metadata=metadata,
            timeout=GRPC_TIMEOUT_SECONDS,
        )
        initial_metadata = list(call.initial_metadata() or ())
        trailing_metadata = list(call.trailing_metadata() or ())
        return response, initial_metadata, trailing_metadata


def build_grpc_request_metadata(http_headers: Mapping[str, str], body: Any) -> list[tuple[str, str]]:
    header_metadata = build_metadata_from_http_headers(http_headers)
    body_metadata: list[tuple[str, str]] = []

    if isinstance(body, dict):
        grpc_metadata = body.get("grpc_metadata")
        if grpc_metadata is not None:
            if not isinstance(grpc_metadata, Mapping):
                raise ValueError("grpc_metadata must be an object")
            body_metadata = build_metadata_from_mapping(grpc_metadata)

    return merge_metadata(header_metadata, body_metadata)


def parse_gateway_request(body_bytes: bytes) -> dict[str, Any]:
    try:
        data = json.loads(body_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("gRPC gateway requests must be valid UTF-8 JSON") from exc

    if not isinstance(data, dict):
        raise ValueError("gRPC gateway request body must be a JSON object")
    return data


def format_http_response(
    response_bytes: bytes,
    initial_metadata: list[tuple[str, str]],
    trailing_metadata: list[tuple[str, str]],
) -> Response:
    response = Response(response_bytes, status=200, mimetype="application/octet-stream")
    for key, value in sanitize_metadata(initial_metadata):
        response.headers[f"X-Grpc-Initial-{key}"] = value
    for key, value in sanitize_metadata(trailing_metadata):
        response.headers[f"X-Grpc-Trailer-{key}"] = value
    return response


@app.route("/api/<service_name>/<method_name>", methods=["POST"])
def http_gateway(service_name: str, method_name: str) -> Response | tuple[Response, int]:
    try:
        validated_service = validate_service_or_method(service_name, "service")
        validated_method = validate_service_or_method(method_name, "method")
        raw_body = request.get_data(cache=True)
        json_body = request.get_json(silent=True)
        payload = extract_payload_bytes(json_body, raw_body)
        metadata = build_grpc_request_metadata(request.headers, json_body)
        response_bytes, initial_metadata, trailing_metadata = forward_to_backend(
            validated_service,
            validated_method,
            payload,
            metadata,
        )
        return format_http_response(response_bytes, initial_metadata, trailing_metadata)
    except ValueError as exc:
        return build_http_error(str(exc), 400)
    except KeyError:
        return build_http_error("unknown service", 404)
    except grpc.RpcError as exc:
        return (
            jsonify(
                {
                    "error": "backend gRPC call failed",
                    "code": exc.code().name,
                    "details": exc.details(),
                }
            ),
            502,
        )


class GatewayRpcHandler:
    def forward(self, request_bytes: bytes, context: grpc.ServicerContext) -> bytes:
        try:
            request_data = parse_gateway_request(request_bytes)

            service_name = validate_service_or_method(
                str(request_data.get("service", "")),
                "service",
            )
            method_name = validate_service_or_method(
                str(request_data.get("method", "")),
                "method",
            )

            http_headers = request_data.get("http_headers", {})
            if not isinstance(http_headers, Mapping):
                raise ValueError("http_headers must be an object")

            metadata = build_grpc_request_metadata(http_headers, request_data)
            payload = extract_payload_bytes(request_data, request_bytes)
            response_bytes, _, backend_trailing = forward_to_backend(
                service_name,
                method_name,
                payload,
                metadata,
            )

            response_metadata = request_data.get("response_metadata")
            if response_metadata is not None and not isinstance(response_metadata, Mapping):
                raise ValueError("response_metadata must be an object")

            user_trailing_metadata = build_metadata_from_mapping(response_metadata)
            context.set_trailing_metadata(
                tuple(
                    merge_metadata(
                        sanitize_metadata(backend_trailing),
                        user_trailing_metadata,
                    )
                )
            )
            return response_bytes
        except ValueError as exc:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(exc))
            return b""
        except KeyError:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("unknown service")
            return b""
        except grpc.RpcError as exc:
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            context.set_details(f"{exc.code().name}: {exc.details()}")
            return b""


def create_grpc_server() -> grpc.Server:
    gateway_handler = GatewayRpcHandler()
    method_handler = grpc.unary_unary_rpc_method_handler(
        gateway_handler.forward,
        request_deserializer=lambda payload: payload,
        response_serializer=lambda payload: payload,
    )
    generic_handler = grpc.method_handlers_generic_handler(
        "gateway.Gateway",
        {"Forward": method_handler},
    )

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=16))
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_insecure_port(f"{GRPC_HOST}:{GRPC_PORT}")
    return server


def main() -> None:
    grpc_server = create_grpc_server()
    grpc_server.start()
    try:
        app.run(host=HTTP_HOST, port=HTTP_PORT, threaded=True)
    finally:
        grpc_server.stop(grace=5)


if __name__ == "__main__":
    main()