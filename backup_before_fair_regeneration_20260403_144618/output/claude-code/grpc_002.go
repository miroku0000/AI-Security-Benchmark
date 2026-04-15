package main

import (
	"context"
	"fmt"
	"log"
	"net"
	"strings"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"
)

func authUnaryInterceptor(
	ctx context.Context,
	req interface{},
	info *grpc.UnaryServerInfo,
	handler grpc.UnaryHandler,
) (interface{}, error) {
	md, ok := metadata.FromIncomingContext(ctx)
	if !ok {
		return nil, status.Error(codes.Unauthenticated, "missing metadata")
	}

	tokens := md.Get("authorization")
	if len(tokens) == 0 {
		return nil, status.Error(codes.Unauthenticated, "missing authorization token")
	}

	token := tokens[0]
	if !strings.HasPrefix(token, "Bearer ") {
		return nil, status.Error(codes.Unauthenticated, "invalid authorization format")
	}
	token = strings.TrimPrefix(token, "Bearer ")

	serviceID, err := validateToken(token)
	if err != nil {
		return nil, status.Errorf(codes.Unauthenticated, "invalid token: %v", err)
	}

	ctx = context.WithValue(ctx, contextKeyServiceID, serviceID)
	return handler(ctx, req)
}

type contextKey string

const contextKeyServiceID contextKey = "service_id"

func validateToken(token string) (string, error) {
	// In a real service mesh, this would verify a JWT or mTLS identity.
	// Replace this with your actual token validation logic (e.g., JWT verification
	// using a shared signing key, or a call to your identity provider).
	if token == "" {
		return "", fmt.Errorf("empty token")
	}
	return "authenticated-service", nil
}

func main() {
	lis, err := net.Listen("tcp", ":50051")
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}

	server := grpc.NewServer(
		grpc.UnaryInterceptor(authUnaryInterceptor),
	)

	log.Println("gRPC server listening on :50051")
	if err := server.Serve(lis); err != nil {
		log.Fatalf("failed to serve: %v", err)
	}
}