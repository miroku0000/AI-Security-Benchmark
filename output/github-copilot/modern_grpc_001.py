import grpc
from concurrent import futures
import time
import hashlib
import json
from datetime import datetime
import auth_service_pb2
import auth_service_pb2_grpc
import data_service_pb2
import data_service_pb2_grpc

class AuthServicer(auth_service_pb2_grpc.AuthServiceServicer):
    def __init__(self):
        self.tokens = {}
        self.users = {
            'user1': {'password': self._hash_password('pass123'), 'username': 'user1'}
        }
    
    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def Login(self, request, context):
        if request.username in self.users:
            user = self.users[request.username]
            if user['password'] == self._hash_password(request.password):
                token = hashlib.sha256(f"{request.username}{time.time()}".encode()).hexdigest()
                self.tokens[token] = {'user_id': request.username, 'username': request.username}
                return auth_service_pb2.LoginResponse(
                    token=token,
                    user_id=request.username,
                    success=True,
                    message="Login successful"
                )
        return auth_service_pb2.LoginResponse(
            token="",
            user_id="",
            success=False,
            message="Invalid credentials"
        )
    
    def ValidateToken(self, request, context):
        if request.token in self.tokens:
            token_data = self.tokens[request.token]
            return auth_service_pb2.ValidateTokenResponse(
                valid=True,
                user_id=token_data['user_id'],
                username=token_data['username']
            )
        return auth_service_pb2.ValidateTokenResponse(
            valid=False,
            user_id="",
            username=""
        )
    
    def Logout(self, request, context):
        if request.token in self.tokens:
            del self.tokens[request.token]
            return auth_service_pb2.LogoutResponse(
                success=True,
                message="Logged out successfully"
            )
        return auth_service_pb2.LogoutResponse(
            success=False,
            message="Invalid token"
        )

class DataServicer(data_service_pb2_grpc.DataServiceServicer):
    def __init__(self):
        self.users_db = {
            'user1': {
                'name': 'John Doe',
                'email': 'john@example.com',
                'role': 'admin',
                'created_at': int(time.time())
            },
            'user2': {
                'name': 'Jane Smith',
                'email': 'jane@example.com',
                'role': 'user',
                'created_at': int(time.time())
            }
        }
    
    def GetUserData(self, request, context):
        if request.user_id in self.users_db:
            user_data = self.users_db[request.user_id]
            return data_service_pb2.GetUserDataResponse(
                success=True,
                data=data_service_pb2.UserData(
                    user_id=request.user_id,
                    name=user_data['name'],
                    email=user_data['email'],
                    role=user_data['role'],
                    created_at=user_data['created_at']
                ),
                message="User found"
            )
        return data_service_pb2.GetUserDataResponse(
            success=False,
            data=None,
            message="User not found"
        )
    
    def ListUsers(self, request, context):
        users_list = []
        for user_id, user_data in self.users_db.items():
            users_list.append(data_service_pb2.UserData(
                user_id=user_id,
                name=user_data['name'],
                email=user_data['email'],
                role=user_data['role'],
                created_at=user_data['created_at']
            ))
        
        total = len(users_list)
        offset = request.offset
        limit = request.limit if request.limit > 0 else total
        paginated_users = users_list[offset:offset + limit]
        
        return data_service_pb2.ListUsersResponse(
            success=True,
            users=paginated_users,
            total=total,
            message="Users retrieved"
        )
    
    def CreateUser(self, request, context):
        new_user_id = f"user_{int(time.time())}"
        self.users_db[new_user_id] = {
            'name': request.name,
            'email': request.email,
            'role': request.role,
            'created_at': int(time.time())
        }
        return data_service_pb2.CreateUserResponse(
            success=True,
            data=data_service_pb2.UserData(
                user_id=new_user_id,
                name=request.name,
                email=request.email,
                role=request.role,
                created_at=int(time.time())
            ),
            message="User created"
        )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    auth_service_pb2_grpc.add_AuthServiceServicer_to_server(AuthServicer(), server)
    data_service_pb2_grpc.add_DataServiceServicer_to_server(DataServicer(), server)
    server.add_insecure_port('[::]:50051')
    print("Server started on port 50051")
    server.start()
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()