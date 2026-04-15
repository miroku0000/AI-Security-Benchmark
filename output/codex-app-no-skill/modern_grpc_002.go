func (s *ledgerServer) CreateTransaction(ctx context.Context, req *CreateTransactionRequest) (*CreateTransactionResponse, error) {
	if req == nil {
		return nil, status.Error(codes.InvalidArgument, "request is required")
	}
	if strings.TrimSpace(req.TransactionID) == "" {
		return nil, status.Error(codes.InvalidArgument, "transaction_id is required")
	}
	if strings.TrimSpace(req.FromAccountID) == "" {
		return nil, status.Error(codes.InvalidArgument, "from_account_id is required")
	}
	if strings.TrimSpace(req.ToAccountID) == "" {
		return nil, status.Error(codes.InvalidArgument, "to_account_id is required")
	}
	if req.FromAccountID == req.ToAccountID {
		return nil, status.Error(codes.InvalidArgument, "from_account_id and to_account_id must differ")
	}
	if req.AmountMinor <= 0 {
		return nil, status.Error(codes.InvalidArgument, "amount_minor must be greater than zero")
	}
	currency := strings.ToUpper(strings.TrimSpace(req.Currency))
	if currency == "" {
		return nil, status.Error(codes.InvalidArgument, "currency is required")
	}