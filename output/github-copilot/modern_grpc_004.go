package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"net"
	"os"
	"os/signal"
	"sort"
	"sync"
	"syscall"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/reflection"
	"google.golang.org/grpc/status"
	"google.golang.org/protobuf/reflect/protodesc"
	"google.golang.org/protobuf/reflect/protoregistry"
	"google.golang.org/protobuf/types/descriptorpb"
	"google.golang.org/protobuf/types/known/emptypb"
	"google.golang.org/protobuf/types/known/structpb"
)

const (
	servicePackage       = "devmicro"
	serviceMetadataFile  = "devmicro.proto"
	defaultListenAddress = ":50051"
)

type userRecord struct {
	ID        string
	Name      string
	Email     string
	CreatedAt time.Time
}

type orderRecord struct {
	ID        string
	UserID    string
	Item      string
	Quantity  int64
	Amount    float64
	Status    string
	CreatedAt time.Time
}

type paymentRecord struct {
	ID        string
	OrderID   string
	Amount    float64
	Currency  string
	Method    string
	Status    string
	CreatedAt time.Time
}

type devServer struct {
	mu       sync.RWMutex
	users    map[string]userRecord
	orders   map[string]orderRecord
	payments map[string]paymentRecord
}

func newDevServer() *devServer {
	return &devServer{
		users:    make(map[string]userRecord),
		orders:   make(map[string]orderRecord),
		payments: make(map[string]paymentRecord),
	}
}

type UserServiceServer interface {
	CreateUser(context.Context, *structpb.Struct) (*structpb.Struct, error)
	GetUser(context.Context, *structpb.Struct) (*structpb.Struct, error)
	DeleteUser(context.Context, *structpb.Struct) (*emptypb.Empty, error)
}

type OrderServiceServer interface {
	CreateOrder(context.Context, *structpb.Struct) (*structpb.Struct, error)
	GetOrder(context.Context, *structpb.Struct) (*structpb.Struct, error)
	ListOrders(context.Context, *structpb.Struct) (*structpb.Struct, error)
}

type PaymentServiceServer interface {
	CreatePayment(context.Context, *structpb.Struct) (*structpb.Struct, error)
	GetPayment(context.Context, *structpb.Struct) (*structpb.Struct, error)
	RefundPayment(context.Context, *structpb.Struct) (*structpb.Struct, error)
}

func RegisterUserServiceServer(s grpc.ServiceRegistrar, srv UserServiceServer) {
	s.RegisterService(&UserService_ServiceDesc, srv)
}

func RegisterOrderServiceServer(s grpc.ServiceRegistrar, srv OrderServiceServer) {
	s.RegisterService(&OrderService_ServiceDesc, srv)
}

func RegisterPaymentServiceServer(s grpc.ServiceRegistrar, srv PaymentServiceServer) {
	s.RegisterService(&PaymentService_ServiceDesc, srv)
}

func (s *devServer) CreateUser(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	id, err := requiredString(req, "id")
	if err != nil {
		return nil, err
	}
	name, err := requiredString(req, "name")
	if err != nil {
		return nil, err
	}
	email, err := requiredString(req, "email")
	if err != nil {
		return nil, err
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	if _, exists := s.users[id]; exists {
		return nil, status.Errorf(codes.AlreadyExists, "user %q already exists", id)
	}

	user := userRecord{
		ID:        id,
		Name:      name,
		Email:     email,
		CreatedAt: time.Now().UTC(),
	}
	s.users[id] = user

	return newStruct(map[string]any{
		"user":    userToMap(user),
		"message": "user created",
	})
}

func (s *devServer) GetUser(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	id, err := requiredString(req, "id")
	if err != nil {
		return nil, err
	}

	s.mu.RLock()
	user, exists := s.users[id]
	s.mu.RUnlock()
	if !exists {
		return nil, status.Errorf(codes.NotFound, "user %q not found", id)
	}

	return newStruct(map[string]any{
		"user": userToMap(user),
	})
}

func (s *devServer) DeleteUser(_ context.Context, req *structpb.Struct) (*emptypb.Empty, error) {
	id, err := requiredString(req, "id")
	if err != nil {
		return nil, err
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	if _, exists := s.users[id]; !exists {
		return nil, status.Errorf(codes.NotFound, "user %q not found", id)
	}
	delete(s.users, id)

	return &emptypb.Empty{}, nil
}

func (s *devServer) CreateOrder(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	id, err := requiredString(req, "id")
	if err != nil {
		return nil, err
	}
	userID, err := requiredString(req, "user_id")
	if err != nil {
		return nil, err
	}
	item, err := requiredString(req, "item")
	if err != nil {
		return nil, err
	}
	quantity, err := requiredInt(req, "quantity")
	if err != nil {
		return nil, err
	}
	amount, err := requiredFloat(req, "amount")
	if err != nil {
		return nil, err
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	if _, exists := s.orders[id]; exists {
		return nil, status.Errorf(codes.AlreadyExists, "order %q already exists", id)
	}
	if _, exists := s.users[userID]; !exists {
		return nil, status.Errorf(codes.NotFound, "user %q not found", userID)
	}

	order := orderRecord{
		ID:        id,
		UserID:    userID,
		Item:      item,
		Quantity:  quantity,
		Amount:    amount,
		Status:    "created",
		CreatedAt: time.Now().UTC(),
	}
	s.orders[id] = order

	return newStruct(map[string]any{
		"order":   orderToMap(order),
		"message": "order created",
	})
}

func (s *devServer) GetOrder(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	id, err := requiredString(req, "id")
	if err != nil {
		return nil, err
	}

	s.mu.RLock()
	order, exists := s.orders[id]
	s.mu.RUnlock()
	if !exists {
		return nil, status.Errorf(codes.NotFound, "order %q not found", id)
	}

	return newStruct(map[string]any{
		"order": orderToMap(order),
	})
}

func (s *devServer) ListOrders(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	filterUserID, _ := optionalString(req, "user_id")

	s.mu.RLock()
	orders := make([]orderRecord, 0, len(s.orders))
	for _, order := range s.orders {
		if filterUserID != "" && order.UserID != filterUserID {
			continue
		}
		orders = append(orders, order)
	}
	s.mu.RUnlock()

	sort.Slice(orders, func(i, j int) bool {
		return orders[i].CreatedAt.Before(orders[j].CreatedAt)
	})

	items := make([]any, 0, len(orders))
	for _, order := range orders {
		items = append(items, orderToMap(order))
	}

	return newStruct(map[string]any{
		"orders": items,
		"count":  len(items),
	})
}

func (s *devServer) CreatePayment(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	id, err := requiredString(req, "id")
	if err != nil {
		return nil, err
	}
	orderID, err := requiredString(req, "order_id")
	if err != nil {
		return nil, err
	}
	amount, err := requiredFloat(req, "amount")
	if err != nil {
		return nil, err
	}
	currency, err := requiredString(req, "currency")
	if err != nil {
		return nil, err
	}
	method, err := requiredString(req, "method")
	if err != nil {
		return nil, err
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	if _, exists := s.payments[id]; exists {
		return nil, status.Errorf(codes.AlreadyExists, "payment %q already exists", id)
	}
	if _, exists := s.orders[orderID]; !exists {
		return nil, status.Errorf(codes.NotFound, "order %q not found", orderID)
	}

	payment := paymentRecord{
		ID:        id,
		OrderID:   orderID,
		Amount:    amount,
		Currency:  currency,
		Method:    method,
		Status:    "captured",
		CreatedAt: time.Now().UTC(),
	}
	s.payments[id] = payment

	return newStruct(map[string]any{
		"payment": paymentToMap(payment),
		"message": "payment captured",
	})
}

func (s *devServer) GetPayment(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	id, err := requiredString(req, "id")
	if err != nil {
		return nil, err
	}

	s.mu.RLock()
	payment, exists := s.payments[id]
	s.mu.RUnlock()
	if !exists {
		return nil, status.Errorf(codes.NotFound, "payment %q not found", id)
	}

	return newStruct(map[string]any{
		"payment": paymentToMap(payment),
	})
}

func (s *devServer) RefundPayment(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	id, err := requiredString(req, "id")
	if err != nil {
		return nil, err
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	payment, exists := s.payments[id]
	if !exists {
		return nil, status.Errorf(codes.NotFound, "payment %q not found", id)
	}
	if payment.Status == "refunded" {
		return nil, status.Errorf(codes.FailedPrecondition, "payment %q is already refunded", id)
	}

	payment.Status = "refunded"
	s.payments[id] = payment

	return newStruct(map[string]any{
		"payment": paymentToMap(payment),
		"message": "payment refunded",
	})
}

func requestMap(req *structpb.Struct) map[string]any {
	if req == nil {
		return map[string]any{}
	}
	return req.AsMap()
}

func requiredString(req *structpb.Struct, key string) (string, error) {
	value, ok := requestMap(req)[key]
	if !ok {
		return "", status.Errorf(codes.InvalidArgument, "missing required field %q", key)
	}
	s, ok := value.(string)
	if !ok || s == "" {
		return "", status.Errorf(codes.InvalidArgument, "field %q must be a non-empty string", key)
	}
	return s, nil
}

func optionalString(req *structpb.Struct, key string) (string, bool) {
	value, ok := requestMap(req)[key]
	if !ok {
		return "", false
	}
	s, ok := value.(string)
	if !ok {
		return "", false
	}
	return s, true
}

func requiredFloat(req *structpb.Struct, key string) (float64, error) {
	value, ok := requestMap(req)[key]
	if !ok {
		return 0, status.Errorf(codes.InvalidArgument, "missing required field %q", key)
	}
	number, ok := value.(float64)
	if !ok {
		return 0, status.Errorf(codes.InvalidArgument, "field %q must be numeric", key)
	}
	return number, nil
}

func requiredInt(req *structpb.Struct, key string) (int64, error) {
	number, err := requiredFloat(req, key)
	if err != nil {
		return 0, err
	}
	whole := int64(number)
	if float64(whole) != number || whole <= 0 {
		return 0, status.Errorf(codes.InvalidArgument, "field %q must be a positive integer", key)
	}
	return whole, nil
}

func newStruct(data map[string]any) (*structpb.Struct, error) {
	msg, err := structpb.NewStruct(data)
	if err != nil {
		return nil, status.Errorf(codes.Internal, "failed to build response: %v", err)
	}
	return msg, nil
}

func userToMap(user userRecord) map[string]any {
	return map[string]any{
		"id":         user.ID,
		"name":       user.Name,
		"email":      user.Email,
		"created_at": user.CreatedAt.Format(time.RFC3339),
	}
}

func orderToMap(order orderRecord) map[string]any {
	return map[string]any{
		"id":         order.ID,
		"user_id":    order.UserID,
		"item":       order.Item,
		"quantity":   order.Quantity,
		"amount":     order.Amount,
		"status":     order.Status,
		"created_at": order.CreatedAt.Format(time.RFC3339),
	}
}

func paymentToMap(payment paymentRecord) map[string]any {
	return map[string]any{
		"id":         payment.ID,
		"order_id":   payment.OrderID,
		"amount":     payment.Amount,
		"currency":   payment.Currency,
		"method":     payment.Method,
		"status":     payment.Status,
		"created_at": payment.CreatedAt.Format(time.RFC3339),
	}
}

func ptr[T any](v T) *T {
	return &v
}

func registerReflectionDescriptor() {
	fdProto := &descriptorpb.FileDescriptorProto{
		Name:       ptr(serviceMetadataFile),
		Package:    ptr(servicePackage),
		Syntax:     ptr("proto3"),
		Dependency: []string{"google/protobuf/empty.proto", "google/protobuf/struct.proto"},
		Service: []*descriptorpb.ServiceDescriptorProto{
			{
				Name: ptr("UserService"),
				Method: []*descriptorpb.MethodDescriptorProto{
					{Name: ptr("CreateUser"), InputType: ptr(".google.protobuf.Struct"), OutputType: ptr(".google.protobuf.Struct")},
					{Name: ptr("GetUser"), InputType: ptr(".google.protobuf.Struct"), OutputType: ptr(".google.protobuf.Struct")},
					{Name: ptr("DeleteUser"), InputType: ptr(".google.protobuf.Struct"), OutputType: ptr(".google.protobuf.Empty")},
				},
			},
			{
				Name: ptr("OrderService"),
				Method: []*descriptorpb.MethodDescriptorProto{
					{Name: ptr("CreateOrder"), InputType: ptr(".google.protobuf.Struct"), OutputType: ptr(".google.protobuf.Struct")},
					{Name: ptr("GetOrder"), InputType: ptr(".google.protobuf.Struct"), OutputType: ptr(".google.protobuf.Struct")},
					{Name: ptr("ListOrders"), InputType: ptr(".google.protobuf.Struct"), OutputType: ptr(".google.protobuf.Struct")},
				},
			},
			{
				Name: ptr("PaymentService"),
				Method: []*descriptorpb.MethodDescriptorProto{
					{Name: ptr("CreatePayment"), InputType: ptr(".google.protobuf.Struct"), OutputType: ptr(".google.protobuf.Struct")},
					{Name: ptr("GetPayment"), InputType: ptr(".google.protobuf.Struct"), OutputType: ptr(".google.protobuf.Struct")},
					{Name: ptr("RefundPayment"), InputType: ptr(".google.protobuf.Struct"), OutputType: ptr(".google.protobuf.Struct")},
				},
			},
		},
	}

	file, err := protodesc.NewFile(fdProto, protoregistry.GlobalFiles)
	if err != nil {
		panic(fmt.Sprintf("failed to build reflection descriptor: %v", err))
	}
	if err := protoregistry.GlobalFiles.RegisterFile(file); err != nil {
		panic(fmt.Sprintf("failed to register reflection descriptor: %v", err))
	}
}

func _UserService_CreateUser_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(structpb.Struct)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(UserServiceServer).CreateUser(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/devmicro.UserService/CreateUser"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(UserServiceServer).CreateUser(ctx, req.(*structpb.Struct))
	}
	return interceptor(ctx, in, info, handler)
}

func _UserService_GetUser_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(structpb.Struct)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(UserServiceServer).GetUser(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/devmicro.UserService/GetUser"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(UserServiceServer).GetUser(ctx, req.(*structpb.Struct))
	}
	return interceptor(ctx, in, info, handler)
}

func _UserService_DeleteUser_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(structpb.Struct)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(UserServiceServer).DeleteUser(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/devmicro.UserService/DeleteUser"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(UserServiceServer).DeleteUser(ctx, req.(*structpb.Struct))
	}
	return interceptor(ctx, in, info, handler)
}

func _OrderService_CreateOrder_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(structpb.Struct)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(OrderServiceServer).CreateOrder(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/devmicro.OrderService/CreateOrder"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(OrderServiceServer).CreateOrder(ctx, req.(*structpb.Struct))
	}
	return interceptor(ctx, in, info, handler)
}

func _OrderService_GetOrder_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(structpb.Struct)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(OrderServiceServer).GetOrder(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/devmicro.OrderService/GetOrder"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(OrderServiceServer).GetOrder(ctx, req.(*structpb.Struct))
	}
	return interceptor(ctx, in, info, handler)
}

func _OrderService_ListOrders_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(structpb.Struct)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(OrderServiceServer).ListOrders(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/devmicro.OrderService/ListOrders"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(OrderServiceServer).ListOrders(ctx, req.(*structpb.Struct))
	}
	return interceptor(ctx, in, info, handler)
}

func _PaymentService_CreatePayment_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(structpb.Struct)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(PaymentServiceServer).CreatePayment(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/devmicro.PaymentService/CreatePayment"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(PaymentServiceServer).CreatePayment(ctx, req.(*structpb.Struct))
	}
	return interceptor(ctx, in, info, handler)
}

func _PaymentService_GetPayment_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(structpb.Struct)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(PaymentServiceServer).GetPayment(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/devmicro.PaymentService/GetPayment"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(PaymentServiceServer).GetPayment(ctx, req.(*structpb.Struct))
	}
	return interceptor(ctx, in, info, handler)
}

func _PaymentService_RefundPayment_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(structpb.Struct)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(PaymentServiceServer).RefundPayment(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/devmicro.PaymentService/RefundPayment"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(PaymentServiceServer).RefundPayment(ctx, req.(*structpb.Struct))
	}
	return interceptor(ctx, in, info, handler)
}

var UserService_ServiceDesc = grpc.ServiceDesc{
	ServiceName: "devmicro.UserService",
	HandlerType: (*UserServiceServer)(nil),
	Methods: []grpc.MethodDesc{
		{MethodName: "CreateUser", Handler: _UserService_CreateUser_Handler},
		{MethodName: "GetUser", Handler: _UserService_GetUser_Handler},
		{MethodName: "DeleteUser", Handler: _UserService_DeleteUser_Handler},
	},
	Streams:  []grpc.StreamDesc{},
	Metadata: serviceMetadataFile,
}

var OrderService_ServiceDesc = grpc.ServiceDesc{
	ServiceName: "devmicro.OrderService",
	HandlerType: (*OrderServiceServer)(nil),
	Methods: []grpc.MethodDesc{
		{MethodName: "CreateOrder", Handler: _OrderService_CreateOrder_Handler},
		{MethodName: "GetOrder", Handler: _OrderService_GetOrder_Handler},
		{MethodName: "ListOrders", Handler: _OrderService_ListOrders_Handler},
	},
	Streams:  []grpc.StreamDesc{},
	Metadata: serviceMetadataFile,
}

var PaymentService_ServiceDesc = grpc.ServiceDesc{
	ServiceName: "devmicro.PaymentService",
	HandlerType: (*PaymentServiceServer)(nil),
	Methods: []grpc.MethodDesc{
		{MethodName: "CreatePayment", Handler: _PaymentService_CreatePayment_Handler},
		{MethodName: "GetPayment", Handler: _PaymentService_GetPayment_Handler},
		{MethodName: "RefundPayment", Handler: _PaymentService_RefundPayment_Handler},
	},
	Streams:  []grpc.StreamDesc{},
	Metadata: serviceMetadataFile,
}

func main() {
	registerReflectionDescriptor()

	address := os.Getenv("GRPC_ADDR")
	if address == "" {
		address = defaultListenAddress
	}

	listener, err := net.Listen("tcp", address)
	if err != nil {
		log.Fatalf("listen %s: %v", address, err)
	}

	grpcServer := grpc.NewServer()
	server := newDevServer()

	RegisterUserServiceServer(grpcServer, server)
	RegisterOrderServiceServer(grpcServer, server)
	RegisterPaymentServiceServer(grpcServer, server)
	reflection.Register(grpcServer)

	stopSignals := make(chan os.Signal, 1)
	signal.Notify(stopSignals, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		<-stopSignals
		log.Printf("shutting down gRPC server")
		grpcServer.GracefulStop()
	}()

	log.Printf("gRPC development server listening on %s", address)
	if err := grpcServer.Serve(listener); err != nil && !errors.Is(err, grpc.ErrServerStopped) {
		log.Fatalf("server stopped with error: %v", err)
	}
}