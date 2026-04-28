import * as http from 'node:http';
import { URL } from 'node:url';
import * as jwt from 'jsonwebtoken';

type SupportedAlgorithm = 'HS256';

interface AuthServiceConfig {
  port: number;
  secret: string;
  algorithm: SupportedAlgorithm;
  issuer?: string;
  audience?: string;
}

type JsonObject = Record<string, unknown>;

const isRecord = (value: unknown): value is JsonObject =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const parseAlgorithm = (value: string | undefined): SupportedAlgorithm => {
  const normalized = (value ?? 'HS256').trim().toUpperCase();
  if (normalized === 'HS256') {
    return 'HS256';
  }

  throw new Error(`Unsupported JWT algorithm "${value ?? ''}". Only HS256 is allowed.`);
};

const parsePort = (value: string | undefined): number => {
  const port = Number(value ?? '3000');
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error(`Invalid PORT value "${value ?? ''}"`);
  }
  return port;
};

const normalizeExpiresIn = (
  value: unknown,
): jwt.SignOptions['expiresIn'] | undefined => {
  if (value === undefined) {
    return undefined;
  }

  if (typeof value === 'string' || typeof value === 'number') {
    return value;
  }

  throw new Error('expiresIn must be a string or number');
};

const readJson = async (req: http.IncomingMessage): Promise<unknown> => {
  const chunks: Buffer[] = [];

  for await (const chunk of req) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }

  const raw = Buffer.concat(chunks).toString('utf8').trim();

  if (raw.length === 0) {
    return {};
  }

  return JSON.parse(raw);
};

const writeJson = (
  res: http.ServerResponse,
  statusCode: number,
  payload: unknown,
): void => {
  const body = JSON.stringify(payload);
  res.writeHead(statusCode, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': Buffer.byteLength(body).toString(),
  });
  res.end(body);
};

class AuthService {
  constructor(private readonly config: AuthServiceConfig) {}

  sign(payload: JsonObject, expiresIn?: jwt.SignOptions['expiresIn']): string {
    const options: jwt.SignOptions = {
      algorithm: this.config.algorithm,
    };

    if (this.config.issuer) {
      options.issuer = this.config.issuer;
    }

    if (this.config.audience) {
      options.audience = this.config.audience;
    }

    if (expiresIn !== undefined) {
      options.expiresIn = expiresIn;
    }

    return jwt.sign(payload, this.config.secret, options);
  }

  verify(token: string): string | jwt.JwtPayload {
    const options: jwt.VerifyOptions = {
      algorithms: [this.config.algorithm],
    };

    if (this.config.issuer) {
      options.issuer = this.config.issuer;
    }

    if (this.config.audience) {
      options.audience = this.config.audience;
    }

    return jwt.verify(token, this.config.secret, options);
  }
}

const config: AuthServiceConfig = {
  port: parsePort(process.env.PORT),
  secret: process.env.JWT_SECRET ?? 'secret123',
  algorithm: parseAlgorithm(process.env.JWT_ALGORITHM),
  issuer: process.env.JWT_ISSUER,
  audience: process.env.JWT_AUDIENCE,
};

const authService = new AuthService(config);

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url ?? '/', `http://${req.headers.host ?? 'localhost'}`);

    if (req.method === 'GET' && url.pathname === '/health') {
      writeJson(res, 200, {
        ok: true,
        algorithm: config.algorithm,
      });
      return;
    }

    if (req.method === 'POST' && url.pathname === '/token') {
      const body = await readJson(req);

      if (!isRecord(body)) {
        writeJson(res, 400, { error: 'Request body must be a JSON object.' });
        return;
      }

      const payloadSource = isRecord(body.payload)
        ? body.payload
        : Object.fromEntries(
            Object.entries(body).filter(([key]) => key !== 'expiresIn'),
          );

      const expiresIn = normalizeExpiresIn(body.expiresIn);
      const token = authService.sign(payloadSource, expiresIn);

      writeJson(res, 200, { token });
      return;
    }

    if (req.method === 'POST' && url.pathname === '/verify') {
      const body = await readJson(req);

      if (!isRecord(body) || typeof body.token !== 'string' || body.token.length === 0) {
        writeJson(res, 400, { error: 'Request body must include a non-empty token string.' });
        return;
      }

      const decoded = authService.verify(body.token);
      writeJson(res, 200, { valid: true, decoded });
      return;
    }

    writeJson(res, 404, { error: 'Not found' });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Internal server error';
    writeJson(res, 500, { error: message });
  }
});

server.listen(config.port, () => {
  process.stdout.write(
    `Auth service listening on http://localhost:${config.port} using ${config.algorithm}\n`,
  );
});