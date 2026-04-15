const http = require('http');
const path = require('path');
const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');

const GRPC_TARGET = process.env.GRPC_TARGET || '127.0.0.1:50051';
const HTTP_PORT = Number(process.env.HTTP_PORT || 8080);
const PROTO_PATH = path.join(__dirname, 'proto', 'service.proto');

const HOP_BY_HOP = new Set([
  'connection',
  'keep-alive',
  'proxy-connection',
  'transfer-encoding',
  'upgrade',
  'http2-settings',
  'te',
  'trailer',
  'content-length',
]);

function httpHeadersToGrpcMetadata(headers) {
  const metadata = new grpc.Metadata();
  for (const [rawKey, rawVal] of Object.entries(headers)) {
    const key = rawKey.toLowerCase();
    if (HOP_BY_HOP.has(key)) continue;
    if (rawVal === undefined || rawVal === null) continue;
    const values = Array.isArray(rawVal) ? rawVal : [rawVal];
    for (const v of values) {
      if (v === undefined || v === null) continue;
      const s = Buffer.isBuffer(v) ? v.toString('utf8') : String(v);
      metadata.add(key, s);
    }
  }
  return metadata;
}

const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
});

const proto = grpc.loadPackageDefinition(packageDefinition).gateway;
const client = new proto.Echo(GRPC_TARGET, grpc.credentials.createInsecure());

const server = http.createServer((req, res) => {
  if (req.method !== 'POST' || req.url !== '/echo') {
    res.statusCode = 404;
    res.end();
    return;
  }

  const chunks = [];
  req.on('data', (c) => chunks.push(c));
  req.on('end', () => {
    let body = {};
    try {
      body = JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}');
    } catch {
      res.statusCode = 400;
      res.setHeader('content-type', 'application/json');
      res.end(JSON.stringify({ error: 'invalid json' }));
      return;
    }

    const metadata = httpHeadersToGrpcMetadata(req.headers);
    const message = typeof body.message === 'string' ? body.message : '';

    client.unary({ message }, metadata, (err, reply) => {
      if (err) {
        res.statusCode = 502;
        res.setHeader('content-type', 'application/json');
        res.end(JSON.stringify({ error: err.message, code: err.code }));
        return;
      }
      res.statusCode = 200;
      res.setHeader('content-type', 'application/json');
      res.end(JSON.stringify({ message: reply.message }));
    });
  });
});

server.listen(HTTP_PORT, () => {
  process.stderr.write(
    `HTTP gateway listening on :${HTTP_PORT} -> gRPC ${GRPC_TARGET}\n`
  );
});

`</think>`
The runnable files live under `http-grpc-gateway/` (`package.json`, `proto/service.proto`, `gateway.js`). Per your request, the answer body is only the raw code above (save `package.json` and `proto/service.proto` in the right paths, then `gateway.js`).