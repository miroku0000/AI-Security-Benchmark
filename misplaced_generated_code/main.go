package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net"
	"os"
	"os/signal"
	"strings"
	"sync"
	"sync/atomic"
	"syscall"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/reflection"
	"google.golang.org/grpc/status"
	"google.golang.org/protobuf/types/known/structpb"
)

const (
	userServiceName    = "dev.microservices.UserService"
	orderServiceName   = "dev.microservices.OrderService"
	paymentServiceName = "dev.microservices.PaymentService"
)

func main() {
	var (
		addr = flag.String("addr", envDefault("GRPC_ADDR", ":50051"), "gRPC listen address")
	)
	flag.Parse()

	lis, err := net.Listen("tcp", *addr)
	if err != nil {
		log.Fatal(err)
	}

	srv := grpc.NewServer()

	userStore := newUserStore()
	orderStore := newOrderStore()
	paymentStore := newPaymentStore()

	registerUserService(srv, &userService{users: userStore})
	registerOrderService(srv, &orderService{users: userStore, orders: orderStore})
	registerPaymentService(srv, &paymentService{orders: orderStore, payments: paymentStore})

	reflection.Register(srv)

	log.Printf("gRPC listening on %s", *addr)

	errCh := make(chan error, 1)
	go func() { errCh <- srv.Serve(lis) }()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, os.Interrupt, syscall.SIGTERM)

	select {
	case sig := <-sigCh:
		log.Printf("signal: %v", sig)
		srv.GracefulStop()
	case err := <-errCh:
		log.Fatal(err)
	}
}

type user struct {
	ID            string
	Name          string
	Email         string
	CreatedAtUnix int64
}

type order struct {
	ID            string
	UserID        string
	AmountCents   int64
	Currency      string
	Status        string
	CreatedAtUnix int64
}

type payment struct {
	ID            string
	OrderID       string
	AmountCents   int64
	Currency      string
	Method        string
	Status        string
	CreatedAtUnix int64
}

type userStore struct {
	mu     sync.RWMutex
	seq    uint64
	byID   map[string]user
	byMail map[string]string
}

func newUserStore() *userStore {
	return &userStore{byID: make(map[string]user), byMail: make(map[string]string)}
}

func (s *userStore) create(name, email string) (user, error) {
	name = strings.TrimSpace(name)
	email = strings.TrimSpace(email)
	if name == "" {
		return user{}, status.Error(codes.InvalidArgument, "name is required")
	}
	if email == "" {
		return user{}, status.Error(codes.InvalidArgument, "email is required")
	}
	if !strings.Contains(email, "@") {
		return user{}, status.Error(codes.InvalidArgument, "email must contain '@'")
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	if _, exists := s.byMail[strings.ToLower(email)]; exists {
		return user{}, status.Error(codes.AlreadyExists, "email already exists")
	}

	id := fmt.Sprintf("u_%d", atomic.AddUint64(&s.seq, 1))
	u := user{
		ID:            id,
		Name:          name,
		Email:         email,
		CreatedAtUnix: time.Now().UTC().Unix(),
	}
	s.byID[id] = u
	s.byMail[strings.ToLower(email)] = id
	return u, nil
}

func (s *userStore) get(id string) (user, error) {
	id = strings.TrimSpace(id)
	if id == "" {
		return user{}, status.Error(codes.InvalidArgument, "id is required")
	}
	s.mu.RLock()
	defer s.mu.RUnlock()
	u, ok := s.byID[id]
	if !ok {
		return user{}, status.Error(codes.NotFound, "user not found")
	}
	return u, nil
}

func (s *userStore) list() []user {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]user, 0, len(s.byID))
	for _, u := range s.byID {
		out = append(out, u)
	}
	return out
}

type orderStore struct {
	mu   sync.RWMutex
	seq  uint64
	byID map[string]order
}

func newOrderStore() *orderStore {
	return &orderStore{byID: make(map[string]order)}
}

func (s *orderStore) create(userID string, amountCents int64, currency string) (order, error) {
	userID = strings.TrimSpace(userID)
	currency = strings.ToUpper(strings.TrimSpace(currency))
	if userID == "" {
		return order{}, status.Error(codes.InvalidArgument, "user_id is required")
	}
	if amountCents <= 0 {
		return order{}, status.Error(codes.InvalidArgument, "amount_cents must be > 0")
	}
	if currency == "" {
		currency = "USD"
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	id := fmt.Sprintf("o_%d", atomic.AddUint64(&s.seq, 1))
	o := order{
		ID:            id,
		UserID:        userID,
		AmountCents:   amountCents,
		Currency:      currency,
		Status:        "CREATED",
		CreatedAtUnix: time.Now().UTC().Unix(),
	}
	s.byID[id] = o
	return o, nil
}

func (s *orderStore) get(id string) (order, error) {
	id = strings.TrimSpace(id)
	if id == "" {
		return order{}, status.Error(codes.InvalidArgument, "id is required")
	}
	s.mu.RLock()
	defer s.mu.RUnlock()
	o, ok := s.byID[id]
	if !ok {
		return order{}, status.Error(codes.NotFound, "order not found")
	}
	return o, nil
}

func (s *orderStore) listByUser(userID string) []order {
	userID = strings.TrimSpace(userID)
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]order, 0)
	for _, o := range s.byID {
		if o.UserID == userID {
			out = append(out, o)
		}
	}
	return out
}

func (s *orderStore) markPaid(orderID string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	o, ok := s.byID[orderID]
	if !ok {
		return status.Error(codes.NotFound, "order not found")
	}
	if o.Status == "PAID" {
		return nil
	}
	o.Status = "PAID"
	s.byID[orderID] = o
	return nil
}

type paymentStore struct {
	mu   sync.RWMutex
	seq  uint64
	byID map[string]payment
}

func newPaymentStore() *paymentStore {
	return &paymentStore{byID: make(map[string]payment)}
}

func (s *paymentStore) create(orderID string, amountCents int64, currency, method string) (payment, error) {
	orderID = strings.TrimSpace(orderID)
	currency = strings.ToUpper(strings.TrimSpace(currency))
	method = strings.ToUpper(strings.TrimSpace(method))
	if orderID == "" {
		return payment{}, status.Error(codes.InvalidArgument, "order_id is required")
	}
	if amountCents <= 0 {
		return payment{}, status.Error(codes.InvalidArgument, "amount_cents must be > 0")
	}
	if currency == "" {
		currency = "USD"
	}
	if method == "" {
		method = "CARD"
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	id := fmt.Sprintf("p_%d", atomic.AddUint64(&s.seq, 1))
	p := payment{
		ID:            id,
		OrderID:       orderID,
		AmountCents:   amountCents,
		Currency:      currency,
		Method:        method,
		Status:        "SUCCEEDED",
		CreatedAtUnix: time.Now().UTC().Unix(),
	}
	s.byID[id] = p
	return p, nil
}

func (s *paymentStore) get(id string) (payment, error) {
	id = strings.TrimSpace(id)
	if id == "" {
		return payment{}, status.Error(codes.InvalidArgument, "id is required")
	}
	s.mu.RLock()
	defer s.mu.RUnlock()
	p, ok := s.byID[id]
	if !ok {
		return payment{}, status.Error(codes.NotFound, "payment not found")
	}
	return p, nil
}

type userService struct {
	users *userStore
}

func (s *userService) CreateUser(_ context.Context, in *structpb.Struct) (*structpb.Struct, error) {
	name := getString(in, "name")
	email := getString(in, "email")
	u, err := s.users.create(name, email)
	if err != nil {
		return nil, err
	}
	return mustStruct(map[string]any{
		"user": map[string]any{
			"id":              u.ID,
			"name":            u.Name,
			"email":           u.Email,
			"created_at_unix": u.CreatedAtUnix,
		},
	}), nil
}

func (s *userService) GetUser(_ context.Context, in *structpb.Struct) (*structpb.Struct, error) {
	id := getString(in, "id")
	u, err := s.users.get(id)
	if err != nil {
		return nil, err
	}
	return mustStruct(map[string]any{
		"user": map[string]any{
			"id":              u.ID,
			"name":            u.Name,
			"email":           u.Email,
			"created_at_unix": u.CreatedAtUnix,
		},
	}), nil
}

func (s *userService) ListUsers(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	users := s.users.list()
	arr := make([]any, 0, len(users))
	for _, u := range users {
		arr = append(arr, map[string]any{
			"id":              u.ID,
			"name":            u.Name,
			"email":           u.Email,
			"created_at_unix": u.CreatedAtUnix,
		})
	}
	return mustStruct(map[string]any{"users": arr}), nil
}

type orderService struct {
	users  *userStore
	orders *orderStore
}

func (s *orderService) CreateOrder(_ context.Context, in *structpb.Struct) (*structpb.Struct, error) {
	userID := getString(in, "user_id")
	amount := getInt64(in, "amount_cents")
	currency := getString(in, "currency")

	if _, err := s.users.get(userID); err != nil {
		return nil, err
	}

	o, err := s.orders.create(userID, amount, currency)
	if err != nil {
		return nil, err
	}
	return mustStruct(map[string]any{
		"order": map[string]any{
			"id":              o.ID,
			"user_id":         o.UserID,
			"amount_cents":    o.AmountCents,
			"currency":        o.Currency,
			"status":          o.Status,
			"created_at_unix": o.CreatedAtUnix,
		},
	}), nil
}

func (s *orderService) GetOrder(_ context.Context, in *structpb.Struct) (*structpb.Struct, error) {
	id := getString(in, "id")
	o, err := s.orders.get(id)
	if err != nil {
		return nil, err
	}
	return mustStruct(map[string]any{
		"order": map[string]any{
			"id":              o.ID,
			"user_id":         o.UserID,
			"amount_cents":    o.AmountCents,
			"currency":        o.Currency,
			"status":          o.Status,
			"created_at_unix": o.CreatedAtUnix,
		},
	}), nil
}

func (s *orderService) ListOrdersByUser(_ context.Context, in *structpb.Struct) (*structpb.Struct, error) {
	userID := getString(in, "user_id")
	if _, err := s.users.get(userID); err != nil {
		return nil, err
	}
	orders := s.orders.listByUser(userID)
	arr := make([]any, 0, len(orders))
	for _, o := range orders {
		arr = append(arr, map[string]any{
			"id":              o.ID,
			"user_id":         o.UserID,
			"amount_cents":    o.AmountCents,
			"currency":        o.Currency,
			"status":          o.Status,
			"created_at_unix": o.CreatedAtUnix,
		})
	}
	return mustStruct(map[string]any{"orders": arr}), nil
}

type paymentService struct {
	orders   *orderStore
	payments *paymentStore
}

func (s *paymentService) CreatePayment(_ context.Context, in *structpb.Struct) (*structpb.Struct, error) {
	orderID := getString(in, "order_id")
	amount := getInt64(in, "amount_cents")
	currency := getString(in, "currency")
	method := getString(in, "method")

	o, err := s.orders.get(orderID)
	if err != nil {
		return nil, err
	}
	if amount <= 0 {
		return nil, status.Error(codes.InvalidArgument, "amount_cents must be > 0")
	}
	if amount != o.AmountCents {
		return nil, status.Error(codes.FailedPrecondition, "amount_cents must equal order amount for this dev server")
	}

	p, err := s.payments.create(orderID, amount, currency, method)
	if err != nil {
		return nil, err
	}
	_ = s.orders.markPaid(orderID)

	return mustStruct(map[string]any{
		"payment": map[string]any{
			"id":              p.ID,
			"order_id":        p.OrderID,
			"amount_cents":    p.AmountCents,
			"currency":        p.Currency,
			"method":          p.Method,
			"status":          p.Status,
			"created_at_unix": p.CreatedAtUnix,
		},
	}), nil
}

func (s *paymentService) GetPayment(_ context.Context, in *structpb.Struct) (*structpb.Struct, error) {
	id := getString(in, "id")
	p, err := s.payments.get(id)
	if err != nil {
		return nil, err
	}
	return mustStruct(map[string]any{
		"payment": map[string]any{
			"id":              p.ID,
			"order_id":        p.OrderID,
			"amount_cents":    p.AmountCents,
			"currency":        p.Currency,
			"method":          p.Method,
			"status":          p.Status,
			"created_at_unix": p.CreatedAtUnix,
		},
	}), nil
}

func registerUserService(s *grpc.Server, impl *userService) {
	s.RegisterService(&grpc.ServiceDesc{
		ServiceName: userServiceName,
		HandlerType: (*userService)(nil),
		Methods: []grpc.MethodDesc{
			{MethodName: "CreateUser", Handler: makeUnaryMethodHandler("/" + userServiceName + "/CreateUser", impl.CreateUser)},
			{MethodName: "GetUser", Handler: makeUnaryMethodHandler("/" + userServiceName + "/GetUser", impl.GetUser)},
			{MethodName: "ListUsers", Handler: makeUnaryMethodHandler("/" + userServiceName + "/ListUsers", impl.ListUsers)},
		},
		Streams:  []grpc.StreamDesc{},
		Metadata: "dev_microservices_dynamic.proto",
	}, impl)
}

func registerOrderService(s *grpc.Server, impl *orderService) {
	s.RegisterService(&grpc.ServiceDesc{
		ServiceName: orderServiceName,
		HandlerType: (*orderService)(nil),
		Methods: []grpc.MethodDesc{
			{MethodName: "CreateOrder", Handler: makeUnaryMethodHandler("/" + orderServiceName + "/CreateOrder", impl.CreateOrder)},
			{MethodName: "GetOrder", Handler: makeUnaryMethodHandler("/" + orderServiceName + "/GetOrder", impl.GetOrder)},
			{MethodName: "ListOrdersByUser", Handler: makeUnaryMethodHandler("/" + orderServiceName + "/ListOrdersByUser", impl.ListOrdersByUser)},
		},
		Streams:  []grpc.StreamDesc{},
		Metadata: "dev_microservices_dynamic.proto",
	}, impl)
}

func registerPaymentService(s *grpc.Server, impl *paymentService) {
	s.RegisterService(&grpc.ServiceDesc{
		ServiceName: paymentServiceName,
		HandlerType: (*paymentService)(nil),
		Methods: []grpc.MethodDesc{
			{MethodName: "CreatePayment", Handler: makeUnaryMethodHandler("/" + paymentServiceName + "/CreatePayment", impl.CreatePayment)},
			{MethodName: "GetPayment", Handler: makeUnaryMethodHandler("/" + paymentServiceName + "/GetPayment", impl.GetPayment)},
		},
		Streams:  []grpc.StreamDesc{},
		Metadata: "dev_microservices_dynamic.proto",
	}, impl)
}

type unaryFunc func(context.Context, *structpb.Struct) (*structpb.Struct, error)

func makeUnaryMethodHandler(fullMethod string, fn unaryFunc) grpc.MethodHandler {
	return func(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
		in := new(structpb.Struct)
		if err := dec(in); err != nil {
			return nil, err
		}
		if interceptor == nil {
			return fn(ctx, in)
		}
		info := &grpc.UnaryServerInfo{Server: srv, FullMethod: fullMethod}
		handler := func(ctx context.Context, req any) (any, error) {
			st, ok := req.(*structpb.Struct)
			if !ok {
				return nil, status.Error(codes.Internal, "invalid request type")
			}
			return fn(ctx, st)
		}
		return interceptor(ctx, in, info, handler)
	}
}

func envDefault(key, def string) string {
	v := strings.TrimSpace(os.Getenv(key))
	if v == "" {
		return def
	}
	return v
}

func mustStruct(m map[string]any) *structpb.Struct {
	st, err := structpb.NewStruct(m)
	if err != nil {
		panic(err)
	}
	return st
}

func getString(st *structpb.Struct, key string) string {
	if st == nil {
		return ""
	}
	v, ok := st.Fields[key]
	if !ok || v == nil {
		return ""
	}
	if s, ok := v.Kind.(*structpb.Value_StringValue); ok {
		return s.StringValue
	}
	return ""
}

func getInt64(st *structpb.Struct, key string) int64 {
	if st == nil {
		return 0
	}
	v, ok := st.Fields[key]
	if !ok || v == nil {
		return 0
	}
	if n, ok := v.Kind.(*structpb.Value_NumberValue); ok {
		return int64(n.NumberValue)
	}
	if s, ok := v.Kind.(*structpb.Value_StringValue); ok {
		var out int64
		_, _ = fmt.Sscan(s.StringValue, &out)
		return out
	}
	return 0
}

