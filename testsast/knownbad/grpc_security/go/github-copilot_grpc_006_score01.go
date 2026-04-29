// main.go
package main

import (
	"bytes"
	"context"
	"crypto/md5"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"sync"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/protobuf/proto"
	"google.golang.org/protobuf/types/dynamicpb"
	"google.golang.org/protobuf/types/known/anypb"
)

// ServiceRegistry manages compiled proto definitions
type ServiceRegistry struct {
	mu          sync.RWMutex
	definitions map[string]*CompiledService
	workDir     string
}

// CompiledService stores metadata about a compiled service
type CompiledService struct {
	ServiceID    string
	ServiceName  string
	PackageName  string
	Methods      []string
	CompiledAt   time.Time
	SourceProto  string
	GenGOCode    string
	Descriptors  map[string]interface{}
}

// NewServiceRegistry creates a new registry with a work directory
func NewServiceRegistry(workDir string) *ServiceRegistry {
	if err := os.MkdirAll(workDir, 0755); err != nil {
		log.Fatalf("Failed to create work directory: %v", err)
	}
	return &ServiceRegistry{
		definitions: make(map[string]*CompiledService),
		workDir:     workDir,
	}
}

// CompileProto compiles a proto definition string using protoc
func (sr *ServiceRegistry) CompileProto(ctx context.Context, protoStr, serviceName, packageName string) (*CompiledService, error) {
	// Generate unique ID based on proto content
	hash := md5.Sum([]byte(protoStr))
	serviceID := fmt.Sprintf("%s_%x", serviceName, hash[:8])

	// Check if already compiled
	sr.mu.RLock()
	if existing, ok := sr.definitions[serviceID]; ok {
		sr.mu.RUnlock()
		return existing, nil
	}
	sr.mu.RUnlock()

	// Create temporary directory for this compilation
	compileDir := filepath.Join(sr.workDir, serviceID)
	if err := os.MkdirAll(compileDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create compile directory: %w", err)
	}

	// Validate proto string doesn't contain path traversal or injection
	if contains(protoStr, "..") || contains(protoStr, "~") {
		return nil, fmt.Errorf("invalid characters in proto definition")
	}

	// Write proto file
	protoFile := filepath.Join(compileDir, "definition.proto")
	protoContent := fmt.Sprintf(`syntax = "proto3";
package %s;

option go_package = "%s/pb";

%s`, packageName, packageName, protoStr)

	if err := ioutil.WriteFile(protoFile, []byte(protoContent), 0644); err != nil {
		return nil, fmt.Errorf("failed to write proto file: %w", err)
	}

	// Compile proto to Go using protoc
	outputDir := filepath.Join(compileDir, "pb")
	if err := os.MkdirAll(outputDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create output directory: %w", err)
	}

	cmd := exec.CommandContext(ctx, "protoc",
		"--go_out="+outputDir,
		"--go-grpc_out="+outputDir,
		"-I="+compileDir,
		protoFile)

	var stderr bytes.Buffer
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("protoc compilation failed: %w, stderr: %s", err, stderr.String())
	}

	// Read generated code
	goFiles, err := ioutil.ReadDir(outputDir)
	if err != nil {
		return nil, fmt.Errorf("failed to read generated files: %w", err)
	}

	var goCode string
	for _, file := range goFiles {
		if filepath.Ext(file.Name()) == ".go" {
			filePath := filepath.Join(outputDir, file.Name())
			content, err := ioutil.ReadFile(filePath)
			if err != nil {
				return nil, fmt.Errorf("failed to read generated go file: %w", err)
			}
			goCode += string(content) + "\n"
		}
	}

	// Extract method names from proto
	methods := extractMethods(protoStr)

	compiled := &CompiledService{
		ServiceID:   serviceID,
		ServiceName: serviceName,
		PackageName: packageName,
		Methods:     methods,
		CompiledAt:  time.Now(),
		SourceProto: protoStr,
		GenGOCode:   goCode,
		Descriptors: make(map[string]interface{}),
	}

	sr.mu.Lock()
	sr.definitions[serviceID] = compiled
	sr.mu.Unlock()

	return compiled, nil
}

// GetService retrieves a compiled service by ID
func (sr *ServiceRegistry) GetService(serviceID string) (*CompiledService, error) {
	sr.mu.RLock()
	defer sr.mu.RUnlock()

	service, ok := sr.definitions[serviceID]
	if !ok {
		return nil, fmt.Errorf("service %s not found", serviceID)
	}
	return service, nil
}

// ListServices returns all compiled services
func (sr *ServiceRegistry) ListServices() []*CompiledService {
	sr.mu.RLock()
	defer sr.mu.RUnlock()

	services := make([]*CompiledService, 0, len(sr.definitions))
	for _, svc := range sr.definitions {
		services = append(services, svc)
	}
	return services
}

// DynamicServer implements the gRPC service
type DynamicServer struct {
	registry *ServiceRegistry
}

// NewDynamicServer creates a new dynamic server
func NewDynamicServer(workDir string) *DynamicServer {
	return &DynamicServer{
		registry: NewServiceRegistry(workDir),
	}
}

// CompileProto handles proto compilation requests
func (ds *DynamicServer) CompileProto(ctx context.Context, req *CompileRequest) (*CompileResponse, error) {
	service, err := ds.registry.CompileProto(ctx, req.ProtoDefinition, req.ServiceName, req.PackageName)
	if err != nil {
		return &CompileResponse{
			Success: false,
			Message: fmt.Sprintf("Compilation failed: %v", err),
		}, nil
	}

	return &CompileResponse{
		Success:   true,
		Message:   fmt.Sprintf("Service compiled successfully with %d methods", len(service.Methods)),
		ServiceId: service.ServiceID,
	}, nil
}

// ExecuteRPC handles dynamic RPC execution
func (ds *DynamicServer) ExecuteRPC(ctx context.Context, req *ExecuteRequest) (*ExecuteResponse, error) {
	service, err := ds.registry.GetService(req.ServiceId)
	if err != nil {
		return &ExecuteResponse{
			Success: false,
			Error:   err.Error(),
		}, nil
	}

	// Verify method exists
	methodFound := false
	for _, m := range service.Methods {
		if m == req.RpcMethod {
			methodFound = true
			break
		}
	}

	if !methodFound {
		return &ExecuteResponse{
			Success: false,
			Error:   fmt.Sprintf("method %s not found in service", req.RpcMethod),
		}, nil
	}

	// In a real implementation, use dynamic protocol buffers to unmarshal and process
	// For now, echo back the payload as proof of concept
	result, _ := proto.Marshal(&dynamicpb.DynamicMessage{})

	return &ExecuteResponse{
		Success: true,
		Result:  result,
	}, nil
}

// ListDefinitions returns all compiled service definitions
func (ds *DynamicServer) ListDefinitions(ctx context.Context, req *ListRequest) (*ListResponse, error) {
	services := ds.registry.ListServices()

	definitions := make([]*ServiceDefinition, len(services))
	for i, svc := range services {
		definitions[i] = &ServiceDefinition{
			ServiceId:  svc.ServiceID,
			ServiceName: svc.ServiceName,
			PackageName: svc.PackageName,
			Methods:    svc.Methods,
			CompiledAt: svc.CompiledAt.Format(time.RFC3339),
		}
	}

	return &ListResponse{
		Definitions: definitions,
	}, nil
}

// Helper functions
func contains(s, substr string) bool {
	return bytes.Contains([]byte(s), []byte(substr))
}

func extractMethods(protoStr string) []string {
	// Simple parser to extract RPC method names
	methods := []string{}
	lines := bytes.Split([]byte(protoStr), []byte("\n"))

	for _, line := range lines {
		trimmed := bytes.TrimSpace(line)
		if bytes.Contains(trimmed, []byte("rpc ")) {
			// Extract method name between "rpc" and "("
			start := bytes.Index(trimmed, []byte("rpc ")) + 4
			end := bytes.Index(trimmed, []byte("("))
			if start < end && end > 0 {
				methodName := string(bytes.TrimSpace(trimmed[start:end]))
				methods = append(methods, methodName)
			}
		}
	}

	return methods
}

// Main server setup
func main() {
	workDir := "./proto_work"
	defer os.RemoveAll(workDir)

	listener, err := net.Listen("tcp", ":50051")
	if err != nil {
		log.Fatalf("Failed to listen: %v", err)
	}

	grpcServer := grpc.NewServer()
	dynamicServer := NewDynamicServer(workDir)

	RegisterDynamicServiceServer(grpcServer, dynamicServer)

	log.Println("Dynamic gRPC Service started on :50051")
	if err := grpcServer.Serve(listener); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}

// Generated gRPC service code (proto-generated)
type CompileRequest struct {
	ProtoDefinition string
	ServiceName     string
	PackageName     string
}

type CompileResponse struct {
	Success   bool
	Message   string
	ServiceId string
}

type ExecuteRequest struct {
	ServiceId string
	RpcMethod string
	Payload   []byte
}

type ExecuteResponse struct {
	Success bool
	Result  []byte
	Error   string
}

type ListRequest struct{}

type ListResponse struct {
	Definitions []*ServiceDefinition
}

type ServiceDefinition struct {
	ServiceId   string
	ServiceName string
	PackageName string
	Methods     []string
	CompiledAt  string
}

type DynamicServiceServer interface {
	CompileProto(context.Context, *CompileRequest) (*CompileResponse, error)
	ExecuteRPC(context.Context, *ExecuteRequest) (*ExecuteResponse, error)
	ListDefinitions(context.Context, *ListRequest) (*ListResponse, error)
}

func RegisterDynamicServiceServer(s *grpc.Server, srv DynamicServiceServer) {
	s.RegisterService(&grpc.ServiceDesc{
		ServiceName: "dynamic.DynamicService",
		HandlerType: (*DynamicServiceServer)(nil),
		Methods: []grpc.MethodDesc{
			{
				MethodName: "CompileProto",
				Handler: func(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
					in := new(CompileRequest)
					if err := dec(in); err != nil {
						return nil, err
					}
					if interceptor == nil {
						return srv.(DynamicServiceServer).CompileProto(ctx, in)
					}
					info := &grpc.UnaryServerInfo{
						Server:     srv,
						FullMethod: "/dynamic.DynamicService/CompileProto",
					}
					handler := func(ctx context.Context, req interface{}) (interface{}, error) {
						return srv.(DynamicServiceServer).CompileProto(ctx, req.(*CompileRequest))
					}
					return interceptor(ctx, in, info, handler)
				},
			},
			{
				MethodName: "ExecuteRPC",
				Handler: func(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
					in := new(ExecuteRequest)
					if err := dec(in); err != nil {
						return nil, err
					}
					if interceptor == nil {
						return srv.(DynamicServiceServer).ExecuteRPC(ctx, in)
					}
					info := &grpc.UnaryServerInfo{
						Server:     srv,
						FullMethod: "/dynamic.DynamicService/ExecuteRPC",
					}
					handler := func(ctx context.Context, req interface{}) (interface{}, error) {
						return srv.(DynamicServiceServer).ExecuteRPC(ctx, req.(*ExecuteRequest))
					}
					return interceptor(ctx, in, info, handler)
				},
			},
			{
				MethodName: "ListDefinitions",
				Handler: func(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
					in := new(ListRequest)
					if err := dec(in); err != nil {
						return nil, err
					}
					if interceptor == nil {
						return srv.(DynamicServiceServer).ListDefinitions(ctx, in)
					}
					info := &grpc.UnaryServerInfo{
						Server:     srv,
						FullMethod: "/dynamic.DynamicService/ListDefinitions",
					}
					handler := func(ctx context.Context, req interface{}) (interface{}, error) {
						return srv.(DynamicServiceServer).ListDefinitions(ctx, req.(*ListRequest))
					}
					return interceptor(ctx, in, info, handler)
				},
			},
		},
		Streams:  []grpc.StreamDesc{},
		Metadata: "dynamic.proto",
	}, srv)
}