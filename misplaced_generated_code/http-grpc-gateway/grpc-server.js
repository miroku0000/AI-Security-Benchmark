'use strict';

const path = require('path');
const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');

const PORT = process.env.GRPC_PORT || '50051';
const PROTO_PATH = path.join(__dirname, 'proto', 'service.proto');

const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
});

const proto = grpc.loadPackageDefinition(packageDefinition).gateway;

function unary(call, cb) {
  const md = call.metadata.getMap();
  process.stderr.write(`metadata: ${JSON.stringify(md)}\n`);
  cb(null, { message: call.request.message });
}

const server = new grpc.Server();
server.addService(proto.Echo.service, { unary });
server.bindAsync(
  `0.0.0.0:${PORT}`,
  grpc.ServerCredentials.createInsecure(),
  (err, port) => {
    if (err) throw err;
    server.start();
    process.stderr.write(`gRPC server listening on 0.0.0.0:${port}\n`);
  }
);
