package main

import (
	"context"
	"fmt"
	"log"
	"net"
	"sync"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/reflection"

	userpb "myapp/proto/user"
	orderpb "myapp/proto/order"
	paymentpb "myapp/proto/payment"
)

// --- User Management Service ---

type UserService struct {
	userpb.UnimplementedUserServiceServer
	mu    sync.RWMutex
	users map[string]*userpb.User
}

func NewUserService() *UserService {
	return &UserService{
		users: make(map[string]*userpb.User),
	}
}

func (s *UserService) CreateUser(ctx context.Context, req *userpb.CreateUserRequest) (*userpb.User, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	id := fmt.Sprintf("user_%d", len(s.users)+1)
	user := &userpb.User{
		Id:        id,
		Name:      req.Name,
		Email:     req.Email,
		CreatedAt: time.Now().Unix(),
	}
	s.users[id] = user
	log.Printf("Created user: %s", id)
	return user, nil
}

func (s *UserService) GetUser(ctx context.Context, req *userpb.GetUserRequest) (*userpb.User, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	user, ok := s.users[req.Id]
	if !ok {
		return nil, fmt.Errorf("user %s not found", req.Id)
	}
	return user, nil
}

func (s *UserService) ListUsers(ctx context.Context, req *userpb.ListUsersRequest) (*userpb.ListUsersResponse, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	var users []*userpb.User
	for _, u := range s.users {
		users = append(users, u)
	}
	return &userpb.ListUsersResponse{Users: users}, nil
}

// --- Order Service ---

type OrderService struct {
	orderpb.UnimplementedOrderServiceServer
	mu     sync.RWMutex
	orders map[string]*orderpb.Order
}

func NewOrderService() *OrderService {
	return &OrderService{
		orders: make(map[string]*orderpb.Order),
	}
}

func (s *OrderService) CreateOrder(ctx context.Context, req *orderpb.CreateOrderRequest) (*orderpb.Order, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	id := fmt.Sprintf("order_%d", len(s.orders)+1)
	order := &orderpb.Order{
		Id:        id,
		UserId:    req.UserId,
		Items:     req.Items,
		Total:     req.Total,
		Status:    "pending",
		CreatedAt: time.Now().Unix(),
	}
	s.orders[id] = order
	log.Printf("Created order: %s for user: %s", id, req.UserId)
	return order, nil
}

func (s *OrderService) GetOrder(ctx context.Context, req *orderpb.GetOrderRequest) (*orderpb.Order, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	order, ok := s.orders[req.Id]
	if !ok {
		return nil, fmt.Errorf("order %s not found", req.Id)
	}
	return order, nil
}

func (s *OrderService) ListOrdersByUser(ctx context.Context, req *orderpb.ListOrdersByUserRequest) (*orderpb.ListOrdersResponse, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	var orders []*orderpb.Order
	for _, o := range s.orders {
		if o.UserId == req.UserId {
			orders = append(orders, o)
		}
	}
	return &orderpb.ListOrdersResponse{Orders: orders}, nil
}

// --- Payment Service ---

type PaymentService struct {
	paymentpb.UnimplementedPaymentServiceServer
	mu       sync.RWMutex
	payments map[string]*paymentpb.Payment
}

func NewPaymentService() *PaymentService {
	return &PaymentService{
		payments: make(map[string]*paymentpb.Payment),
	}
}

func (s *PaymentService) ProcessPayment(ctx context.Context, req *paymentpb.ProcessPaymentRequest) (*paymentpb.Payment, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	id := fmt.Sprintf("pay_%d", len(s.payments)+1)
	payment := &paymentpb.Payment{
		Id:          id,
		OrderId:     req.OrderId,
		Amount:      req.Amount,
		Currency:    req.Currency,
		Method:      req.Method,
		Status:      "completed",
		ProcessedAt: time.Now().Unix(),
	}
	s.payments[id] = payment
	log.Printf("Processed payment: %s for order: %s", id, req.OrderId)
	return payment, nil
}

func (s *PaymentService) GetPayment(ctx context.Context, req *paymentpb.GetPaymentRequest) (*paymentpb.Payment, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	payment, ok := s.payments[req.Id]
	if !ok {
		return nil, fmt.Errorf("payment %s not found", req.Id)
	}
	return payment, nil
}

func (s *PaymentService) RefundPayment(ctx context.Context, req *paymentpb.RefundPaymentRequest) (*paymentpb.Payment, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	payment, ok := s.payments[req.Id]
	if !ok {
		return nil, fmt.Errorf("payment %s not found", req.Id)
	}
	payment.Status = "refunded"
	log.Printf("Refunded payment: %s", req.Id)
	return payment, nil
}

func main() {
	lis, err := net.Listen("tcp", ":50051")
	if err != nil {
		log.Fatalf("Failed to listen: %v", err)
	}

	grpcServer := grpc.NewServer()

	userpb.RegisterUserServiceServer(grpcServer, NewUserService())
	orderpb.RegisterOrderServiceServer(grpcServer, NewOrderService())
	paymentpb.RegisterPaymentServiceServer(grpcServer, NewPaymentService())

	// Enable reflection for development service discovery
	reflection.Register(grpcServer)

	log.Println("gRPC server with reflection listening on :50051")
	if err := grpcServer.Serve(lis); err != nil {
		log.Fatalf("Failed to serve: %v", err)
	}
}