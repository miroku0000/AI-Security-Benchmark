const PORT = Number(process.env.PORT || 3000);
const GRPC_TARGET = process.env.GRPC_TARGET || 'localhost:50051';
const PROTO_PATH = process.env.PROTO_PATH || './service.proto';
const PROTO_PACKAGE = process.env.PROTO_PACKAGE || '';
const GRPC_SERVICE = process.env.GRPC_SERVICE || 'BackendService';
const GRPC_METHOD = process.env.GRPC_METHOD || 'Handle';