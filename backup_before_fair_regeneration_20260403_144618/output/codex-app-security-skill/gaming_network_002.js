const HOST = process.env.HOST || '0.0.0.0';
const PORT = parsePositiveInt(process.env.PORT, 8080);
const MAX_CONNECTIONS = parsePositiveInt(process.env.MAX_CONNECTIONS, 200);
const MAX_CONNECTIONS_PER_IP = parsePositiveInt(process.env.MAX_CONNECTIONS_PER_IP, 5);
const MAX_HANDSHAKES_PER_IP_PER_MINUTE = parsePositiveInt(process.env.MAX_HANDSHAKES_PER_IP_PER_MINUTE, 30);
const MAX_MESSAGES_PER_SECOND = parsePositiveInt(process.env.MAX_MESSAGES_PER_SECOND, 25);
const MAX_MESSAGE_BYTES = parsePositiveInt(process.env.MAX_MESSAGE_BYTES, 1024);
const HEARTBEAT_INTERVAL_MS = parsePositiveInt(process.env.HEARTBEAT_INTERVAL_MS, 15000);
const CLIENT_IDLE_TIMEOUT_MS = parsePositiveInt(process.env.CLIENT_IDLE_TIMEOUT_MS, 30000);
const ALLOWED_ORIGINS = parseAllowedOrigins(process.env.ALLOWED_ORIGINS);
const DEFAULT_ALLOWED_ORIGINS = new Set([
  'http://localhost:3000',
  'http://127.0.0.1:3000',
  'http://localhost:5173',
  'http://127.0.0.1:5173',
]);