import type { NextFunction, Request, Response } from 'express';
import jwt, { JwtPayload } from 'jsonwebtoken';

export type AuthenticatedUser = {
  id?: string;
  email?: string;
  name?: string;
  roles: string[];
  [key: string]: unknown;
};

declare global {
  namespace Express {
    interface Request {
      user?: AuthenticatedUser;
    }
  }
}

function getBearerToken(authorization?: string): string | null {
  if (!authorization) return null;
  const [scheme, token] = authorization.split(' ');
  if (scheme !== 'Bearer' || !token) return null;
  return token as string;
}

function normalizeRoles(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.filter((role): role is string => typeof role === 'string');
  }

  if (typeof value === 'string') {
    return value
      .split(',')
      .map((role) => role.trim())
      .filter(Boolean);
  }

  return [];
}

function extractUser(payload: JwtPayload): AuthenticatedUser {
  return {
    id:
      typeof payload.sub === 'string'
        ? payload.sub
        : typeof payload.id === 'string'
          ? payload.id
          : undefined,
    email: typeof payload.email === 'string' ? payload.email : undefined,
    name:
      typeof payload.name === 'string'
        ? payload.name
        : typeof payload.username === 'string'
          ? payload.username
          : undefined,
    roles: normalizeRoles(payload.roles ?? payload.role),
    ...payload,
  };
}

export function jwtAuthMiddleware(req: Request, res: Response, next: NextFunction): void {
  const token: string | null = getBearerToken(req.headers.authorization);

  if (!token) {
    res.status(401).json({ error: 'Missing bearer token' });
    return;
  }

  const secret = process.env.JWT_SECRET;

  if (!secret) {
    res.status(500).json({ error: 'JWT_SECRET is not configured' });
    return;
  }

  try {
    const decoded = jwt.verify(token, secret);

    if (!decoded || typeof decoded === 'string') {
      res.status(401).json({ error: 'Invalid token payload' });
      return;
    }

    req.user = extractUser(decoded);
    next();
  } catch {
    res.status(401).json({ error: 'Invalid token' });
  }
}

export default jwtAuthMiddleware;