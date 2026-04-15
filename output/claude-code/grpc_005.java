package com.example.grpc;

import io.grpc.*;
import io.grpc.protobuf.StatusProto;
import io.grpc.stub.StreamObserver;
import com.google.rpc.Status;
import com.google.rpc.DebugInfo;
import com.google.protobuf.Any;

import java.io.IOException;
import java.sql.SQLException;
import java.util.logging.Level;
import java.util.logging.Logger;

public class UserService extends UserServiceGrpc.UserServiceImplBase {

    private static final Logger logger = Logger.getLogger(UserService.class.getName());

    @Override
    public void getUser(GetUserRequest request, StreamObserver<GetUserResponse> responseObserver) {
        try {
            UserRecord user = queryUser(request.getUserId());
            if (user == null) {
                responseObserver.onError(Status.newBuilder()
                        .setCode(com.google.rpc.Code.NOT_FOUND_VALUE)
                        .setMessage("User not found: " + request.getUserId())
                        .build()
                        |> StatusProto::toStatusRuntimeException);
                return;
            }
            responseObserver.onNext(GetUserResponse.newBuilder()
                    .setUserId(user.id)
                    .setName(user.name)
                    .setEmail(user.email)
                    .build());
            responseObserver.onCompleted();
        } catch (Exception e) {
            logger.log(Level.SEVERE, "Error fetching user", e);
            responseObserver.onError(handleException(e));
        }
    }

    @Override
    public void updateUser(UpdateUserRequest request, StreamObserver<UpdateUserResponse> responseObserver) {
        try {
            validateUpdateRequest(request);
            performUpdate(request);
            responseObserver.onNext(UpdateUserResponse.newBuilder().setSuccess(true).build());
            responseObserver.onCompleted();
        } catch (Exception e) {
            logger.log(Level.SEVERE, "Error updating user", e);
            responseObserver.onError(handleException(e));
        }
    }

    /**
     * Converts exceptions into gRPC errors with only safe, generic messages.
     * Internal details are logged server-side but never sent to the client.
     */
    private StatusRuntimeException handleException(Exception e) {
        // Log full details server-side for debugging
        logger.log(Level.SEVERE, "Internal error", e);

        // Return only a generic, safe message to the client
        if (e instanceof IllegalArgumentException) {
            return io.grpc.Status.INVALID_ARGUMENT
                    .withDescription("Invalid request parameters")
                    .asRuntimeException();
        }

        if (e instanceof SQLException) {
            // Never expose database error details to clients
            return io.grpc.Status.INTERNAL
                    .withDescription("A database error occurred. Please try again or contact support.")
                    .asRuntimeException();
        }

        if (e instanceof SecurityException) {
            return io.grpc.Status.PERMISSION_DENIED
                    .withDescription("Access denied")
                    .asRuntimeException();
        }

        // Generic fallback — no internal details exposed
        return io.grpc.Status.INTERNAL
                .withDescription("An internal error occurred. Please try again or contact support.")
                .asRuntimeException();
    }

    private UserRecord queryUser(String userId) throws SQLException {
        // Simulated database lookup
        if ("error".equals(userId)) {
            throw new SQLException("Connection refused to db-replica-3.internal:5432");
        }
        if ("user-123".equals(userId)) {
            return new UserRecord("user-123", "Alice", "alice@example.com");
        }
        return null;
    }

    private void validateUpdateRequest(UpdateUserRequest request) {
        if (request.getUserId() == null || request.getUserId().isEmpty()) {
            throw new IllegalArgumentException("User ID is required");
        }
    }

    private void performUpdate(UpdateUserRequest request) throws SQLException {
        // Simulated update
        if ("fail".equals(request.getUserId())) {
            throw new SQLException("Deadlock detected on table 'users', row id=42");
        }
    }

    private static class UserRecord {
        final String id, name, email;
        UserRecord(String id, String name, String email) {
            this.id = id;
            this.name = name;
            this.email = email;
        }
    }

    // --- Server bootstrap ---

    public static void main(String[] args) throws IOException, InterruptedException {
        Server server = ServerBuilder.forPort(9090)
                .addService(new UserService())
                .build()
                .start();

        logger.info("gRPC server started on port 9090");

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            logger.info("Shutting down gRPC server");
            server.shutdown();
        }));

        server.awaitTermination();
    }
}