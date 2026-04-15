func initDescriptors() error {
	fdp := &descriptorpb.FileDescriptorProto{
		Name:    strPtr("transactions.proto"),
		Package: strPtr("banking.v1"),
		Syntax:  strPtr("proto3"),
		MessageType: []*descriptorpb.DescriptorProto{
			{
				Name: strPtr("CreateTransactionRequest"),
				Field: []*descriptorpb.FieldDescriptorProto{
					newStringField("transaction_id", 1),
					newStringField("from_account_id", 2),
					newStringField("to_account_id", 3),
					newInt64Field("amount_minor", 4),
					newStringField("currency", 5),
					newStringField("idempotency_key", 6),
				},
			},
			{
				Name: strPtr("CreateTransactionResponse"),
				Field: []*descriptorpb.FieldDescriptorProto{
					newStringField("transaction_id", 1),
					newStringField("status", 2),
					newInt64Field("from_balance_minor", 3),
					newInt64Field("to_balance_minor", 4),
				},
			},
			{
				Name: strPtr("GetBalanceRequest"),
				Field: []*descriptorpb.FieldDescriptorProto{
					newStringField("account_id", 1),
					newStringField("currency", 2),
				},
			},
			{
				Name: strPtr("GetBalanceResponse"),
				Field: []*descriptorpb.FieldDescriptorProto{
					newStringField("account_id", 1),
					newStringField("currency", 2),
					newInt64Field("balance_minor", 3),
				},
			},
		},
		Service: []*descriptorpb.ServiceDescriptorProto{
			{
				Name: strPtr("TransactionService"),
				Method: []*descriptorpb.MethodDescriptorProto{
					{
						Name:       strPtr("CreateTransaction"),
						InputType:  strPtr(".banking.v1.CreateTransactionRequest"),
						OutputType: strPtr(".banking.v1.CreateTransactionResponse"),
					},
					{
						Name:       strPtr("GetBalance"),
						InputType:  strPtr(".banking.v1.GetBalanceRequest"),
						OutputType: strPtr(".banking.v1.GetBalanceResponse"),
					},
				},
			},
		},
	}