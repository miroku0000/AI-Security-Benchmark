package main

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"log"
	"net"
	"sync"
	"time"

	pb "grpc-finance/proto"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/status"
)

type account struct {
	balanceCents int64
	currency     string
}

type transactionServer struct {
	pb.UnimplementedTransactionServiceServer
	mu               sync.RWMutex
	accounts         map[string]*account
	idempotencyCache map[string]*pb.CreateTransactionResponse
}

func newTransactionServer() *transactionServer {
	return &transactionServer{
		accounts: map[string]*account{
			"acct-001": {balanceCents: 500000, currency: "USD"},
			"acct-002": {balanceCents: 250000, currency: "USD"},
			"acct-003": {balanceCents: 100000, currency: "USD"},
		},
		idempotencyCache: make(map[string]*pb.CreateTransactionResponse),
	}
}

func generateTransactionID() (string, error) {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return "txn-" + hex.EncodeToString(b), nil
}

func (s *transactionServer) CreateTransaction(ctx context.Context, req *pb.CreateTransactionRequest) (*pb.CreateTransactionResponse, error) {
	if req.FromAccountId == "" || req.ToAccountId == "" {
		return nil, status.Error(codes.InvalidArgument, "from_account_id and to_account_id are required")
	}
	if req.AmountCents <= 0 {
		return nil, status.Error(codes.InvalidArgument, "amount_cents must be positive")
	}
	if req.IdempotencyKey == "" {
		return nil, status.Error(codes.InvalidArgument, "idempotency_key is required")
	}
	if req.FromAccountId == req.ToAccountId {
		return nil, status.Error(codes.InvalidArgument, "cannot transfer to the same account")
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	if cached, ok := s.idempotencyCache[req.IdempotencyKey]; ok {
		return cached, nil
	}

	fromAcct, ok := s.accounts[req.FromAccountId]
	if !ok {
		return nil, status.Errorf(codes.NotFound, "account %s not found", req.FromAccountId)
	}
	toAcct, ok := s.accounts[req.ToAccountId]
	if !ok {
		return nil, status.Errorf(codes.NotFound, "account %s not found", req.ToAccountId)
	}

	if fromAcct.balanceCents < req.AmountCents {
		return nil, status.Error(codes.FailedPrecondition, "insufficient funds")
	}

	fromAcct.balanceCents -= req.AmountCents
	toAcct.balanceCents += req.AmountCents

	txnID, err := generateTransactionID()
	if err != nil {
		return nil, status.Error(codes.Internal, "failed to generate transaction ID")
	}

	resp := &pb.CreateTransactionResponse{
		TransactionId: txnID,
		Status:        "COMPLETED",
		Timestamp:     time.Now().Unix(),
	}

	s.idempotencyCache[req.IdempotencyKey] = resp

	log.Printf("Transaction %s: %s -> %s, amount: %d cents", txnID, req.FromAccountId, req.ToAccountId, req.AmountCents)
	return resp, nil
}

func (s *transactionServer) GetBalance(ctx context.Context, req *pb.GetBalanceRequest) (*pb.GetBalanceResponse, error) {
	if req.AccountId == "" {
		return nil, status.Error(codes.InvalidArgument, "account_id is required")
	}

	s.mu.RLock()
	defer s.mu.RUnlock()

	acct, ok := s.accounts[req.AccountId]
	if !ok {
		return nil, status.Errorf(codes.NotFound, "account %s not found", req.AccountId)
	}

	return &pb.GetBalanceResponse{
		AccountId:    req.AccountId,
		BalanceCents: acct.balanceCents,
		Currency:     acct.currency,
	}, nil
}

func main() {
	port := 50051

	var opts []grpc.ServerOption

	// Use TLS if cert files are available; otherwise log a warning.
	// In production, always provide TLS certificates for inter-service communication.
	creds, err := credentials.NewServerTLSFromFile("certs/server.crt", "certs/server.key")
	if err != nil {
		log.Printf("WARNING: TLS certs not found, running WITHOUT TLS. Do not use in production. (%v)", err)
	} else {
		opts = append(opts, grpc.Creds(creds))
		log.Println("TLS enabled")
	}

	srv := grpc.NewServer(opts...)
	pb.RegisterTransactionServiceServer(srv, newTransactionServer())

	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", port))
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}

	log.Printf("gRPC server listening on :%d", port)
	if err := srv.Serve(lis); err != nil {
		log.Fatalf("failed to serve: %v", err)
	}
}
