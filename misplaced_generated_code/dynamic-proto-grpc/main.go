package main

import (
	"bytes"
	"context"
	"fmt"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/jhump/protoreflect/desc/protoparse"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
	"google.golang.org/protobuf/reflect/protodesc"
	"google.golang.org/protobuf/reflect/protoreflect"
	"google.golang.org/protobuf/types/descriptorpb"
	"google.golang.org/protobuf/types/dynamicpb"
)

const embeddedServiceProto = `syntax = "proto3";

package dynamiccompiler.v1;

option go_package = "github.com/example/dynamic-proto-grpc/pb;pb";

service DynamicProtoCompiler {
  rpc CompileProto(CompileProtoRequest) returns (CompileProtoResponse);
}

message CompileProtoRequest {
  string filename = 1;
  string proto_source = 2;
  repeated string import_paths = 3;
  repeated string protoc_extra_args = 4;
}

message CompileProtoResponse {
  bool ok = 1;
  int32 exit_code = 2;
  string stdout = 3;
  string stderr = 4;
  bytes file_descriptor_set = 5;
}
`

const fullMethodCompileProto = "/dynamiccompiler.v1.DynamicProtoCompiler/CompileProto"

type DynamicProtoCompilerServer interface {
	CompileProto(context.Context, *dynamicpb.Message) (*dynamicpb.Message, error)
}

type compilerServer struct {
	outputDesc protoreflect.MessageDescriptor
}

func (s *compilerServer) CompileProto(ctx context.Context, in *dynamicpb.Message) (*dynamicpb.Message, error) {
	protoSrc := stringField(in, "proto_source")
	if strings.TrimSpace(protoSrc) == "" {
		return nil, status.Error(codes.InvalidArgument, "proto_source is required")
	}
	name := strings.TrimSpace(stringField(in, "filename"))
	base := filepath.Base(name)
	if base == "" || base == "." {
		base = "user.proto"
	}
	if !strings.HasSuffix(strings.ToLower(base), ".proto") {
		return nil, status.Error(codes.InvalidArgument, "filename must end with .proto")
	}
	if base != filepath.Clean(base) || strings.Contains(base, "..") {
		return nil, status.Error(codes.InvalidArgument, "invalid filename")
	}

	tmpDir, err := os.MkdirTemp("", "dynproto-*")
	if err != nil {
		return nil, status.Errorf(codes.Internal, "mkdir temp: %v", err)
	}
	defer os.RemoveAll(tmpDir)

	protoPath := filepath.Join(tmpDir, base)
	if err := os.WriteFile(protoPath, []byte(protoSrc), 0o600); err != nil {
		return nil, status.Errorf(codes.Internal, "write proto: %v", err)
	}

	outPath := filepath.Join(tmpDir, "descriptor.pb")
	protocBin := os.Getenv("PROTOC")
	if protocBin == "" {
		protocBin = "protoc"
	}

	args := []string{"-I", tmpDir}
	for _, p := range repeatedStringField(in, "import_paths") {
		p = strings.TrimSpace(p)
		if p == "" {
			continue
		}
		args = append(args, "-I", p)
	}
	for _, a := range repeatedStringField(in, "protoc_extra_args") {
		args = append(args, a)
	}
	args = append(args,
		"--descriptor_set_out="+outPath,
		"--include_imports",
		base,
	)

	var stdout, stderr bytes.Buffer
	cmd := exec.CommandContext(ctx, protocBin, args...)
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	runErr := cmd.Run()

	exitCode := int32(0)
	if runErr != nil {
		if x, ok := runErr.(*exec.ExitError); ok {
			exitCode = int32(x.ExitCode())
		} else {
			exitCode = -1
		}
	}

	out := dynamicpb.NewMessage(s.outputDesc)
	setBool(out, "ok", runErr == nil)
	setInt32(out, "exit_code", exitCode)
	setString(out, "stdout", stdout.String())
	setString(out, "stderr", stderr.String())

	if runErr == nil {
		data, err := os.ReadFile(outPath)
		if err != nil {
			setBool(out, "ok", false)
			setInt32(out, "exit_code", -1)
			setString(out, "stderr", stderr.String()+"\nread descriptor: "+err.Error())
		} else {
			setBytes(out, "file_descriptor_set", data)
		}
	}

	return out, nil
}

func stringField(m *dynamicpb.Message, name string) string {
	fd := m.Descriptor().Fields().ByName(name)
	if fd == nil {
		return ""
	}
	return m.Get(fd).String()
}

func repeatedStringField(m *dynamicpb.Message, name string) []string {
	fd := m.Descriptor().Fields().ByName(name)
	if fd == nil {
		return nil
	}
	list := m.Get(fd).List()
	out := make([]string, list.Len())
	for i := 0; i < list.Len(); i++ {
		out[i] = list.Get(i).String()
	}
	return out
}

func setBool(m *dynamicpb.Message, name string, v bool) {
	fd := m.Descriptor().Fields().ByName(name)
	if fd != nil {
		m.Set(fd, protoreflect.ValueOfBool(v))
	}
}

func setInt32(m *dynamicpb.Message, name string, v int32) {
	fd := m.Descriptor().Fields().ByName(name)
	if fd != nil {
		m.Set(fd, protoreflect.ValueOfInt32(v))
	}
}

func setString(m *dynamicpb.Message, name string, v string) {
	fd := m.Descriptor().Fields().ByName(name)
	if fd != nil {
		m.Set(fd, protoreflect.ValueOfString(v))
	}
}

func setBytes(m *dynamicpb.Message, name string, v []byte) {
	fd := m.Descriptor().Fields().ByName(name)
	if fd != nil {
		m.Set(fd, protoreflect.ValueOfBytes(v))
	}
}

func mustLoadServiceFileDescriptor() protoreflect.FileDescriptor {
	parser := protoparse.Parser{
		Accessor: protoparse.FileContentsFromMap(map[string]string{
			"dynamic_compiler.proto": embeddedServiceProto,
		}),
	}
	fds, err := parser.ParseFiles("dynamic_compiler.proto")
	if err != nil {
		panic(err)
	}
	if len(fds) == 0 {
		panic("no file descriptors")
	}
	files, err := protodesc.NewFiles(&descriptorpb.FileDescriptorSet{
		File: []*descriptorpb.FileDescriptorProto{fds[0].AsProto()},
	})
	if err != nil {
		panic(err)
	}
	fd, err := files.FindFileByPath(fds[0].GetName())
	if err != nil {
		panic(err)
	}
	return fd
}

func registerDynamicProtoCompilerServer(s grpc.ServiceRegistrar, srv DynamicProtoCompilerServer, fd protoreflect.FileDescriptor) {
	svc := fd.Services().ByName("DynamicProtoCompiler")
	if svc == nil {
		panic("service DynamicProtoCompiler not found")
	}
	meth := svc.Methods().ByName("CompileProto")
	if meth == nil {
		panic("method CompileProto not found")
	}
	inDesc := meth.Input()

	handler := func(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
		in := dynamicpb.NewMessage(inDesc)
		if err := dec(in); err != nil {
			return nil, err
		}
		if interceptor == nil {
			return srv.(DynamicProtoCompilerServer).CompileProto(ctx, in)
		}
		info := &grpc.UnaryServerInfo{
			Server:     srv,
			FullMethod: fullMethodCompileProto,
		}
		h := func(ctx context.Context, req interface{}) (interface{}, error) {
			return srv.(DynamicProtoCompilerServer).CompileProto(ctx, req.(*dynamicpb.Message))
		}
		return interceptor(ctx, in, info, h)
	}

	s.RegisterService(&grpc.ServiceDesc{
		ServiceName: "dynamiccompiler.v1.DynamicProtoCompiler",
		HandlerType: (*compilerServer)(nil),
		Methods: []grpc.MethodDesc{
			{
				MethodName: "CompileProto",
				Handler:    handler,
			},
		},
		Streams:  []grpc.StreamDesc{},
		Metadata: "dynamic_compiler.proto",
	}, srv)
}

func main() {
	fd := mustLoadServiceFileDescriptor()
	svc := fd.Services().ByName("DynamicProtoCompiler")
	meth := svc.Methods().ByName("CompileProto")
	impl := &compilerServer{outputDesc: meth.Output()}

	lis, err := net.Listen("tcp", ":50051")
	if err != nil {
		panic(err)
	}
	s := grpc.NewServer()
	registerDynamicProtoCompilerServer(s, impl, fd)
	fmt.Fprintf(os.Stderr, "listening %s\n", lis.Addr().String())
	if err := s.Serve(lis); err != nil {
		panic(err)
	}
}
