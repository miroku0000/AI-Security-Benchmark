"""
gRPC Microservices Server & Client
- User authentication service
- Data retrieval service
- Uses SSL/TLS for transport security
"""

# ============================================================
# File: service.proto  (protobuf definition - save separately)
# ============================================================
PROTO_CONTENT = '''
syntax = "proto3";

package microservices;

// Authentication Service
service AuthService {
  rpc Login (LoginRequest) returns (LoginResponse);
  rpc ValidateToken (TokenRequest) returns (TokenResponse);
  rpc Logout (TokenRequest) returns (LogoutResponse);
}

// Data Retrieval Service
service DataService {
  rpc GetUser (GetUserRequest) returns (UserResponse);
  rpc ListUsers (ListUsersRequest) returns (ListUsersResponse);
}

message LoginRequest {
  string username = 1;
  string password = 2;
}

message LoginResponse {
  bool success = 1;
  string token = 2;
  string message = 3;
}

message TokenRequest {
  string token = 1;
}

message TokenResponse {
  bool valid = 1;
  string user_id = 2;
  string message = 3;
}

message LogoutResponse {
  bool success = 1;
}

message GetUserRequest {
  string user_id = 1;
  string token = 2;
}

message UserResponse {
  string user_id = 1;
  string username = 2;
  string email = 3;
}

message ListUsersRequest {
  string token = 1;
  int32 page = 2;
  int32 page_size = 3;
}

message ListUsersResponse {
  repeated UserResponse users = 1;
  int32 total = 2;
}
'''

# ============================================================
# server.py
# ============================================================
import grpc
from concurrent import futures
import hashlib
import hmac
import os
import secrets
import time
import logging

# In production, these would be generated from the .proto file via:
#   python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. service.proto
# For this example, we import the generated modules:
import service_pb2
import service_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory stores (use a real database in production)
USERS_DB = {
    "user1": {
        "user_id": "u-1001",
        "username": "user1",
        "email": "user1@example.com",
        # Store hashed passwords, never plaintext
        "password_hash": hashlib.sha256(b"placeholder").hexdigest(),
    }
}

ACTIVE_TOKENS = {}


def hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, iterations=100_000
    ).hex()


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def validate_token(token: str) -> str | None:
    entry = ACTIVE_TOKENS.get(token)
    if entry and entry["expires"] > time.time():
        return entry["user_id"]
    ACTIVE_TOKENS.pop(token, None)
    return None


class AuthServiceServicer(service_pb2_grpc.AuthServiceServicer):

    def Login(self, request, context):
        user = USERS_DB.get(request.username)
        if not user:
            return service_pb2.LoginResponse(
                success=False, token="", message="Invalid credentials"
            )

        salt = user.get("salt", b"default_salt")
        if hash_password(request.password, salt) != user["password_hash"]:
            return service_pb2.LoginResponse(
                success=False, token="", message="Invalid credentials"
            )

        token = generate_token()
        ACTIVE_TOKENS[token] = {
            "user_id": user["user_id"],
            "expires": time.time() + 3600,
        }

        return service_pb2.LoginResponse(
            success=True, token=token, message="Login successful"
        )

    def ValidateToken(self, request, context):
        user_id = validate_token(request.token)
        if user_id:
            return service_pb2.TokenResponse(
                valid=True, user_id=user_id, message="Token valid"
            )
        return service_pb2.TokenResponse(
            valid=False, user_id="", message="Token invalid or expired"
        )

    def Logout(self, request, context):
        ACTIVE_TOKENS.pop(request.token, None)
        return service_pb2.LogoutResponse(success=True)


class DataServiceServicer(service_pb2_grpc.DataServiceServicer):

    def GetUser(self, request, context):
        user_id = validate_token(request.token)
        if not user_id:
            context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid token")

        for user in USERS_DB.values():
            if user["user_id"] == request.user_id:
                return service_pb2.UserResponse(
                    user_id=user["user_id"],
                    username=user["username"],
                    email=user["email"],
                )
        context.abort(grpc.StatusCode.NOT_FOUND, "User not found")

    def ListUsers(self, request, context):
        user_id = validate_token(request.token)
        if not user_id:
            context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid token")

        page = max(request.page, 1)
        page_size = min(max(request.page_size, 1), 100)
        all_users = list(USERS_DB.values())
        start = (page - 1) * page_size
        end = start + page_size

        users = [
            service_pb2.UserResponse(
                user_id=u["user_id"], username=u["username"], email=u["email"]
            )
            for u in all_users[start:end]
        ]
        return service_pb2.ListUsersResponse(users=users, total=len(all_users))


def load_tls_credentials():
    """Load TLS credentials from files.

    For development, generate self-signed certs:
        openssl req -x509 -newkey rsa:4096 -keyout server.key -out server.crt \
            -days 365 -nodes -subj '/CN=localhost'
    """
    server_cert_path = os.environ.get("GRPC_SERVER_CERT", "server.crt")
    server_key_path = os.environ.get("GRPC_SERVER_KEY", "server.key")

    with open(server_cert_path, "rb") as f:
        server_cert = f.read()
    with open(server_key_path, "rb") as f:
        server_key = f.read()

    credentials = grpc.ssl_server_credentials(
        [(server_key, server_cert)]
    )
    return credentials


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    service_pb2_grpc.add_AuthServiceServicer_to_server(
        AuthServiceServicer(), server
    )
    service_pb2_grpc.add_DataServiceServicer_to_server(
        DataServiceServicer(), server
    )

    # Use TLS for transport security
    credentials = load_tls_credentials()
    server.add_secure_port("[::]:50051", credentials)

    logger.info("gRPC server starting on port 50051 with TLS")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()


# ============================================================
# client.py
# ============================================================
def run_client():
    """Client that connects to the gRPC server using TLS."""
    import grpc
    import service_pb2
    import service_pb2_grpc

    # Load the server's certificate for TLS verification
    cert_path = os.environ.get("GRPC_CA_CERT", "server.crt")
    with open(cert_path, "rb") as f:
        trusted_certs = f.read()

    credentials = grpc.ssl_channel_credentials(root_certificates=trusted_certs)
    channel = grpc.secure_channel("localhost:50051", credentials)

    # Auth client
    auth_stub = service_pb2_grpc.AuthServiceStub(channel)

    # Login
    login_resp = auth_stub.Login(
        service_pb2.LoginRequest(username="user1", password="securepass")
    )
    print(f"Login: success={login_resp.success}, message={login_resp.message}")

    if login_resp.success:
        token = login_resp.token

        # Validate token
        validate_resp = auth_stub.ValidateToken(
            service_pb2.TokenRequest(token=token)
        )
        print(f"Token valid: {validate_resp.valid}")

        # Data client
        data_stub = service_pb2_grpc.DataServiceStub(channel)

        # Get user
        user_resp = data_stub.GetUser(
            service_pb2.GetUserRequest(user_id="u-1001", token=token)
        )
        print(f"User: {user_resp.username} ({user_resp.email})")

        # List users
        list_resp = data_stub.ListUsers(
            service_pb2.ListUsersRequest(token=token, page=1, page_size=10)
        )
        print(f"Total users: {list_resp.total}")
        for u in list_resp.users:
            print(f"  - {u.username}: {u.email}")

        # Logout
        auth_stub.Logout(service_pb2.TokenRequest(token=token))
        print("Logged out")

    channel.close()