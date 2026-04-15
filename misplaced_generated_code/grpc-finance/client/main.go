package main

import (
	"context"
	"log"
	"time"

	pb "grpc-finance/proto"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/credentials/insecure"
)

func main() {
	var opts []grpc.DialOption

	creds, err := credentials.NewClientTLSFromFile("certs/server.crt", "")
	if err != nil {
		log.Printf("WARNING: TLS cert not found, connecting WITHOUT TLS. (%v)", err)
		opts = append(opts, grpc.WithTransportCredentials(insecure.NewCredentials()))
	} else {
		opts = append(opts, grpc.WithTransportCredentials(creds))
	}

	conn, err := grpc.NewClient("localhost:50051", opts...)
	if err != nil {
		log.Fatalf("failed to connect: %v", err)
	}
	defer conn.Close()

	client := pb.NewTransactionServiceClient(conn)
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	// Check initial balances
	bal, err := client.GetBalance(ctx, &pb.GetBalanceRequest{AccountId: "acct-001"})
	if err != nil {
		log.Fatalf("GetBalance failed: %v", err)
	}
	log.Printf("acct-001 balance: %d %s", bal.BalanceCents, bal.Currency)

	bal, err = client.GetBalance(ctx, &pb.GetBalanceRequest{AccountId: "acct-002"})
	if err != nil {
		log.Fatalf("GetBalance failed: %v", err)
	}
	log.Printf("acct-002 balance: %d %s", bal.BalanceCents, bal.Currency)

	// Create a transaction
	txnResp, err := client.CreateTransaction(ctx, &pb.CreateTransactionRequest{
		FromAccountId:  "acct-001",
		ToAccountId:    "acct-002",
		AmountCents:    10000,
		Currency:       "USD",
		IdempotencyKey: "test-key-001",
	})
	if err != nil {
		log.Fatalf("CreateTransaction failed: %v", err)
	}
	log.Printf("Transaction created: id=%s status=%s", txnResp.TransactionId, txnResp.Status)

	// Check balances after transaction
	bal, err = client.GetBalance(ctx, &pb.GetBalanceRequest{AccountId: "acct-001"})
	if err != nil {
		log.Fatalf("GetBalance failed: %v", err)
	}
	log.Printf("acct-001 balance after: %d %s", bal.BalanceCents, bal.Currency)

	bal, err = client.GetBalance(ctx, &pb.GetBalanceRequest{AccountId: "acct-002"})
	if err != nil {
		log.Fatalf("GetBalance failed: %v", err)
	}
	log.Printf("acct-002 balance after: %d %s", bal.BalanceCents, bal.Currency)
}
