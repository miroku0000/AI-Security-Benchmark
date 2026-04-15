package bankingv1

import (
	reflect "reflect"
	sync "sync"

	"google.golang.org/protobuf/proto"
	protoreflect "google.golang.org/protobuf/reflect/protoreflect"
	protoimpl "google.golang.org/protobuf/runtime/protoimpl"
	descriptorpb "google.golang.org/protobuf/types/descriptorpb"
)

type CreateTransactionRequest struct {
	state         protoimpl.MessageState
	sizeCache     protoimpl.SizeCache
	unknownFields protoimpl.UnknownFields

	DebitAccountId   string `protobuf:"bytes,1,opt,name=debit_account_id,json=debitAccountId,proto3" json:"debit_account_id,omitempty"`
	CreditAccountId  string `protobuf:"bytes,2,opt,name=credit_account_id,json=creditAccountId,proto3" json:"credit_account_id,omitempty"`
	AmountMinorUnits int64  `protobuf:"varint,3,opt,name=amount_minor_units,json=amountMinorUnits,proto3" json:"amount_minor_units,omitempty"`
	Reference        string `protobuf:"bytes,4,opt,name=reference,proto3" json:"reference,omitempty"`
}

func (x *CreateTransactionRequest) Reset() {
	*x = CreateTransactionRequest{}
	if protoimpl.UnsafeEnabled {
		mi := &file_banking_v1_transaction_proto_msgTypes[0]
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		ms.StoreMessageInfo(mi)
	}
}
func (x *CreateTransactionRequest) String() string {
	return protoimpl.X.MessageStringOf(x)
}
func (*CreateTransactionRequest) ProtoMessage() {}
func (x *CreateTransactionRequest) ProtoReflect() protoreflect.Message {
	mi := &file_banking_v1_transaction_proto_msgTypes[0]
	if protoimpl.UnsafeEnabled && x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

func (*CreateTransactionRequest) Descriptor() ([]byte, []int) {
	return file_banking_v1_transaction_proto_rawDescGZIP(), []int{0}
}

func (x *CreateTransactionRequest) GetDebitAccountId() string {
	if x != nil {
		return x.DebitAccountId
	}
	return ""
}
func (x *CreateTransactionRequest) GetCreditAccountId() string {
	if x != nil {
		return x.CreditAccountId
	}
	return ""
}
func (x *CreateTransactionRequest) GetAmountMinorUnits() int64 {
	if x != nil {
		return x.AmountMinorUnits
	}
	return 0
}
func (x *CreateTransactionRequest) GetReference() string {
	if x != nil {
		return x.Reference
	}
	return ""
}

type CreateTransactionResponse struct {
	state         protoimpl.MessageState
	sizeCache     protoimpl.SizeCache
	unknownFields protoimpl.UnknownFields

	TransactionId                  string `protobuf:"bytes,1,opt,name=transaction_id,json=transactionId,proto3" json:"transaction_id,omitempty"`
	DebitBalanceAfterMinorUnits    int64  `protobuf:"varint,2,opt,name=debit_balance_after_minor_units,json=debitBalanceAfterMinorUnits,proto3" json:"debit_balance_after_minor_units,omitempty"`
	CreditBalanceAfterMinorUnits   int64  `protobuf:"varint,3,opt,name=credit_balance_after_minor_units,json=creditBalanceAfterMinorUnits,proto3" json:"credit_balance_after_minor_units,omitempty"`
}

func (x *CreateTransactionResponse) Reset() {
	*x = CreateTransactionResponse{}
	if protoimpl.UnsafeEnabled {
		mi := &file_banking_v1_transaction_proto_msgTypes[1]
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		ms.StoreMessageInfo(mi)
	}
}
func (x *CreateTransactionResponse) String() string {
	return protoimpl.X.MessageStringOf(x)
}
func (*CreateTransactionResponse) ProtoMessage() {}
func (x *CreateTransactionResponse) ProtoReflect() protoreflect.Message {
	mi := &file_banking_v1_transaction_proto_msgTypes[1]
	if protoimpl.UnsafeEnabled && x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

func (*CreateTransactionResponse) Descriptor() ([]byte, []int) {
	return file_banking_v1_transaction_proto_rawDescGZIP(), []int{1}
}

func (x *CreateTransactionResponse) GetTransactionId() string {
	if x != nil {
		return x.TransactionId
	}
	return ""
}
func (x *CreateTransactionResponse) GetDebitBalanceAfterMinorUnits() int64 {
	if x != nil {
		return x.DebitBalanceAfterMinorUnits
	}
	return 0
}
func (x *CreateTransactionResponse) GetCreditBalanceAfterMinorUnits() int64 {
	if x != nil {
		return x.CreditBalanceAfterMinorUnits
	}
	return 0
}

type GetBalanceRequest struct {
	state         protoimpl.MessageState
	sizeCache     protoimpl.SizeCache
	unknownFields protoimpl.UnknownFields

	AccountId string `protobuf:"bytes,1,opt,name=account_id,json=accountId,proto3" json:"account_id,omitempty"`
}

func (x *GetBalanceRequest) Reset() {
	*x = GetBalanceRequest{}
	if protoimpl.UnsafeEnabled {
		mi := &file_banking_v1_transaction_proto_msgTypes[2]
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		ms.StoreMessageInfo(mi)
	}
}
func (x *GetBalanceRequest) String() string {
	return protoimpl.X.MessageStringOf(x)
}
func (*GetBalanceRequest) ProtoMessage() {}
func (x *GetBalanceRequest) ProtoReflect() protoreflect.Message {
	mi := &file_banking_v1_transaction_proto_msgTypes[2]
	if protoimpl.UnsafeEnabled && x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

func (*GetBalanceRequest) Descriptor() ([]byte, []int) {
	return file_banking_v1_transaction_proto_rawDescGZIP(), []int{2}
}

func (x *GetBalanceRequest) GetAccountId() string {
	if x != nil {
		return x.AccountId
	}
	return ""
}

type GetBalanceResponse struct {
	state         protoimpl.MessageState
	sizeCache     protoimpl.SizeCache
	unknownFields protoimpl.UnknownFields

	BalanceMinorUnits int64 `protobuf:"varint,1,opt,name=balance_minor_units,json=balanceMinorUnits,proto3" json:"balance_minor_units,omitempty"`
}

func (x *GetBalanceResponse) Reset() {
	*x = GetBalanceResponse{}
	if protoimpl.UnsafeEnabled {
		mi := &file_banking_v1_transaction_proto_msgTypes[3]
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		ms.StoreMessageInfo(mi)
	}
}
func (x *GetBalanceResponse) String() string {
	return protoimpl.X.MessageStringOf(x)
}
func (*GetBalanceResponse) ProtoMessage() {}
func (x *GetBalanceResponse) ProtoReflect() protoreflect.Message {
	mi := &file_banking_v1_transaction_proto_msgTypes[3]
	if protoimpl.UnsafeEnabled && x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

func (*GetBalanceResponse) Descriptor() ([]byte, []int) {
	return file_banking_v1_transaction_proto_rawDescGZIP(), []int{3}
}

func (x *GetBalanceResponse) GetBalanceMinorUnits() int64 {
	if x != nil {
		return x.BalanceMinorUnits
	}
	return 0
}

var File_banking_v1_transaction_proto protoreflect.FileDescriptor

func buildFileDescriptorProto() *descriptorpb.FileDescriptorProto {
	return &descriptorpb.FileDescriptorProto{
		Name:    proto.String("banking/v1/transaction.proto"),
		Package: proto.String("banking.platform.v1"),
		Syntax:  proto.String("proto3"),
		MessageType: []*descriptorpb.DescriptorProto{
			{
				Name: proto.String("CreateTransactionRequest"),
				Field: []*descriptorpb.FieldDescriptorProto{
					{Name: proto.String("debit_account_id"), Number: proto.Int32(1), Label: descriptorpb.FieldDescriptorProto_LABEL_OPTIONAL.Enum(), Type: descriptorpb.FieldDescriptorProto_TYPE_STRING.Enum(), JsonName: proto.String("debitAccountId")},
					{Name: proto.String("credit_account_id"), Number: proto.Int32(2), Label: descriptorpb.FieldDescriptorProto_LABEL_OPTIONAL.Enum(), Type: descriptorpb.FieldDescriptorProto_TYPE_STRING.Enum(), JsonName: proto.String("creditAccountId")},
					{Name: proto.String("amount_minor_units"), Number: proto.Int32(3), Label: descriptorpb.FieldDescriptorProto_LABEL_OPTIONAL.Enum(), Type: descriptorpb.FieldDescriptorProto_TYPE_INT64.Enum(), JsonName: proto.String("amountMinorUnits")},
					{Name: proto.String("reference"), Number: proto.Int32(4), Label: descriptorpb.FieldDescriptorProto_LABEL_OPTIONAL.Enum(), Type: descriptorpb.FieldDescriptorProto_TYPE_STRING.Enum(), JsonName: proto.String("reference")},
				},
			},
			{
				Name: proto.String("CreateTransactionResponse"),
				Field: []*descriptorpb.FieldDescriptorProto{
					{Name: proto.String("transaction_id"), Number: proto.Int32(1), Label: descriptorpb.FieldDescriptorProto_LABEL_OPTIONAL.Enum(), Type: descriptorpb.FieldDescriptorProto_TYPE_STRING.Enum(), JsonName: proto.String("transactionId")},
					{Name: proto.String("debit_balance_after_minor_units"), Number: proto.Int32(2), Label: descriptorpb.FieldDescriptorProto_LABEL_OPTIONAL.Enum(), Type: descriptorpb.FieldDescriptorProto_TYPE_INT64.Enum(), JsonName: proto.String("debitBalanceAfterMinorUnits")},
					{Name: proto.String("credit_balance_after_minor_units"), Number: proto.Int32(3), Label: descriptorpb.FieldDescriptorProto_LABEL_OPTIONAL.Enum(), Type: descriptorpb.FieldDescriptorProto_TYPE_INT64.Enum(), JsonName: proto.String("creditBalanceAfterMinorUnits")},
				},
			},
			{
				Name: proto.String("GetBalanceRequest"),
				Field: []*descriptorpb.FieldDescriptorProto{
					{Name: proto.String("account_id"), Number: proto.Int32(1), Label: descriptorpb.FieldDescriptorProto_LABEL_OPTIONAL.Enum(), Type: descriptorpb.FieldDescriptorProto_TYPE_STRING.Enum(), JsonName: proto.String("accountId")},
				},
			},
			{
				Name: proto.String("GetBalanceResponse"),
				Field: []*descriptorpb.FieldDescriptorProto{
					{Name: proto.String("balance_minor_units"), Number: proto.Int32(1), Label: descriptorpb.FieldDescriptorProto_LABEL_OPTIONAL.Enum(), Type: descriptorpb.FieldDescriptorProto_TYPE_INT64.Enum(), JsonName: proto.String("balanceMinorUnits")},
				},
			},
		},
		Service: []*descriptorpb.ServiceDescriptorProto{
			{
				Name: proto.String("TransactionService"),
				Method: []*descriptorpb.MethodDescriptorProto{
					{
						Name:       proto.String("CreateTransaction"),
						InputType:  proto.String(".banking.platform.v1.CreateTransactionRequest"),
						OutputType: proto.String(".banking.platform.v1.CreateTransactionResponse"),
					},
					{
						Name:       proto.String("GetBalance"),
						InputType:  proto.String(".banking.platform.v1.GetBalanceRequest"),
						OutputType: proto.String(".banking.platform.v1.GetBalanceResponse"),
					},
				},
			},
		},
	}
}

var file_banking_v1_transaction_proto_rawDesc = mustMarshal(buildFileDescriptorProto())

func mustMarshal(m proto.Message) []byte {
	b, err := proto.Marshal(m)
	if err != nil {
		panic(err)
	}
	return b
}

var (
	file_banking_v1_transaction_proto_rawDescOnce sync.Once
	file_banking_v1_transaction_proto_rawDescData = file_banking_v1_transaction_proto_rawDesc
)

func file_banking_v1_transaction_proto_rawDescGZIP() []byte {
	file_banking_v1_transaction_proto_rawDescOnce.Do(func() {
		file_banking_v1_transaction_proto_rawDescData = protoimpl.X.CompressGZIP(file_banking_v1_transaction_proto_rawDescData)
	})
	return file_banking_v1_transaction_proto_rawDescData
}

var file_banking_v1_transaction_proto_msgTypes = make([]protoimpl.MessageInfo, 4)
var file_banking_v1_transaction_proto_goTypes = []any{
	(*CreateTransactionRequest)(nil),
	(*CreateTransactionResponse)(nil),
	(*GetBalanceRequest)(nil),
	(*GetBalanceResponse)(nil),
}
var file_banking_v1_transaction_proto_depIdxs = []int32{
	0, 0, 0,
	0, 2,
	1, 3,
	5, 3, 3, 3, 0,
}

func init() { file_banking_v1_transaction_proto_init() }
func file_banking_v1_transaction_proto_init() {
	if File_banking_v1_transaction_proto != nil {
		return
	}
	if !protoimpl.UnsafeEnabled {
		file_banking_v1_transaction_proto_msgTypes[0].Exporter = func(v any, i int) any {
			switch v := v.(*CreateTransactionRequest); i {
			case 0:
				return &v.state
			case 1:
				return &v.sizeCache
			case 2:
				return &v.unknownFields
			default:
				return nil
			}
		}
		file_banking_v1_transaction_proto_msgTypes[1].Exporter = func(v any, i int) any {
			switch v := v.(*CreateTransactionResponse); i {
			case 0:
				return &v.state
			case 1:
				return &v.sizeCache
			case 2:
				return &v.unknownFields
			default:
				return nil
			}
		}
		file_banking_v1_transaction_proto_msgTypes[2].Exporter = func(v any, i int) any {
			switch v := v.(*GetBalanceRequest); i {
			case 0:
				return &v.state
			case 1:
				return &v.sizeCache
			case 2:
				return &v.unknownFields
			default:
				return nil
			}
		}
		file_banking_v1_transaction_proto_msgTypes[3].Exporter = func(v any, i int) any {
			switch v := v.(*GetBalanceResponse); i {
			case 0:
				return &v.state
			case 1:
				return &v.sizeCache
			case 2:
				return &v.unknownFields
			default:
				return nil
			}
		}
	}
	type x struct{}
	out := protoimpl.TypeBuilder{
		File: protoimpl.DescBuilder{
			GoPackagePath: reflect.TypeOf(x{}).PkgPath(),
			RawDescriptor: file_banking_v1_transaction_proto_rawDesc,
			NumEnums:      0,
			NumMessages:   4,
			NumExtensions: 0,
			NumServices:   1,
		},
		GoTypes:           file_banking_v1_transaction_proto_goTypes,
		DependencyIndexes: file_banking_v1_transaction_proto_depIdxs,
		MessageInfos:      file_banking_v1_transaction_proto_msgTypes,
	}.Build()
	File_banking_v1_transaction_proto = out.File
	file_banking_v1_transaction_proto_rawDesc = nil
	file_banking_v1_transaction_proto_goTypes = nil
	file_banking_v1_transaction_proto_depIdxs = nil
}
