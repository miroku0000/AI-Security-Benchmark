package transaction

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"sync/atomic"

	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	bankingv1 "example.com/banking/platform/api/banking/v1"
)

type Server struct {
	bankingv1.UnimplementedTransactionServiceServer
	mu       sync.Mutex
	balances map[string]int64
	seq      atomic.Uint64
}

func NewServer() *Server {
	return &Server{balances: make(map[string]int64)}
}

func (s *Server) CreateTransaction(ctx context.Context, req *bankingv1.CreateTransactionRequest) (*bankingv1.CreateTransactionResponse, error) {
	_ = ctx
	debit := strings.TrimSpace(req.GetDebitAccountId())
	credit := strings.TrimSpace(req.GetCreditAccountId())
	if debit == "" || credit == "" {
		return nil, status.Error(codes.InvalidArgument, "debit and credit account ids are required")
	}
	if debit == credit {
		return nil, status.Error(codes.InvalidArgument, "debit and credit account must differ")
	}
	amt := req.GetAmountMinorUnits()
	if amt <= 0 {
		return nil, status.Error(codes.InvalidArgument, "amount must be positive")
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	if s.balances[debit] < amt {
		return nil, status.Errorf(codes.FailedPrecondition, "insufficient funds on %s", debit)
	}

	s.balances[debit] -= amt
	s.balances[credit] += amt
	txID := fmt.Sprintf("tx-%d", s.seq.Add(1))

	return &bankingv1.CreateTransactionResponse{
		TransactionId:                 txID,
		DebitBalanceAfterMinorUnits:   s.balances[debit],
		CreditBalanceAfterMinorUnits:  s.balances[credit],
	}, nil
}

func (s *Server) GetBalance(ctx context.Context, req *bankingv1.GetBalanceRequest) (*bankingv1.GetBalanceResponse, error) {
	_ = ctx
	id := strings.TrimSpace(req.GetAccountId())
	if id == "" {
		return nil, status.Error(codes.InvalidArgument, "account_id is required")
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	return &bankingv1.GetBalanceResponse{BalanceMinorUnits: s.balances[id]}, nil
}
