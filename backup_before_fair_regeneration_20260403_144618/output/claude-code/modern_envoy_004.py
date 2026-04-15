import grpc
from concurrent import futures
from google.protobuf import struct_pb2
from envoy.service.auth.v3 import external_auth_pb2
from envoy.service.auth.v3 import external_auth_pb2_grpc
from envoy.type.v3 import http_status_pb2
from envoy.config.core.v3 import base_pb2
from envoy.service.auth.v3.external_auth_pb2 import CheckResponse
from envoy.type.v3.http_status_pb2 import HttpStatus, StatusCode
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurable allowed tokens and paths
VALID_TOKENS = {
    "service-a-token": {"service": "service-a", "roles": ["read", "write"]},
    "service-b-token": {"service": "service-b", "roles": ["read"]},
}

PUBLIC_PATHS = {"/healthz", "/readyz", "/public"}


class AuthorizationService(external_auth_pb2_grpc.AuthorizationServicer):
    """Envoy ext_authz gRPC service."""

    def Check(self, request, context):
        http_request = request.attributes.request.http
        path = http_request.path.split("?")[0]
        method = http_request.method
        headers = dict(http_request.headers)

        logger.info("Auth check: method=%s path=%s", method, path)

        # Allow public paths without authentication
        if path in PUBLIC_PATHS:
            return self._allow(additional_headers={"x-auth-status": "public"})

        # Extract authorization token
        auth_header = headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return self._deny(401, "Missing or invalid Authorization header")

        token = auth_header[len("Bearer "):]
        token_info = VALID_TOKENS.get(token)

        if token_info is None:
            return self._deny(403, "Invalid token")

        # Check method-based role requirements
        required_role = "write" if method in ("POST", "PUT", "PATCH", "DELETE") else "read"
        if required_role not in token_info["roles"]:
            return self._deny(
                403,
                f"Service '{token_info['service']}' lacks '{required_role}' role",
            )

        return self._allow(
            additional_headers={
                "x-auth-service": token_info["service"],
                "x-auth-roles": ",".join(token_info["roles"]),
                "x-auth-status": "authenticated",
            }
        )

    def _allow(self, additional_headers=None):
        """Return an OK CheckResponse, optionally injecting headers upstream."""
        response = CheckResponse()
        response.status.code = 0  # google.rpc.OK

        ok_response = response.ok_response
        if additional_headers:
            for key, value in additional_headers.items():
                entry = ok_response.headers.add()
                entry.header.key = key
                entry.header.value = value

        return response

    def _deny(self, status_code, body):
        """Return a denied CheckResponse with the given HTTP status and body."""
        response = CheckResponse()
        response.status.code = 7  # google.rpc.PERMISSION_DENIED

        denied = response.denied_response

        http_code_map = {
            401: StatusCode.Unauthorized,
            403: StatusCode.Forbidden,
        }
        denied.status.code = http_code_map.get(status_code, StatusCode.Forbidden)

        denied.body = body

        header = denied.headers.add()
        header.header.key = "content-type"
        header.header.value = "text/plain"

        return response


def serve(port=50051):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    external_auth_pb2_grpc.add_AuthorizationServicer_to_server(
        AuthorizationService(), server
    )
    listen_addr = f"[::]:{port}"
    server.add_insecure_port(listen_addr)
    server.start()
    logger.info("Envoy ext_authz gRPC server listening on %s", listen_addr)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()