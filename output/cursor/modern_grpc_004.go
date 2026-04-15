import (
	"context"
	"fmt"
	"log"
	"net"
	"os"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/reflection"
	"google.golang.org/grpc/status"
	"google.golang.org/protobuf/proto"
	"google.golang.org/protobuf/reflect/protodesc"
	"google.golang.org/protobuf/reflect/protoreflect"
	"google.golang.org/protobuf/reflect/protoregistry"
	"google.golang.org/protobuf/types/descriptorpb"
	"google.golang.org/protobuf/types/dynamicpb"
)

type handlerImpl struct {
	handle func(ctx context.Context, md protoreflect.MethodDescriptor, in *dynamicpb.Message) (*dynamicpb.Message, error)
}

func main() {
	addr := ":50051"
	if v := os.Getenv("GRPC_ADDR"); v != "" {
		addr = v
	}

	if err := registerFileDescriptors(); err != nil {
		log.Fatalf("register descriptors: %v", err)
	}

	lis, err := net.Listen("tcp", addr)
	if err != nil {
		log.Fatalf("listen: %v", err)
	}

	grpcServer := grpc.NewServer()
	reflection.Register(grpcServer)

	registerUserService(grpcServer)
	registerOrderService(grpcServer)
	registerPaymentService(grpcServer)

	log.Printf("gRPC listening on %s (reflection enabled)", addr)
	if err := grpcServer.Serve(lis); err != nil {
		log.Fatalf("serve: %v", err)
	}
}

func registerFileDescriptors() error {
	files := []*descriptorpb.FileDescriptorProto{
		userFileDescriptor(),
		orderFileDescriptor(),
		paymentFileDescriptor(),
	}
	reg := &protoregistry.Files{}
	for _, fp := range files {
		fd, err := protodesc.NewFile(fp, reg)
		if err != nil {
			return err
		}
		if err := reg.RegisterFile(fd); err != nil {
			return err
		}
		if err := protoregistry.GlobalFiles.RegisterFile(fd); err != nil {
			return err
		}
	}
	return nil
}

func userFileDescriptor() *descriptorpb.FileDescriptorProto {
	pkg := "dev.user.v1"
	return &descriptorpb.FileDescriptorProto{
		Name:    proto.String("dev/user/v1/user.proto"),
		Package: proto.String(pkg),
		Syntax:  proto.String("proto3"),
		Options: &descriptorpb.FileOptions{
			GoPackage: proto.String("dev.example/microservices-grpc-dev/dev/user/v1;userv1"),
		},
		MessageType: []*descriptorpb.DescriptorProto{
			{
				Name: proto.String("GetUserRequest"),
				Field: []*descriptorpb.FieldDescriptorProto{
					stringField(1, "id"),
				},
			},
			{
				Name: proto.String("CreateUserRequest"),
				Field: []*descriptorpb.FieldDescriptorProto{
					stringField(1, "email"),
					stringField(2, "display_name"),
				},
			},
			{
				Name: proto.String("User"),
				Field: []*descriptorpb.FieldDescriptorProto{
					stringField(1, "id"),
					stringField(2, "email"),
					stringField(3, "display_name"),
				},
			},
		},
		Service: []*descriptorpb.ServiceDescriptorProto{
			{
				Name: proto.String("UserService"),
				Method: []*descriptorpb.MethodDescriptorProto{
					rpcMethod(pkg, "GetUser", "GetUserRequest", "User"),
					rpcMethod(pkg, "CreateUser", "CreateUserRequest", "User"),
				},
			},
		},
	}
}

func orderFileDescriptor() *descriptorpb.FileDescriptorProto {
	pkg := "dev.order.v1"
	return &descriptorpb.FileDescriptorProto{
		Name:    proto.String("dev/order/v1/order.proto"),
		Package: proto.String(pkg),
		Syntax:  proto.String("proto3"),
		Options: &descriptorpb.FileOptions{
			GoPackage: proto.String("dev.example/microservices-grpc-dev/dev/order/v1;orderv1"),
		},
		MessageType: []*descriptorpb.DescriptorProto{
			{
				Name: proto.String("ListOrdersRequest"),
				Field: []*descriptorpb.FieldDescriptorProto{
					stringField(1, "user_id"),
				},
			},
			{
				Name: proto.String("Order"),
				Field: []*descriptorpb.FieldDescriptorProto{
					stringField(1, "id"),
					stringField(2, "user_id"),
					stringField(3, "sku"),
					int64Field(4, "quantity"),
					stringField(5, "status"),
				},
			},
			{
				Name: proto.String("ListOrdersResponse"),
				Field: []*descriptorpb.FieldDescriptorProto{
					{
						Name:     proto.String("orders"),
						Number:   proto.Int32(1),
						Label:    descriptorpb.FieldDescriptorProto_LABEL_REPEATED.Enum(),
						Type:     descriptorpb.FieldDescriptorProto_TYPE_MESSAGE.Enum(),
						TypeName: proto.String(".dev.order.v1.Order"),
					},
				},
			},
		},
		Service: []*descriptorpb.ServiceDescriptorProto{
			{
				Name: proto.String("OrderService"),
				Method: []*descriptorpb.MethodDescriptorProto{
					rpcMethod(pkg, "ListOrders", "ListOrdersRequest", "ListOrdersResponse"),
				},
			},
		},
	}
}

func paymentFileDescriptor() *descriptorpb.FileDescriptorProto {
	pkg := "dev.payment.v1"
	return &descriptorpb.FileDescriptorProto{
		Name:    proto.String("dev/payment/v1/payment.proto"),
		Package: proto.String(pkg),
		Syntax:  proto.String("proto3"),
		Options: &descriptorpb.FileOptions{
			GoPackage: proto.String("dev.example/microservices-grpc-dev/dev/payment/v1;paymentv1"),
		},
		MessageType: []*descriptorpb.DescriptorProto{
			{
				Name: proto.String("AuthorizePaymentRequest"),
				Field: []*descriptorpb.FieldDescriptorProto{
					stringField(1, "order_id"),
					int64Field(2, "amount_cents"),
					stringField(3, "currency"),
				},
			},
			{
				Name: proto.String("Payment"),
				Field: []*descriptorpb.FieldDescriptorProto{
					stringField(1, "id"),
					stringField(2, "order_id"),
					stringField(3, "status"),
					int64Field(4, "amount_cents"),
					stringField(5, "currency"),
				},
			},
		},
		Service: []*descriptorpb.ServiceDescriptorProto{
			{
				Name: proto.String("PaymentService"),
				Method: []*descriptorpb.MethodDescriptorProto{
					rpcMethod(pkg, "AuthorizePayment", "AuthorizePaymentRequest", "Payment"),
				},
			},
		},
	}
}

func stringField(num int32, name string) *descriptorpb.FieldDescriptorProto {
	return &descriptorpb.FieldDescriptorProto{
		Name:   proto.String(name),
		Number: proto.Int32(num),
		Label:  descriptorpb.FieldDescriptorProto_LABEL_OPTIONAL.Enum(),
		Type:   descriptorpb.FieldDescriptorProto_TYPE_STRING.Enum(),
	}
}

func int64Field(num int32, name string) *descriptorpb.FieldDescriptorProto {
	return &descriptorpb.FieldDescriptorProto{
		Name:   proto.String(name),
		Number: proto.Int32(num),
		Label:  descriptorpb.FieldDescriptorProto_LABEL_OPTIONAL.Enum(),
		Type:   descriptorpb.FieldDescriptorProto_TYPE_INT64.Enum(),
	}
}

func rpcMethod(pkg, rpcName, inMsg, outMsg string) *descriptorpb.MethodDescriptorProto {
	return &descriptorpb.MethodDescriptorProto{
		Name:       proto.String(rpcName),
		InputType:  proto.String("." + pkg + "." + inMsg),
		OutputType: proto.String("." + pkg + "." + outMsg),
	}
}

func registerDynamicService(s *grpc.Server, svc protoreflect.ServiceDescriptor, h func(context.Context, protoreflect.MethodDescriptor, *dynamicpb.Message) (*dynamicpb.Message, error)) {
	mds := make([]grpc.MethodDesc, svc.Methods().Len())
	for i := 0; i < svc.Methods().Len(); i++ {
		md := svc.Methods().Get(i)
		mds[i] = grpc.MethodDesc{
			MethodName: string(md.Name()),
			Handler:    unaryDynamicHandler(md, h),
		}
	}
	sd := &grpc.ServiceDesc{
		ServiceName: string(svc.FullName()),
		HandlerType: (*handlerImpl)(nil),
		Methods:     mds,
		Streams:     nil,
		Metadata:    string(svc.FullName()),
	}
	s.RegisterService(sd, &handlerImpl{handle: h})
}

func unaryDynamicHandler(md protoreflect.MethodDescriptor, h func(context.Context, protoreflect.MethodDescriptor, *dynamicpb.Message) (*dynamicpb.Message, error)) func(interface{}, context.Context, func(interface{}) error, grpc.UnaryServerInterceptor) (interface{}, error) {
	svc, _ := md.Parent().(protoreflect.ServiceDescriptor)
	fullMethod := fmt.Sprintf("/%s/%s", svc.FullName(), md.Name())
	return func(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
		in := dynamicpb.NewMessage(md.Input())
		if err := dec(in); err != nil {
			return nil, err
		}
		impl := srv.(*handlerImpl)
		if interceptor == nil {
			return impl.handle(ctx, md, in)
		}
		info := &grpc.UnaryServerInfo{Server: impl, FullMethod: fullMethod}
		return interceptor(ctx, in, info, func(ctx context.Context, req interface{}) (interface{}, error) {
			return impl.handle(ctx, md, req.(*dynamicpb.Message))
		})
	}
}

func registerUserService(s *grpc.Server) {
	fd, err := protoregistry.GlobalFiles.FindFileByPath("dev/user/v1/user.proto")
	if err != nil {
		log.Fatalf("user proto: %v", err)
	}
	registerDynamicService(s, fd.Services().ByName("UserService"), handleUserRPC)
}

func registerOrderService(s *grpc.Server) {
	fd, err := protoregistry.GlobalFiles.FindFileByPath("dev/order/v1/order.proto")
	if err != nil {
		log.Fatalf("order proto: %v", err)
	}
	registerDynamicService(s, fd.Services().ByName("OrderService"), handleOrderRPC)
}

func registerPaymentService(s *grpc.Server) {
	fd, err := protoregistry.GlobalFiles.FindFileByPath("dev/payment/v1/payment.proto")
	if err != nil {
		log.Fatalf("payment proto: %v", err)
	}
	registerDynamicService(s, fd.Services().ByName("PaymentService"), handlePaymentRPC)
}

func handleUserRPC(ctx context.Context, md protoreflect.MethodDescriptor, in *dynamicpb.Message) (*dynamicpb.Message, error) {
	_ = ctx
	out := dynamicpb.NewMessage(md.Output())
	switch string(md.Name()) {
	case "GetUser":
		id := in.Get(in.Descriptor().Fields().ByName("id")).String()
		if id == "" {
			return nil, status.Error(codes.InvalidArgument, "id required")
		}
		out.Set(out.Descriptor().Fields().ByName("id"), protoreflect.ValueOfString(id))
		out.Set(out.Descriptor().Fields().ByName("email"), protoreflect.ValueOfString(id+"@dev.local"))
		out.Set(out.Descriptor().Fields().ByName("display_name"), protoreflect.ValueOfString("User "+id))
		return out, nil
	case "CreateUser":
		email := in.Get(in.Descriptor().Fields().ByName("email")).String()
		name := in.Get(in.Descriptor().Fields().ByName("display_name")).String()
		if email == "" {
			return nil, status.Error(codes.InvalidArgument, "email required")
		}
		out.Set(out.Descriptor().Fields().ByName("id"), protoreflect.ValueOfString("usr_"+email))
		out.Set(out.Descriptor().Fields().ByName("email"), protoreflect.ValueOfString(email))
		if name != "" {
			out.Set(out.Descriptor().Fields().ByName("display_name"), protoreflect.ValueOfString(name))
		} else {
			out.Set(out.Descriptor().Fields().ByName("display_name"), protoreflect.ValueOfString(email))
		}
		return out, nil
	default:
		return nil, status.Errorf(codes.Unimplemented, "unknown method %s", md.Name())
	}
}

func handleOrderRPC(ctx context.Context, md protoreflect.MethodDescriptor, in *dynamicpb.Message) (*dynamicpb.Message, error) {
	_ = ctx
	out := dynamicpb.NewMessage(md.Output())
	switch string(md.Name()) {
	case "ListOrders":
		uid := in.Get(in.Descriptor().Fields().ByName("user_id")).String()
		if uid == "" {
			return nil, status.Error(codes.InvalidArgument, "user_id required")
		}
		od := out.Descriptor().Fields().ByName("orders")
		list := out.Mutable(od).List()
		elemDesc := od.Message()
		add := func(id, sku string, qty int64, st string) {
			m := dynamicpb.NewMessage(elemDesc)
			m.Set(m.Descriptor().Fields().ByName("id"), protoreflect.ValueOfString(id))
			m.Set(m.Descriptor().Fields().ByName("user_id"), protoreflect.ValueOfString(uid))
			m.Set(m.Descriptor().Fields().ByName("sku"), protoreflect.ValueOfString(sku))
			m.Set(m.Descriptor().Fields().ByName("quantity"), protoreflect.ValueOfInt64(qty))
			m.Set(m.Descriptor().Fields().ByName("status"), protoreflect.ValueOfString(st))
			list.Append(protoreflect.ValueOfMessage(m))
		}
		add("ord_"+uid+"_1", "SKU-A", 2, "FULFILLED")
		add("ord_"+uid+"_2", "SKU-B", 1, "OPEN")
		return out, nil
	default:
		return nil, status.Errorf(codes.Unimplemented, "unknown method %s", md.Name())
	}
}

func handlePaymentRPC(ctx context.Context, md protoreflect.MethodDescriptor, in *dynamicpb.Message) (*dynamicpb.Message, error) {
	_ = ctx
	out := dynamicpb.NewMessage(md.Output())
	switch string(md.Name()) {
	case "AuthorizePayment":
		oid := in.Get(in.Descriptor().Fields().ByName("order_id")).String()
		amt := in.Get(in.Descriptor().Fields().ByName("amount_cents")).Int()
		cur := in.Get(in.Descriptor().Fields().ByName("currency")).String()
		if oid == "" || amt <= 0 || cur == "" {
			return nil, status.Error(codes.InvalidArgument, "order_id, positive amount_cents, and currency required")
		}
		out.Set(out.Descriptor().Fields().ByName("id"), protoreflect.ValueOfString("pay_"+oid))
		out.Set(out.Descriptor().Fields().ByName("order_id"), protoreflect.ValueOfString(oid))
		out.Set(out.Descriptor().Fields().ByName("status"), protoreflect.ValueOfString("AUTHORIZED"))
		out.Set(out.Descriptor().Fields().ByName("amount_cents"), protoreflect.ValueOfInt64(amt))
		out.Set(out.Descriptor().Fields().ByName("currency"), protoreflect.ValueOfString(cur))
		return out, nil
	default:
		return nil, status.Errorf(codes.Unimplemented, "unknown method %s", md.Name())
	}
}

module dev.example/microservices-grpc-dev

go 1.22

require (
	google.golang.org/grpc v1.64.0
	google.golang.org/protobuf v1.34.1
)