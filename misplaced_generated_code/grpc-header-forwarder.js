const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const http = require('http');
const url = require('url');

const GRPC_SERVER_ADDRESS = process.env.GRPC_SERVER_ADDRESS || 'localhost:50051';
const HTTP_PORT = process.env.HTTP_PORT || 3000;
const PROTO_PATH = process.env.PROTO_PATH || './service.proto';

const BLOCKED_HEADERS = new Set([
  'host',
  'connection',
  'keep-alive',
  'transfer-encoding',
  'te',
  'trailer',
  'upgrade',
  'proxy-authorization',
  'proxy-authenticate',
]);

const ALLOWED_HEADER_PATTERN = /^[a-zA-Z0-9\-]+$/;
const MAX_HEADER_VALUE_LENGTH = 8192;

function sanitizeHeaderValue(value) {
  if (typeof value !== 'string') {
    value = String(value);
  }
  if (value.length > MAX_HEADER_VALUE_LENGTH) {
    value = value.substring(0, MAX_HEADER_VALUE_LENGTH);
  }
  return value.replace(/[\r\n\0]/g, '');
}

function buildGrpcMetadata(httpHeaders) {
  const metadata = new grpc.Metadata();

  for (const [key, value] of Object.entries(httpHeaders)) {
    const lowerKey = key.toLowerCase();

    if (BLOCKED_HEADERS.has(lowerKey)) {
      continue;
    }

    if (!ALLOWED_HEADER_PATTERN.test(key)) {
      continue;
    }

    const values = Array.isArray(value) ? value : [value];
    for (const v of values) {
      const sanitized = sanitizeHeaderValue(v);
      if (sanitized.length > 0) {
        metadata.add(lowerKey, sanitized);
      }
    }
  }

  return metadata;
}

function createGrpcClient(protoPath, packageName, serviceName) {
  const packageDefinition = protoLoader.loadSync(protoPath, {
    keepCase: true,
    longs: String,
    enums: String,
    defaults: true,
    oneofs: true,
  });

  const proto = grpc.loadPackageDefinition(packageDefinition);
  const ServiceClient = packageName
    ? proto[packageName][serviceName]
    : proto[serviceName];

  return new ServiceClient(
    GRPC_SERVER_ADDRESS,
    grpc.credentials.createInsecure()
  );
}

function forwardToGrpc(client, method, requestBody, metadata) {
  return new Promise((resolve, reject) => {
    if (typeof client[method] !== 'function') {
      reject(new Error(`Unknown gRPC method: ${method}`));
      return;
    }

    client[method](requestBody, metadata, (error, response) => {
      if (error) {
        reject(error);
      } else {
        resolve(response);
      }
    });
  });
}

const server = http.createServer(async (req, res) => {
  if (req.method !== 'POST') {
    res.writeHead(405, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Method not allowed' }));
    return;
  }

  const parsed = url.parse(req.url, true);
  const pathParts = parsed.pathname.replace(/^\/+|\/+$/g, '').split('/');

  if (pathParts.length < 2) {
    res.writeHead(400, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'URL must be /{service}/{method}' }));
    return;
  }

  const serviceName = pathParts[0];
  const methodName = pathParts[1];
  const packageName = parsed.query.package || '';

  let body = '';
  req.on('data', (chunk) => {
    body += chunk;
    if (body.length > 1e6) {
      req.destroy();
    }
  });

  req.on('end', async () => {
    let requestBody;
    try {
      requestBody = JSON.parse(body || '{}');
    } catch {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Invalid JSON body' }));
      return;
    }

    const metadata = buildGrpcMetadata(req.headers);

    try {
      const client = createGrpcClient(PROTO_PATH, packageName, serviceName);
      const response = await forwardToGrpc(client, methodName, requestBody, metadata);

      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(response));

      client.close();
    } catch (error) {
      const status = error.code ? 502 : 500;
      res.writeHead(status, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        error: error.message,
        grpcCode: error.code,
      }));
    }
  });
});

server.listen(HTTP_PORT, () => {
  console.log(`HTTP-to-gRPC gateway listening on port ${HTTP_PORT}`);
  console.log(`Forwarding to gRPC server at ${GRPC_SERVER_ADDRESS}`);
});
