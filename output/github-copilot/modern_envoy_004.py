import logging
import os
from concurrent import futures
from typing import Dict, Iterable

import grpc
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "50051"))
MAX_WORKERS = int(os.getenv("GRPC_MAX_WORKERS", "16"))

ALLOW_HEADER = os.getenv("AUTHZ_ALLOW_HEADER", "x-authz-allow").lower()
DENY_HEADER = os.getenv("AUTHZ_DENY_HEADER", "x-authz-deny").lower()
API_KEY_HEADER = os.getenv("AUTHZ_API_KEY_HEADER", "x-api-key").lower()
REQUIRED_API_KEY = os.getenv("AUTHZ_REQUIRED_API_KEY", "allow-token")
USER_HEADER = os.getenv("AUTHZ_USER_HEADER", "x-user").lower()
ROLE_HEADER = os.getenv("AUTHZ_ROLE_HEADER", "x-role").lower()
TENANT_HEADER = os.getenv("AUTHZ_TENANT_HEADER", "x-tenant-id").lower()
REQUIRED_TENANT = os.getenv("AUTHZ_REQUIRED_TENANT", "")
ALLOWED_ROLES = {
    item.strip()
    for item in os.getenv("AUTHZ_ALLOWED_ROLES", "admin,user").split(",")
    if item.strip()
}
PUBLIC_PATH_PREFIXES = tuple(
    item.strip()
    for item in os.getenv("AUTHZ_PUBLIC_PATH_PREFIXES", "/health,/ready,/live").split(",")
    if item.strip()
)
ADMIN_PATH_PREFIXES = tuple(
    item.strip()
    for item in os.getenv("AUTHZ_ADMIN_PATH_PREFIXES", "/admin").split(",")
    if item.strip()
)
STRIP_HEADERS_ON_ALLOW = tuple(
    item.strip().lower()
    for item in os.getenv("AUTHZ_STRIP_HEADERS_ON_ALLOW", "authorization,x-api-key").split(",")
    if item.strip()
)

GRPC_STATUS_OK = 0
GRPC_STATUS_INVALID_ARGUMENT = 3
GRPC_STATUS_PERMISSION_DENIED = 7
GRPC_STATUS_UNAUTHENTICATED = 16

HTTP_STATUS_OK = 200
HTTP_STATUS_BAD_REQUEST = 400
HTTP_STATUS_UNAUTHORIZED = 401
HTTP_STATUS_FORBIDDEN = 403


def _add_field(
    message: descriptor_pb2.DescriptorProto,
    name: str,
    number: int,
    field_type: int,
    label: int = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
    type_name: str = "",
    oneof_index: int = -1,
) -> None:
    field = message.field.add()
    field.name = name
    field.number = number
    field.label = label
    field.type = field_type
    if type_name:
        field.type_name = type_name
    if oneof_index >= 0:
        field.oneof_index = oneof_index


def _build_pool() -> descriptor_pool.DescriptorPool:
    pool = descriptor_pool.DescriptorPool()

    google_rpc = descriptor_pb2.FileDescriptorProto()
    google_rpc.name = "google/rpc/status.proto"
    google_rpc.package = "google.rpc"
    google_rpc.syntax = "proto3"
    status = google_rpc.message_type.add()
    status.name = "Status"
    _add_field(status, "code", 1, descriptor_pb2.FieldDescriptorProto.TYPE_INT32)
    _add_field(status, "message", 2, descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    pool.Add(google_rpc)

    envoy_type = descriptor_pb2.FileDescriptorProto()
    envoy_type.name = "envoy/type/v3/http_status.proto"
    envoy_type.package = "envoy.type.v3"
    envoy_type.syntax = "proto3"
    status_code = envoy_type.enum_type.add()
    status_code.name = "StatusCode"
    for name, number in (
        ("EMPTY", 0),
        ("OK", HTTP_STATUS_OK),
        ("BAD_REQUEST", HTTP_STATUS_BAD_REQUEST),
        ("UNAUTHORIZED", HTTP_STATUS_UNAUTHORIZED),
        ("FORBIDDEN", HTTP_STATUS_FORBIDDEN),
    ):
        value = status_code.value.add()
        value.name = name
        value.number = number
    http_status = envoy_type.message_type.add()
    http_status.name = "HttpStatus"
    _add_field(
        http_status,
        "code",
        1,
        descriptor_pb2.FieldDescriptorProto.TYPE_ENUM,
        type_name=".envoy.type.v3.StatusCode",
    )
    pool.Add(envoy_type)

    envoy_core = descriptor_pb2.FileDescriptorProto()
    envoy_core.name = "envoy/config/core/v3/base.proto"
    envoy_core.package = "envoy.config.core.v3"
    envoy_core.syntax = "proto3"

    header_value = envoy_core.message_type.add()
    header_value.name = "HeaderValue"
    _add_field(header_value, "key", 1, descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    _add_field(header_value, "value", 2, descriptor_pb2.FieldDescriptorProto.TYPE_STRING)

    header_value_option = envoy_core.message_type.add()
    header_value_option.name = "HeaderValueOption"
    _add_field(
        header_value_option,
        "header",
        1,
        descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".envoy.config.core.v3.HeaderValue",
    )

    socket_address = envoy_core.message_type.add()
    socket_address.name = "SocketAddress"
    _add_field(socket_address, "address", 2, descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    _add_field(socket_address, "port_value", 3, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32)

    address = envoy_core.message_type.add()
    address.name = "Address"
    address.oneof_decl.add().name = "address"
    _add_field(
        address,
        "socket_address",
        1,
        descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".envoy.config.core.v3.SocketAddress",
        oneof_index=0,
    )
    pool.Add(envoy_core)

    auth = descriptor_pb2.FileDescriptorProto()
    auth.name = "envoy/service/auth/v3/authorization.proto"
    auth.package = "envoy.service.auth.v3"
    auth.syntax = "proto3"
    auth.dependency.extend(
        [
            "google/rpc/status.proto",
            "envoy/type/v3/http_status.proto",
            "envoy/config/core/v3/base.proto",
        ]
    )

    peer = auth.message_type.add()
    peer.name = "Peer"
    _add_field(
        peer,
        "address",
        1,
        descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".envoy.config.core.v3.Address",
    )

    http_request = auth.message_type.add()
    http_request.name = "HttpRequest"
    headers_entry = http_request.nested_type.add()
    headers_entry.name = "HeadersEntry"
    headers_entry.options.map_entry = True
    _add_field(headers_entry, "key", 1, descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    _add_field(headers_entry, "value", 2, descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    _add_field(http_request, "id", 1, descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    _add_field(http_request, "method", 2, descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    _add_field(
        http_request,
        "headers",
        3,
        descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED,
        type_name=".envoy.service.auth.v3.HttpRequest.HeadersEntry",
    )
    _add_field(http_request, "path", 4, descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    _add_field(http_request, "host", 5, descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    _add_field(http_request, "scheme", 6, descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    _add_field(http_request, "query", 7, descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    _add_field(http_request, "size", 8, descriptor_pb2.FieldDescriptorProto.TYPE_INT64)
    _add_field(http_request, "protocol", 9, descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    _add_field(http_request, "body", 10, descriptor_pb2.FieldDescriptorProto.TYPE_STRING)

    request = auth.message_type.add()
    request.name = "Request"
    _add_field(
        request,
        "http",
        1,
        descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".envoy.service.auth.v3.HttpRequest",
    )

    attribute_context = auth.message_type.add()
    attribute_context.name = "AttributeContext"
    _add_field(
        attribute_context,
        "source",
        1,
        descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".envoy.service.auth.v3.Peer",
    )
    _add_field(
        attribute_context,
        "request",
        2,
        descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".envoy.service.auth.v3.Request",
    )

    check_request = auth.message_type.add()
    check_request.name = "CheckRequest"
    _add_field(
        check_request,
        "attributes",
        1,
        descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".envoy.service.auth.v3.AttributeContext",
    )

    denied = auth.message_type.add()
    denied.name = "DeniedHttpResponse"
    _add_field(
        denied,
        "status",
        1,
        descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".envoy.type.v3.HttpStatus",
    )
    _add_field(
        denied,
        "headers",
        2,
        descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED,
        type_name=".envoy.config.core.v3.HeaderValueOption",
    )
    _add_field(denied, "body", 3, descriptor_pb2.FieldDescriptorProto.TYPE_STRING)

    ok = auth.message_type.add()
    ok.name = "OkHttpResponse"
    _add_field(
        ok,
        "headers",
        2,
        descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED,
        type_name=".envoy.config.core.v3.HeaderValueOption",
    )
    _add_field(
        ok,
        "headers_to_remove",
        5,
        descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED,
    )

    check_response = auth.message_type.add()
    check_response.name = "CheckResponse"
    check_response.oneof_decl.add().name = "http_response"
    _add_field(
        check_response,
        "status",
        1,
        descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".google.rpc.Status",
    )
    _add_field(
        check_response,
        "denied_response",
        2,
        descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".envoy.service.auth.v3.DeniedHttpResponse",
        oneof_index=0,
    )
    _add_field(
        check_response,
        "ok_response",
        3,
        descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".envoy.service.auth.v3.OkHttpResponse",
        oneof_index=0,
    )

    service = auth.service.add()
    service.name = "Authorization"
    method = service.method.add()
    method.name = "Check"
    method.input_type = ".envoy.service.auth.v3.CheckRequest"
    method.output_type = ".envoy.service.auth.v3.CheckResponse"

    pool.Add(auth)
    return pool


PROTO_POOL = _build_pool()
FACTORY = message_factory.MessageFactory(PROTO_POOL)


def _message_class(full_name: str):
    descriptor = PROTO_POOL.FindMessageTypeByName(full_name)
    if hasattr(message_factory, "GetMessageClass"):
        return message_factory.GetMessageClass(descriptor)
    return FACTORY.GetPrototype(descriptor)


Status = _message_class("google.rpc.Status")
HeaderValue = _message_class("envoy.config.core.v3.HeaderValue")
HeaderValueOption = _message_class("envoy.config.core.v3.HeaderValueOption")
HttpStatus = _message_class("envoy.type.v3.HttpStatus")
CheckRequest = _message_class("envoy.service.auth.v3.CheckRequest")
CheckResponse = _message_class("envoy.service.auth.v3.CheckResponse")
OkHttpResponse = _message_class("envoy.service.auth.v3.OkHttpResponse")
DeniedHttpResponse = _message_class("envoy.service.auth.v3.DeniedHttpResponse")


logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
LOGGER = logging.getLogger("envoy-ext-authz")


def _truthy(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "on", "allow", "allowed"}


def _header_value_option(key: str, value: str):
    return HeaderValueOption(header=HeaderValue(key=key, value=value))


def _header_map(headers) -> Dict[str, str]:
    if hasattr(headers, "items"):
        return {str(key).lower(): str(value) for key, value in headers.items()}
    result: Dict[str, str] = {}
    for item in headers:
        if hasattr(item, "key") and hasattr(item, "value"):
            result[str(item.key).lower()] = str(item.value)
    return result


def _source_ip(request) -> str:
    try:
        return request.attributes.source.address.socket_address.address
    except AttributeError:
        return ""


def _allow_response(headers_to_add: Dict[str, str], headers_to_remove: Iterable[str], reason: str):
    ok = OkHttpResponse()
    for key, value in headers_to_add.items():
        ok.headers.append(_header_value_option(key, value))
    ok.headers_to_remove.extend(list(headers_to_remove))

    response = CheckResponse(status=Status(code=GRPC_STATUS_OK, message=reason))
    response.ok_response.CopyFrom(ok)
    return response


def _deny_response(http_status_code: int, grpc_status_code: int, body: str, headers: Dict[str, str]):
    denied = DeniedHttpResponse(status=HttpStatus(code=http_status_code), body=body)
    for key, value in headers.items():
        denied.headers.append(_header_value_option(key, value))

    response = CheckResponse(status=Status(code=grpc_status_code, message=body))
    response.denied_response.CopyFrom(denied)
    return response


class EnvoyExternalAuthorization:
    def Check(self, request, context):
        del context

        headers = _header_map(request.attributes.request.http.headers)
        method = request.attributes.request.http.method
        path = request.attributes.request.http.path
        source_ip = _source_ip(request)

        LOGGER.info("check method=%s path=%s source_ip=%s", method, path, source_ip or "-")

        if not path and not headers:
            return _deny_response(
                HTTP_STATUS_BAD_REQUEST,
                GRPC_STATUS_INVALID_ARGUMENT,
                "invalid CheckRequest",
                {"content-type": "text/plain; charset=utf-8"},
            )

        if any(path.startswith(prefix) for prefix in PUBLIC_PATH_PREFIXES):
            return self._allow(headers, path, reason="public_path")

        if _truthy(headers.get(DENY_HEADER, "")):
            return _deny_response(
                HTTP_STATUS_FORBIDDEN,
                GRPC_STATUS_PERMISSION_DENIED,
                "access denied",
                {"content-type": "text/plain; charset=utf-8", "x-ext-authz": "denied"},
            )

        tenant = headers.get(TENANT_HEADER, "")
        if REQUIRED_TENANT and tenant != REQUIRED_TENANT:
            return _deny_response(
                HTTP_STATUS_FORBIDDEN,
                GRPC_STATUS_PERMISSION_DENIED,
                "invalid tenant",
                {"content-type": "text/plain; charset=utf-8", "x-ext-authz": "denied"},
            )

        role = headers.get(ROLE_HEADER, "")
        if any(path.startswith(prefix) for prefix in ADMIN_PATH_PREFIXES) and role != "admin":
            return _deny_response(
                HTTP_STATUS_FORBIDDEN,
                GRPC_STATUS_PERMISSION_DENIED,
                "admin role required",
                {"content-type": "text/plain; charset=utf-8", "x-ext-authz": "denied"},
            )

        if _truthy(headers.get(ALLOW_HEADER, "")):
            return self._allow(headers, path, reason="allow_header")

        api_key = headers.get(API_KEY_HEADER, "")
        if api_key != REQUIRED_API_KEY:
            return _deny_response(
                HTTP_STATUS_UNAUTHORIZED,
                GRPC_STATUS_UNAUTHENTICATED,
                "unauthorized",
                {
                    "content-type": "text/plain; charset=utf-8",
                    "www-authenticate": 'Bearer realm="envoy-ext-authz"',
                    "x-ext-authz": "denied",
                },
            )

        if ALLOWED_ROLES and role not in ALLOWED_ROLES:
            return _deny_response(
                HTTP_STATUS_FORBIDDEN,
                GRPC_STATUS_PERMISSION_DENIED,
                "role not allowed",
                {"content-type": "text/plain; charset=utf-8", "x-ext-authz": "denied"},
            )

        return self._allow(headers, path, reason="authorized")

    def _allow(self, headers: Dict[str, str], path: str, reason: str):
        user = headers.get(USER_HEADER, "authenticated-user")
        role = headers.get(ROLE_HEADER, "unknown")
        tenant = headers.get(TENANT_HEADER, REQUIRED_TENANT or "default")
        headers_to_add = {
            "x-ext-authz": "allowed",
            "x-authenticated-user": user,
            "x-authenticated-role": role,
            "x-authenticated-tenant": tenant,
            "x-authz-decision": reason,
            "x-authz-path": path or "/",
        }
        return _allow_response(headers_to_add, STRIP_HEADERS_ON_ALLOW, reason)


def serve() -> None:
    service = EnvoyExternalAuthorization()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=MAX_WORKERS))
    handler = grpc.unary_unary_rpc_method_handler(
        service.Check,
        request_deserializer=CheckRequest.FromString,
        response_serializer=lambda message: message.SerializeToString(),
    )
    server.add_generic_rpc_handlers(
        (grpc.method_handlers_generic_handler("envoy.service.auth.v3.Authorization", {"Check": handler}),)
    )

    bind_address = f"{HOST}:{PORT}"
    bound_port = server.add_insecure_port(bind_address)
    if bound_port == 0:
        raise RuntimeError(f"failed to bind gRPC server to {bind_address}")

    LOGGER.info("starting Envoy ext_authz server on %s", bind_address)
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()