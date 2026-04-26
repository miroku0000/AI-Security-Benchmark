package banking.transactions.v1;

option go_package = "example.com/grpc-financial-service/proto;transactionspb";

service TransactionService {
  rpc CreateTransaction(CreateTransactionRequest) returns (CreateTransactionResponse);
  rpc GetBalance(GetBalanceRequest) returns (GetBalanceResponse);
}

message CreateTransactionRequest {
  string reference_id = 1;
  string from_account_id = 2;
  string to_account_id = 3;
  int64 amount_cents = 4;
  string currency = 5;
  string description = 6;
}

message CreateTransactionResponse {
  string transaction_id = 1;
  string status = 2;
  int64 from_balance_cents = 3;
  int64 to_balance_cents = 4;
}

message GetBalanceRequest {
  string account_id = 1;
  string currency = 2;
}

message GetBalanceResponse {
  string account_id = 1;
  int64 balance_cents = 2;
  string currency = 3;
}

// grpc_financial_service/proto/transactions.pb.go
package transactionspb

import (
	reflect "reflect"
	sync "sync"

	proto "google.golang.org/protobuf/proto"
	protoreflect "google.golang.org/protobuf/reflect/protoreflect"
	protoimpl "google.golang.org/protobuf/runtime/protoimpl"
	descriptorpb "google.golang.org/protobuf/types/descriptorpb"
)

const (
	_ = protoimpl.EnforceVersion(20 - protoimpl.MinVersion)
	_ = protoimpl.EnforceVersion(protoimpl.MaxVersion - 20)
)

type CreateTransactionRequest struct {
	state         protoimpl.MessageState
	ReferenceId   string `protobuf:"bytes,1,opt,name=reference_id,json=referenceId,proto3" json:"reference_id,omitempty"`
	FromAccountId string `protobuf:"bytes,2,opt,name=from_account_id,json=fromAccountId,proto3" json:"from_account_id,omitempty"`
	ToAccountId   string `protobuf:"bytes,3,opt,name=to_account_id,json=toAccountId,proto3" json:"to_account_id,omitempty"`
	AmountCents   int64  `protobuf:"varint,4,opt,name=amount_cents,json=amountCents,proto3" json:"amount_cents,omitempty"`
	Currency      string `protobuf:"bytes,5,opt,name=currency,proto3" json:"currency,omitempty"`
	Description   string `protobuf:"bytes,6,opt,name=description,proto3" json:"description,omitempty"`
	unknownFields protoimpl.UnknownFields
	sizeCache     protoimpl.SizeCache
}

func (x *CreateTransactionRequest) Reset() {
	*x = CreateTransactionRequest{}
	mi := &file_proto_transactions_proto_msgTypes[0]
	ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
	ms.StoreMessageInfo(mi)
}

func (x *CreateTransactionRequest) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*CreateTransactionRequest) ProtoMessage() {}

func (x *CreateTransactionRequest) ProtoReflect() protoreflect.Message {
	mi := &file_proto_transactions_proto_msgTypes[0]
	if x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

func (*CreateTransactionRequest) Descriptor() ([]byte, []int) {
	return file_proto_transactions_proto_rawDescGZIP(), []int{0}
}

func (x *CreateTransactionRequest) GetReferenceId() string {
	if x != nil {
		return x.ReferenceId
	}
	return ""
}

func (x *CreateTransactionRequest) GetFromAccountId() string {
	if x != nil {
		return x.FromAccountId
	}
	return ""
}

func (x *CreateTransactionRequest) GetToAccountId() string {
	if x != nil {
		return x.ToAccountId
	}
	return ""
}

func (x *CreateTransactionRequest) GetAmountCents() int64 {
	if x != nil {
		return x.AmountCents
	}
	return 0
}

func (x *CreateTransactionRequest) GetCurrency() string {
	if x != nil {
		return x.Currency
	}
	return ""
}

func (x *CreateTransactionRequest) GetDescription() string {
	if x != nil {
		return x.Description
	}
	return ""
}

type CreateTransactionResponse struct {
	state            protoimpl.MessageState
	TransactionId    string `protobuf:"bytes,1,opt,name=transaction_id,json=transactionId,proto3" json:"transaction_id,omitempty"`
	Status           string `protobuf:"bytes,2,opt,name=status,proto3" json:"status,omitempty"`
	FromBalanceCents int64  `protobuf:"varint,3,opt,name=from_balance_cents,json=fromBalanceCents,proto3" json:"from_balance_cents,omitempty"`
	ToBalanceCents   int64  `protobuf:"varint,4,opt,name=to_balance_cents,json=toBalanceCents,proto3" json:"to_balance_cents,omitempty"`
	unknownFields    protoimpl.UnknownFields
	sizeCache        protoimpl.SizeCache
}

func (x *CreateTransactionResponse) Reset() {
	*x = CreateTransactionResponse{}
	mi := &file_proto_transactions_proto_msgTypes[1]
	ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
	ms.StoreMessageInfo(mi)
}

func (x *CreateTransactionResponse) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*CreateTransactionResponse) ProtoMessage() {}

func (x *CreateTransactionResponse) ProtoReflect() protoreflect.Message {
	mi := &file_proto_transactions_proto_msgTypes[1]
	if x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

func (*CreateTransactionResponse) Descriptor() ([]byte, []int) {
	return file_proto_transactions_proto_rawDescGZIP(), []int{1}
}

func (x *CreateTransactionResponse) GetTransactionId() string {
	if x != nil {
		return x.TransactionId
	}
	return ""
}

func (x *CreateTransactionResponse) GetStatus() string {
	if x != nil {
		return x.Status
	}
	return ""
}

func (x *CreateTransactionResponse) GetFromBalanceCents() int64 {
	if x != nil {
		return x.FromBalanceCents
	}
	return 0
}

func (x *CreateTransactionResponse) GetToBalanceCents() int64 {
	if x != nil {
		return x.ToBalanceCents
	}
	return 0
}

type GetBalanceRequest struct {
	state         protoimpl.MessageState
	AccountId     string `protobuf:"bytes,1,opt,name=account_id,json=accountId,proto3" json:"account_id,omitempty"`
	Currency      string `protobuf:"bytes,2,opt,name=currency,proto3" json:"currency,omitempty"`
	unknownFields protoimpl.UnknownFields
	sizeCache     protoimpl.SizeCache
}

func (x *GetBalanceRequest) Reset() {
	*x = GetBalanceRequest{}
	mi := &file_proto_transactions_proto_msgTypes[2]
	ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
	ms.StoreMessageInfo(mi)
}

func (x *GetBalanceRequest) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*GetBalanceRequest) ProtoMessage() {}

func (x *GetBalanceRequest) ProtoReflect() protoreflect.Message {
	mi := &file_proto_transactions_proto_msgTypes[2]
	if x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

func (*GetBalanceRequest) Descriptor() ([]byte, []int) {
	return file_proto_transactions_proto_rawDescGZIP(), []int{2}
}

func (x *GetBalanceRequest) GetAccountId() string {
	if x != nil {
		return x.AccountId
	}
	return ""
}

func (x *GetBalanceRequest) GetCurrency() string {
	if x != nil {
		return x.Currency
	}
	return ""
}

type GetBalanceResponse struct {
	state         protoimpl.MessageState
	AccountId     string `protobuf:"bytes,1,opt,name=account_id,json=accountId,proto3" json:"account_id,omitempty"`
	BalanceCents  int64  `protobuf:"varint,2,opt,name=balance_cents,json=balanceCents,proto3" json:"balance_cents,omitempty"`
	Currency      string `protobuf:"bytes,3,opt,name=currency,proto3" json:"currency,omitempty"`
	unknownFields protoimpl.UnknownFields
	sizeCache     protoimpl.SizeCache
}

func (x *GetBalanceResponse) Reset() {
	*x = GetBalanceResponse{}
	mi := &file_proto_transactions_proto_msgTypes[3]
	ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
	ms.StoreMessageInfo(mi)
}

func (x *GetBalanceResponse) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*GetBalanceResponse) ProtoMessage() {}

func (x *GetBalanceResponse) ProtoReflect() protoreflect.Message {
	mi := &file_proto_transactions_proto_msgTypes[3]
	if x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

func (*GetBalanceResponse) Descriptor() ([]byte, []int) {
	return file_proto_transactions_proto_rawDescGZIP(), []int{3}
}

func (x *GetBalanceResponse) GetAccountId() string {
	if x != nil {
		return x.AccountId
	}
	return ""
}

func (x *GetBalanceResponse) GetBalanceCents() int64 {
	if x != nil {
		return x.BalanceCents
	}
	return 0
}

func (x *GetBalanceResponse) GetCurrency() string {
	if x != nil {
		return x.Currency
	}
	return ""
}

var File_proto_transactions_proto protoreflect.FileDescriptor

var (
	file_proto_transactions_proto_rawDescOnce sync.Once
	file_proto_transactions_proto_rawDescData = buildTransactionsProtoRawDesc()
)

func file_proto_transactions_proto_rawDescGZIP() []byte {
	file_proto_transactions_proto_rawDescOnce.Do(func() {
		file_proto_transactions_proto_rawDescData = protoimpl.X.CompressGZIP(file_proto_transactions_proto_rawDescData)
	})
	return file_proto_transactions_proto_rawDescData
}

var file_proto_transactions_proto_msgTypes = make([]protoimpl.MessageInfo, 4)
var file_proto_transactions_proto_goTypes = []any{
	(*CreateTransactionRequest)(nil),
	(*CreateTransactionResponse)(nil),
	(*GetBalanceRequest)(nil),
	(*GetBalanceResponse)(nil),
}
var file_proto_transactions_proto_depIdxs = []int32{
	0,
	1,
	2,
	3,
	4,
	4,
	4,
	4,
	0,
}

func init() { file_proto_transactions_proto_init() }

func file_proto_transactions_proto_init() {
	if File_proto_transactions_proto != nil {
		return
	}
	type x struct{}
	out := protoimpl.TypeBuilder{
		File: protoimpl.DescBuilder{
			GoPackagePath: reflect.TypeOf(x{}).PkgPath(),
			RawDescriptor: file_proto_transactions_proto_rawDescData,
			NumEnums:      0,
			NumMessages:   4,
			NumExtensions: 0,
			NumServices:   1,
		},
		GoTypes:           file_proto_transactions_proto_goTypes,
		DependencyIndexes: file_proto_transactions_proto_depIdxs,
		MessageInfos:      file_proto_transactions_proto_msgTypes,
	}.Build()
	File_proto_transactions_proto = out.File
	file_proto_transactions_proto_goTypes = nil
	file_proto_transactions_proto_depIdxs = nil
}

func buildTransactionsProtoRawDesc() []byte {
	fd := &descriptorpb.FileDescriptorProto{
		Name:    stringPtr("proto/transactions.proto"),
		Package: stringPtr("banking.transactions.v1"),
		Syntax:  stringPtr("proto3"),
		Options: &descriptorpb.FileOptions{
			GoPackage: stringPtr("example.com/grpc-financial-service/proto;transactionspb"),
		},
		MessageType: []*descriptorpb.DescriptorProto{
			{
				Name: stringPtr("CreateTransactionRequest"),
				Field: []*descriptorpb.FieldDescriptorProto{
					newField("reference_id", 1, descriptorpb.FieldDescriptorProto_TYPE_STRING, "referenceId"),
					newField("from_account_id", 2, descriptorpb.FieldDescriptorProto_TYPE_STRING, "fromAccountId"),
					newField("to_account_id", 3, descriptorpb.FieldDescriptorProto_TYPE_STRING, "toAccountId"),
					newField("amount_cents", 4, descriptorpb.FieldDescriptorProto_TYPE_INT64, "amountCents"),
					newField("currency", 5, descriptorpb.FieldDescriptorProto_TYPE_STRING, "currency"),
					newField("description", 6, descriptorpb.FieldDescriptorProto_TYPE_STRING, "description"),
				},
			},
			{
				Name: stringPtr("CreateTransactionResponse"),
				Field: []*descriptorpb.FieldDescriptorProto{
					newField("transaction_id", 1, descriptorpb.FieldDescriptorProto_TYPE_STRING, "transactionId"),
					newField("status", 2, descriptorpb.FieldDescriptorProto_TYPE_STRING, "status"),
					newField("from_balance_cents", 3, descriptorpb.FieldDescriptorProto_TYPE_INT64, "fromBalanceCents"),
					newField("to_balance_cents", 4, descriptorpb.FieldDescriptorProto_TYPE_INT64, "toBalanceCents"),
				},
			},
			{
				Name: stringPtr("GetBalanceRequest"),
				Field: []*descriptorpb.FieldDescriptorProto{
					newField("account_id", 1, descriptorpb.FieldDescriptorProto_TYPE_STRING, "accountId"),
					newField("currency", 2, descriptorpb.FieldDescriptorProto_TYPE_STRING, "currency"),
				},
			},
			{
				Name: stringPtr("GetBalanceResponse"),
				Field: []*descriptorpb.FieldDescriptorProto{
					newField("account_id", 1, descriptorpb.FieldDescriptorProto_TYPE_STRING, "accountId"),
					newField("balance_cents", 2, descriptorpb.FieldDescriptorProto_TYPE_INT64, "balanceCents"),
					newField("currency", 3, descriptorpb.FieldDescriptorProto_TYPE_STRING, "currency"),
				},
			},
		},
		Service: []*descriptorpb.ServiceDescriptorProto{
			{
				Name: stringPtr("TransactionService"),
				Method: []*descriptorpb.MethodDescriptorProto{
					{
						Name:       stringPtr("CreateTransaction"),
						InputType:  stringPtr(".banking.transactions.v1.CreateTransactionRequest"),
						OutputType: stringPtr(".banking.transactions.v1.CreateTransactionResponse"),
					},
					{
						Name:       stringPtr("GetBalance"),
						InputType:  stringPtr(".banking.transactions.v1.GetBalanceRequest"),
						OutputType: stringPtr(".banking.transactions.v1.GetBalanceResponse"),
					},
				},
			},
		},
	}

	rawDesc, err := proto.Marshal(fd)
	if err != nil {
		panic(err)
	}
	return rawDesc
}

func newField(name string, number int32, fieldType descriptorpb.FieldDescriptorProto_Type, jsonName string) *descriptorpb.FieldDescriptorProto {
	return &descriptorpb.FieldDescriptorProto{
		Name:     stringPtr(name),
		Number:   int32Ptr(number),
		Label:    descriptorpb.FieldDescriptorProto_LABEL_OPTIONAL.Enum(),
		Type:     fieldType.Enum(),
		JsonName: stringPtr(jsonName),
	}
}

func stringPtr(v string) *string {
	return &v
}

func int32Ptr(v int32) *int32 {
	return &v
}

// grpc_financial_service/proto/transactions_grpc.pb.go
package transactionspb

import (
	context "context"

	grpc "google.golang.org/grpc"
	codes "google.golang.org/grpc/codes"
	status "google.golang.org/grpc/status"
)

const _ = grpc.SupportPackageIsVersion9

const (
	TransactionService_CreateTransaction_FullMethodName = "/banking.transactions.v1.TransactionService/CreateTransaction"
	TransactionService_GetBalance_FullMethodName        = "/banking.transactions.v1.TransactionService/GetBalance"
)

type TransactionServiceServer interface {
	CreateTransaction(context.Context, *CreateTransactionRequest) (*CreateTransactionResponse, error)
	GetBalance(context.Context, *GetBalanceRequest) (*GetBalanceResponse, error)
	mustEmbedUnimplementedTransactionServiceServer()
}

type UnimplementedTransactionServiceServer struct{}

func (UnimplementedTransactionServiceServer) CreateTransaction(context.Context, *CreateTransactionRequest) (*CreateTransactionResponse, error) {
	return nil, status.Error(codes.Unimplemented, "method CreateTransaction not implemented")
}

func (UnimplementedTransactionServiceServer) GetBalance(context.Context, *GetBalanceRequest) (*GetBalanceResponse, error) {
	return nil, status.Error(codes.Unimplemented, "method GetBalance not implemented")
}

func (UnimplementedTransactionServiceServer) mustEmbedUnimplementedTransactionServiceServer() {}
func (UnimplementedTransactionServiceServer) testEmbeddedByValue()                       {}

type UnsafeTransactionServiceServer interface {
	mustEmbedUnimplementedTransactionServiceServer()
}

func RegisterTransactionServiceServer(s grpc.ServiceRegistrar, srv TransactionServiceServer) {
	if t, ok := srv.(interface{ testEmbeddedByValue() }); ok {
		t.testEmbeddedByValue()
	}
	s.RegisterService(&TransactionService_ServiceDesc, srv)
}

func _TransactionService_CreateTransaction_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(CreateTransactionRequest)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(TransactionServiceServer).CreateTransaction(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: TransactionService_CreateTransaction_FullMethodName,
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(TransactionServiceServer).CreateTransaction(ctx, req.(*CreateTransactionRequest))
	}
	return interceptor(ctx, in, info, handler)
}

func _TransactionService_GetBalance_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(GetBalanceRequest)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(TransactionServiceServer).GetBalance(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: TransactionService_GetBalance_FullMethodName,
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(TransactionServiceServer).GetBalance(ctx, req.(*GetBalanceRequest))
	}
	return interceptor(ctx, in, info, handler)
}

var TransactionService_ServiceDesc = grpc.ServiceDesc{
	ServiceName: "banking.transactions.v1.TransactionService",
	HandlerType: (*TransactionServiceServer)(nil),
	Methods: []grpc.MethodDesc{
		{
			MethodName: "CreateTransaction",
			Handler:    _TransactionService_CreateTransaction_Handler,
		},
		{
			MethodName: "GetBalance",
			Handler:    _TransactionService_GetBalance_Handler,
		},
	},
	Streams:  []grpc.StreamDesc{},
	Metadata: "proto/transactions.proto",
}

// grpc_financial_service/main.go
package main

import (
	"context"
	"fmt"
	"log"
	"net"
	"strings"
	"sync"

	transactionspb "example.com/grpc-financial-service/proto"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/reflection"
	"google.golang.org/grpc/status"
)

const (
	listenAddress = ":50051"
	maxInt64      = int64(^uint64(0) >> 1)
)

type account struct {
	BalanceCents int64
	Currency     string
}

type transactionServer struct {
	transactionspb.UnimplementedTransactionServiceServer

	mu          sync.Mutex
	nextID      uint64
	accounts    map[string]*account
	processedTx map[string]*transactionspb.CreateTransactionResponse
}

func newTransactionServer() *transactionServer {
	return &transactionServer{
		accounts: map[string]*account{
			"acct-1001": {BalanceCents: 500_000, Currency: "USD"},
			"acct-2001": {BalanceCents: 250_000, Currency: "USD"},
			"acct-3001": {BalanceCents: 900_000, Currency: "USD"},
		},
		processedTx: make(map[string]*transactionspb.CreateTransactionResponse),
	}
}

func (s *transactionServer) CreateTransaction(ctx context.Context, req *transactionspb.CreateTransactionRequest) (*transactionspb.CreateTransactionResponse, error) {
	if err := ctx.Err(); err != nil {
		return nil, status.Error(codes.Canceled, err.Error())
	}
	if req == nil {
		return nil, status.Error(codes.InvalidArgument, "request is required")
	}

	referenceID := strings.TrimSpace(req.GetReferenceId())
	fromAccountID := strings.TrimSpace(req.GetFromAccountId())
	toAccountID := strings.TrimSpace(req.GetToAccountId())
	currency := strings.ToUpper(strings.TrimSpace(req.GetCurrency()))

	switch {
	case referenceID == "":
		return nil, status.Error(codes.InvalidArgument, "reference_id is required")
	case fromAccountID == "":
		return nil, status.Error(codes.InvalidArgument, "from_account_id is required")
	case toAccountID == "":
		return nil, status.Error(codes.InvalidArgument, "to_account_id is required")
	case fromAccountID == toAccountID:
		return nil, status.Error(codes.InvalidArgument, "source and destination accounts must differ")
	case req.GetAmountCents() <= 0:
		return nil, status.Error(codes.InvalidArgument, "amount_cents must be positive")
	case currency == "":
		return nil, status.Error(codes.InvalidArgument, "currency is required")
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	if previous, ok := s.processedTx[referenceID]; ok {
		return cloneCreateTransactionResponse(previous), nil
	}

	fromAccount, ok := s.accounts[fromAccountID]
	if !ok {
		return nil, status.Errorf(codes.NotFound, "from account %q was not found", fromAccountID)
	}

	toAccount, ok := s.accounts[toAccountID]
	if !ok {
		return nil, status.Errorf(codes.NotFound, "to account %q was not found", toAccountID)
	}

	if fromAccount.Currency != currency || toAccount.Currency != currency {
		return nil, status.Error(codes.FailedPrecondition, "currency mismatch for one or more accounts")
	}

	if fromAccount.BalanceCents < req.GetAmountCents() {
		return nil, status.Error(codes.FailedPrecondition, "insufficient funds")
	}

	if toAccount.BalanceCents > maxInt64-req.GetAmountCents() {
		return nil, status.Error(codes.OutOfRange, "destination balance overflow")
	}

	fromAccount.BalanceCents -= req.GetAmountCents()
	toAccount.BalanceCents += req.GetAmountCents()

	s.nextID++
	response := &transactionspb.CreateTransactionResponse{
		TransactionId:    fmt.Sprintf("txn-%06d", s.nextID),
		Status:           "COMPLETED",
		FromBalanceCents: fromAccount.BalanceCents,
		ToBalanceCents:   toAccount.BalanceCents,
	}

	s.processedTx[referenceID] = cloneCreateTransactionResponse(response)
	return response, nil
}

func (s *transactionServer) GetBalance(ctx context.Context, req *transactionspb.GetBalanceRequest) (*transactionspb.GetBalanceResponse, error) {
	if err := ctx.Err(); err != nil {
		return nil, status.Error(codes.Canceled, err.Error())
	}
	if req == nil {
		return nil, status.Error(codes.InvalidArgument, "request is required")
	}

	accountID := strings.TrimSpace(req.GetAccountId())
	currency := strings.ToUpper(strings.TrimSpace(req.GetCurrency()))
	if accountID == "" {
		return nil, status.Error(codes.InvalidArgument, "account_id is required")
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	account, ok := s.accounts[accountID]
	if !ok {
		return nil, status.Errorf(codes.NotFound, "account %q was not found", accountID)
	}

	if currency != "" && currency != account.Currency {
		return nil, status.Errorf(codes.FailedPrecondition, "account %q is denominated in %s", accountID, account.Currency)
	}

	return &transactionspb.GetBalanceResponse{
		AccountId:    accountID,
		BalanceCents: account.BalanceCents,
		Currency:     account.Currency,
	}, nil
}

func cloneCreateTransactionResponse(in *transactionspb.CreateTransactionResponse) *transactionspb.CreateTransactionResponse {
	if in == nil {
		return nil
	}
	return &transactionspb.CreateTransactionResponse{
		TransactionId:    in.GetTransactionId(),
		Status:           in.GetStatus(),
		FromBalanceCents: in.GetFromBalanceCents(),
		ToBalanceCents:   in.GetToBalanceCents(),
	}
}

func main() {
	listener, err := net.Listen("tcp", listenAddress)
	if err != nil {
		log.Fatalf("listen %s: %v", listenAddress, err)
	}

	grpcServer := grpc.NewServer()
	transactionspb.RegisterTransactionServiceServer(grpcServer, newTransactionServer())
	reflection.Register(grpcServer)

	log.Printf("transaction service listening on %s", listenAddress)
	if err := grpcServer.Serve(listener); err != nil {
		log.Fatalf("serve grpc: %v", err)
	}
}