package main

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"log"
	"net"
	"os"
	"sync"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/reflection"
	"google.golang.org/grpc/status"
	"google.golang.org/protobuf/proto"
	"google.golang.org/protobuf/reflect/protodesc"
	"google.golang.org/protobuf/reflect/protoreflect"
	"google.golang.org/protobuf/reflect/protoregistry"
	"google.golang.org/protobuf/types/descriptorpb"
	"google.golang.org/protobuf/types/dynamicpb"
)

var (
	mdUser, mdCreateUserReq, mdGetUserReq                 protoreflect.MessageDescriptor
	mdOrder, mdCreateOrderReq, mdGetOrderReq            protoreflect.MessageDescriptor
	mdPayment, mdProcessPaymentReq, mdGetPaymentReq    protoreflect.MessageDescriptor
)

func strField(num int32, name string) *descriptorpb.FieldDescriptorProto {
	return &descriptorpb.FieldDescriptorProto{
		Name:   proto.String(name),
		Number: proto.Int32(num),
		Label:  descriptorpb.FieldDescriptorProto_LABEL_OPTIONAL.Enum(),
		Type:   descriptorpb.FieldDescriptorProto_TYPE_STRING.Enum(),
	}
}

func doubleField(num int32, name string) *descriptorpb.FieldDescriptorProto {
	return &descriptorpb.FieldDescriptorProto{
		Name:   proto.String(name),
		Number: proto.Int32(num),
		Label:  descriptorpb.FieldDescriptorProto_LABEL_OPTIONAL.Enum(),
		Type:   descriptorpb.FieldDescriptorProto_TYPE_DOUBLE.Enum(),
	}
}

func fileDescriptorProto() *descriptorpb.FileDescriptorProto {
	return &descriptorpb.FileDescriptorProto{
		Name:    proto.String("dev/v1/api.proto"),
		Package: proto.String("dev.v1"),
		Syntax:  proto.String("proto3"),
		MessageType: []*descriptorpb.DescriptorProto{
			{Name: proto.String("User"), Field: []*descriptorpb.FieldDescriptorProto{
				strField(1, "id"), strField(2, "email"), strField(3, "name"),
			}},
			{Name: proto.String("CreateUserRequest"), Field: []*descriptorpb.FieldDescriptorProto{
				strField(1, "email"), strField(2, "name"),
			}},
			{Name: proto.String("GetUserRequest"), Field: []*descriptorpb.FieldDescriptorProto{
				strField(1, "id"),
			}},
			{Name: proto.String("Order"), Field: []*descriptorpb.FieldDescriptorProto{
				strField(1, "id"), strField(2, "user_id"), doubleField(3, "total"), strField(4, "status"),
			}},
			{Name: proto.String("CreateOrderRequest"), Field: []*descriptorpb.FieldDescriptorProto{
				strField(1, "user_id"), doubleField(2, "total"),
			}},
			{Name: proto.String("GetOrderRequest"), Field: []*descriptorpb.FieldDescriptorProto{
				strField(1, "id"),
			}},
			{Name: proto.String("Payment"), Field: []*descriptorpb.FieldDescriptorProto{
				strField(1, "id"), strField(2, "order_id"), doubleField(3, "amount"), strField(4, "status"),
			}},
			{Name: proto.String("ProcessPaymentRequest"), Field: []*descriptorpb.FieldDescriptorProto{
				strField(1, "order_id"), doubleField(2, "amount"),
			}},
			{Name: proto.String("GetPaymentRequest"), Field: []*descriptorpb.FieldDescriptorProto{
				strField(1, "id"),
			}},
		},
		Service: []*descriptorpb.ServiceDescriptorProto{
			{
				Name: proto.String("UserService"),
				Method: []*descriptorpb.MethodDescriptorProto{
					{Name: proto.String("CreateUser"), InputType: proto.String(".dev.v1.CreateUserRequest"), OutputType: proto.String(".dev.v1.User")},
					{Name: proto.String("GetUser"), InputType: proto.String(".dev.v1.GetUserRequest"), OutputType: proto.String(".dev.v1.User")},
				},
			},
			{
				Name: proto.String("OrderService"),
				Method: []*descriptorpb.MethodDescriptorProto{
					{Name: proto.String("CreateOrder"), InputType: proto.String(".dev.v1.CreateOrderRequest"), OutputType: proto.String(".dev.v1.Order")},
					{Name: proto.String("GetOrder"), InputType: proto.String(".dev.v1.GetOrderRequest"), OutputType: proto.String(".dev.v1.Order")},
				},
			},
			{
				Name: proto.String("PaymentService"),
				Method: []*descriptorpb.MethodDescriptorProto{
					{Name: proto.String("ProcessPayment"), InputType: proto.String(".dev.v1.ProcessPaymentRequest"), OutputType: proto.String(".dev.v1.Payment")},
					{Name: proto.String("GetPayment"), InputType: proto.String(".dev.v1.GetPaymentRequest"), OutputType: proto.String(".dev.v1.Payment")},
				},
			},
		},
	}
}

func init() {
	fd, err := protodesc.NewFile(fileDescriptorProto(), nil)
	if err != nil {
		panic(err)
	}
	if err := protoregistry.GlobalFiles.RegisterFile(fd); err != nil {
		panic(err)
	}
	mdUser = fd.Messages().ByName("User")
	mdCreateUserReq = fd.Messages().ByName("CreateUserRequest")
	mdGetUserReq = fd.Messages().ByName("GetUserRequest")
	mdOrder = fd.Messages().ByName("Order")
	mdCreateOrderReq = fd.Messages().ByName("CreateOrderRequest")
	mdGetOrderReq = fd.Messages().ByName("GetOrderRequest")
	mdPayment = fd.Messages().ByName("Payment")
	mdProcessPaymentReq = fd.Messages().ByName("ProcessPaymentRequest")
	mdGetPaymentReq = fd.Messages().ByName("GetPaymentRequest")
}

func newID(prefix string) string {
	var b [8]byte
	if _, err := rand.Read(b[:]); err != nil {
		return prefix + hex.EncodeToString(b[:])
	}
	return prefix + hex.EncodeToString(b[:])
}

type userServer struct {
	mu    sync.RWMutex
	users map[string]*dynamicpb.Message
}

func newUserServer() *userServer {
	return &userServer{users: make(map[string]*dynamicpb.Message)}
}

func (s *userServer) createUser(_ context.Context, in *dynamicpb.Message) (*dynamicpb.Message, error) {
	email := in.Get(mdCreateUserReq.Fields().ByName("email")).String()
	name := in.Get(mdCreateUserReq.Fields().ByName("name")).String()
	if email == "" {
		return nil, status.Error(codes.InvalidArgument, "email is required")
	}
	id := newID("usr-")
	out := dynamicpb.NewMessage(mdUser)
	out.Set(mdUser.Fields().ByName("id"), protoreflect.ValueOfString(id))
	out.Set(mdUser.Fields().ByName("email"), protoreflect.ValueOfString(email))
	out.Set(mdUser.Fields().ByName("name"), protoreflect.ValueOfString(name))
	s.mu.Lock()
	s.users[id] = out
	s.mu.Unlock()
	return out, nil
}

func (s *userServer) getUser(_ context.Context, in *dynamicpb.Message) (*dynamicpb.Message, error) {
	id := in.Get(mdGetUserReq.Fields().ByName("id")).String()
	if id == "" {
		return nil, status.Error(codes.InvalidArgument, "id is required")
	}
	s.mu.RLock()
	u, ok := s.users[id]
	s.mu.RUnlock()
	if !ok {
		return nil, status.Errorf(codes.NotFound, "user %s not found", id)
	}
	return u, nil
}

type orderServer struct {
	mu     sync.RWMutex
	orders map[string]*dynamicpb.Message
}

func newOrderServer() *orderServer {
	return &orderServer{orders: make(map[string]*dynamicpb.Message)}
}

func (s *orderServer) createOrder(_ context.Context, in *dynamicpb.Message) (*dynamicpb.Message, error) {
	uid := in.Get(mdCreateOrderReq.Fields().ByName("user_id")).String()
	total := in.Get(mdCreateOrderReq.Fields().ByName("total")).Float()
	if uid == "" || total <= 0 {
		return nil, status.Error(codes.InvalidArgument, "user_id and positive total are required")
	}
	id := newID("ord-")
	out := dynamicpb.NewMessage(mdOrder)
	out.Set(mdOrder.Fields().ByName("id"), protoreflect.ValueOfString(id))
	out.Set(mdOrder.Fields().ByName("user_id"), protoreflect.ValueOfString(uid))
	out.Set(mdOrder.Fields().ByName("total"), protoreflect.ValueOfFloat64(total))
	out.Set(mdOrder.Fields().ByName("status"), protoreflect.ValueOfString("CREATED"))
	s.mu.Lock()
	s.orders[id] = out
	s.mu.Unlock()
	return out, nil
}

func (s *orderServer) getOrder(_ context.Context, in *dynamicpb.Message) (*dynamicpb.Message, error) {
	id := in.Get(mdGetOrderReq.Fields().ByName("id")).String()
	if id == "" {
		return nil, status.Error(codes.InvalidArgument, "id is required")
	}
	s.mu.RLock()
	o, ok := s.orders[id]
	s.mu.RUnlock()
	if !ok {
		return nil, status.Errorf(codes.NotFound, "order %s not found", id)
	}
	return o, nil
}

type paymentServer struct {
	mu       sync.RWMutex
	payments map[string]*dynamicpb.Message
}

func newPaymentServer() *paymentServer {
	return &paymentServer{payments: make(map[string]*dynamicpb.Message)}
}

func (s *paymentServer) processPayment(_ context.Context, in *dynamicpb.Message) (*dynamicpb.Message, error) {
	oid := in.Get(mdProcessPaymentReq.Fields().ByName("order_id")).String()
	amount := in.Get(mdProcessPaymentReq.Fields().ByName("amount")).Float()
	if oid == "" || amount <= 0 {
		return nil, status.Error(codes.InvalidArgument, "order_id and positive amount are required")
	}
	id := newID("pay-")
	out := dynamicpb.NewMessage(mdPayment)
	out.Set(mdPayment.Fields().ByName("id"), protoreflect.ValueOfString(id))
	out.Set(mdPayment.Fields().ByName("order_id"), protoreflect.ValueOfString(oid))
	out.Set(mdPayment.Fields().ByName("amount"), protoreflect.ValueOfFloat64(amount))
	out.Set(mdPayment.Fields().ByName("status"), protoreflect.ValueOfString("CAPTURED"))
	s.mu.Lock()
	s.payments[id] = out
	s.mu.Unlock()
	return out, nil
}

func (s *paymentServer) getPayment(_ context.Context, in *dynamicpb.Message) (*dynamicpb.Message, error) {
	id := in.Get(mdGetPaymentReq.Fields().ByName("id")).String()
	if id == "" {
		return nil, status.Error(codes.InvalidArgument, "id is required")
	}
	s.mu.RLock()
	p, ok := s.payments[id]
	s.mu.RUnlock()
	if !ok {
		return nil, status.Errorf(codes.NotFound, "payment %s not found", id)
	}
	return p, nil
}

func userCreateHandler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := dynamicpb.NewMessage(mdCreateUserReq)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*userServer).createUser(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/dev.v1.UserService/CreateUser"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(*userServer).createUser(ctx, req.(*dynamicpb.Message))
	}
	return interceptor(ctx, in, info, handler)
}

func userGetHandler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := dynamicpb.NewMessage(mdGetUserReq)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*userServer).getUser(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/dev.v1.UserService/GetUser"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(*userServer).getUser(ctx, req.(*dynamicpb.Message))
	}
	return interceptor(ctx, in, info, handler)
}

func orderCreateHandler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := dynamicpb.NewMessage(mdCreateOrderReq)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*orderServer).createOrder(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/dev.v1.OrderService/CreateOrder"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(*orderServer).createOrder(ctx, req.(*dynamicpb.Message))
	}
	return interceptor(ctx, in, info, handler)
}

func orderGetHandler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := dynamicpb.NewMessage(mdGetOrderReq)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*orderServer).getOrder(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/dev.v1.OrderService/GetOrder"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(*orderServer).getOrder(ctx, req.(*dynamicpb.Message))
	}
	return interceptor(ctx, in, info, handler)
}

func paymentProcessHandler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := dynamicpb.NewMessage(mdProcessPaymentReq)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*paymentServer).processPayment(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/dev.v1.PaymentService/ProcessPayment"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(*paymentServer).processPayment(ctx, req.(*dynamicpb.Message))
	}
	return interceptor(ctx, in, info, handler)
}

func paymentGetHandler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := dynamicpb.NewMessage(mdGetPaymentReq)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*paymentServer).getPayment(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/dev.v1.PaymentService/GetPayment"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(*paymentServer).getPayment(ctx, req.(*dynamicpb.Message))
	}
	return interceptor(ctx, in, info, handler)
}

var (
	userServiceDesc = grpc.ServiceDesc{
		ServiceName: "dev.v1.UserService",
		HandlerType: (*userServer)(nil),
		Methods: []grpc.MethodDesc{
			{MethodName: "CreateUser", Handler: userCreateHandler},
			{MethodName: "GetUser", Handler: userGetHandler},
		},
		Streams:  []grpc.StreamDesc{},
		Metadata: "dev/v1/api.proto",
	}
	orderServiceDesc = grpc.ServiceDesc{
		ServiceName: "dev.v1.OrderService",
		HandlerType: (*orderServer)(nil),
		Methods: []grpc.MethodDesc{
			{MethodName: "CreateOrder", Handler: orderCreateHandler},
			{MethodName: "GetOrder", Handler: orderGetHandler},
		},
		Streams:  []grpc.StreamDesc{},
		Metadata: "dev/v1/api.proto",
	}
	paymentServiceDesc = grpc.ServiceDesc{
		ServiceName: "dev.v1.PaymentService",
		HandlerType: (*paymentServer)(nil),
		Methods: []grpc.MethodDesc{
			{MethodName: "ProcessPayment", Handler: paymentProcessHandler},
			{MethodName: "GetPayment", Handler: paymentGetHandler},
		},
		Streams:  []grpc.StreamDesc{},
		Metadata: "dev/v1/api.proto",
	}
)

func main() {
	addr := ":50051"
	if v := os.Getenv("GRPC_LISTEN_ADDR"); v != "" {
		addr = v
	}
	lis, err := net.Listen("tcp", addr)
	if err != nil {
		log.Fatalf("listen: %v", err)
	}
	grpcServer := grpc.NewServer()
	grpcServer.RegisterService(&userServiceDesc, newUserServer())
	grpcServer.RegisterService(&orderServiceDesc, newOrderServer())
	grpcServer.RegisterService(&paymentServiceDesc, newPaymentServer())
	reflection.Register(grpcServer)
	log.Printf("gRPC (users, orders, payments) listening on %s; reflection enabled", addr)
	if err := grpcServer.Serve(lis); err != nil {
		log.Fatalf("serve: %v", err)
	}
}
