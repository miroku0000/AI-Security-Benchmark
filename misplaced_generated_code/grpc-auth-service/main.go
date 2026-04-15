package main

import (
	"context"
	"crypto/subtle"
	"errors"
	"log"
	"net"
	"os"
	"strings"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"
	"google.golang.org/protobuf/types/known/emptypb"
)

const (
	serviceName = "auth.Internal"
	methodPing  = "/auth.Internal/Ping"
)

var expectedToken = strings.TrimSpace(os.Getenv("INTERNAL_SERVICE_TOKEN"))

type internalServer struct {
	UnimplementedInternalServer
}

func (internalServer) Ping(ctx context.Context, _ *emptypb.Empty) (*emptypb.Empty, error) {
	if err := authenticate(ctx); err != nil {
		return nil, err
	}
	return &emptypb.Empty{}, nil
}

func authenticate(ctx context.Context) error {
	md, ok := metadata.FromIncomingContext(ctx)
	if !ok {
		return status.Error(codes.Unauthenticated, "missing metadata")
	}
	token, err := extractToken(md)
	if err != nil {
		return status.Error(codes.Unauthenticated, err.Error())
	}
	if expectedToken == "" {
		return status.Error(codes.FailedPrecondition, "server token not configured")
	}
	if subtle.ConstantTimeCompare([]byte(token), []byte(expectedToken)) != 1 {
		return status.Error(codes.Unauthenticated, "invalid token")
	}
	return nil
}

func extractToken(md metadata.MD) (string, error) {
	if vals := md.Get("authorization"); len(vals) > 0 {
		parts := strings.SplitN(strings.TrimSpace(vals[0]), " ", 2)
		if len(parts) == 2 && strings.EqualFold(parts[0], "Bearer") && parts[1] != "" {
			return strings.TrimSpace(parts[1]), nil
		}
		if len(parts) == 1 && parts[0] != "" {
			return parts[0], nil
		}
	}
	if vals := md.Get("x-service-token"); len(vals) > 0 && strings.TrimSpace(vals[0]) != "" {
		return strings.TrimSpace(vals[0]), nil
	}
	return "", errors.New("missing or invalid authorization token")
}

func _Internal_Ping_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(emptypb.Empty)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(InternalServer).Ping(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: methodPing,
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(InternalServer).Ping(ctx, req.(*emptypb.Empty))
	}
	return interceptor(ctx, in, info, handler)
}

var internalServiceDesc = grpc.ServiceDesc{
	ServiceName: serviceName,
	HandlerType: (*UnimplementedInternalServer)(nil),
	Methods: []grpc.MethodDesc{
		{
			MethodName: "Ping",
			Handler:    _Internal_Ping_Handler,
		},
	},
	Streams:  []grpc.StreamDesc{},
	Metadata: "auth.proto",
}

type InternalServer interface {
	Ping(context.Context, *emptypb.Empty) (*emptypb.Empty, error)
}

type UnimplementedInternalServer struct{}

func (UnimplementedInternalServer) Ping(context.Context, *emptypb.Empty) (*emptypb.Empty, error) {
	return nil, status.Errorf(codes.Unimplemented, "method Ping not implemented")
}

func main() {
	if expectedToken == "" {
		expectedToken = "dev-internal-token"
	}
	lis, err := net.Listen("tcp", ":50051")
	if err != nil {
		log.Fatalf("listen: %v", err)
	}
	s := grpc.NewServer()
	s.RegisterService(&internalServiceDesc, &internalServer{})
	log.Printf("gRPC listening on %s", lis.Addr().String())
	if err := s.Serve(lis); err != nil {
		log.Fatalf("serve: %v", err)
	}
}
