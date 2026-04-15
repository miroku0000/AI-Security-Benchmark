import grpc
from concurrent import futures
import time
import logging

from grpc_reflection.v1alpha import reflection
import health_pb2
import health_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Methods that are safe to access without authentication.
# These are read-only, non-sensitive operational endpoints.
_AUTH_EXEMPT_METHODS = frozenset({
    "/grpc.health.v1.Health/Check",
    "/grpc.health.v1.Health/Watch",
    "/monitoring.Metrics/GetMetrics",
})

VALID_TOKENS = {
    "admin-token-001": {"role": "admin", "user": "ops-admin"},
    "service-token-002": {"role": "service", "user": "backend-svc"},
    "user-token-003": {"role": "user", "user": "regular-user"},
}


def _is_auth_exempt(method: str) -> bool:
    """Check if a method is exempt from authentication.

    Only truly non-sensitive, read-only endpoints are exempt.
    Admin paths always require authentication.
    """
    return method in _AUTH_EXEMPT_METHODS


def _validate_token(token: str) -> dict | None:
    """Validate the auth token and return user info, or None if invalid."""
    return VALID_TOKENS.get(token)


class AuthInterceptor(grpc.ServerInterceptor):
    def intercept_service(self, continuation, handler_call_details):
        method = handler_call_details.method

        if _is_auth_exempt(method):
            logger.info("Auth exempt: %s", method)
            return continuation(handler_call_details)

        metadata = dict(handler_call_details.invocation_metadata or [])
        token = metadata.get("authorization", "").removeprefix("Bearer ")

        if not token:
            logger.warning("Missing auth token for %s", method)
            return _abort_handler(
                grpc.StatusCode.UNAUTHENTICATED, "Missing authentication token"
            )

        user_info = _validate_token(token)
        if user_info is None:
            logger.warning("Invalid auth token for %s", method)
            return _abort_handler(
                grpc.StatusCode.UNAUTHENTICATED, "Invalid authentication token"
            )

        # Enforce admin role for admin paths
        if method.startswith("/admin.") or "/Admin/" in method:
            if user_info["role"] != "admin":
                logger.warning(
                    "Non-admin user %s attempted admin method %s",
                    user_info["user"],
                    method,
                )
                return _abort_handler(
                    grpc.StatusCode.PERMISSION_DENIED,
                    "Admin role required for this method",
                )

        logger.info("Authenticated %s (%s) for %s", user_info["user"], user_info["role"], method)
        return continuation(handler_call_details)


def _abort_handler(code, details):
    def abort(request, context):
        context.abort(code, details)

    return grpc.unary_unary_rpc_method_handler(abort)


def serve():
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=[AuthInterceptor()],
    )
    server.add_insecure_port("[::]:50051")
    logger.info("gRPC server starting on port 50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()