package main

import (
	"log"
	"net"

	"google.golang.org/grpc"

	bankingv1 "example.com/banking/platform/api/banking/v1"
	"example.com/banking/platform/internal/transaction"
)

func main() {
	lis, err := net.Listen("tcp", ":50051")
	if err != nil {
		log.Fatalf("listen: %v", err)
	}
	s := grpc.NewServer()
	bankingv1.RegisterTransactionServiceServer(s, transaction.NewServer())
	log.Printf("transaction gRPC listening on %s", lis.Addr().String())
	if err := s.Serve(lis); err != nil {
		log.Fatalf("serve: %v", err)
	}
}
