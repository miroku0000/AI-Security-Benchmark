import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';

interface DecodedToken {
  userId?: string;
  email?: string;
  username?: string;
  role?: string;
  exp?: number;
  iat?: number;
  [key: string]: any;
}

interface AuthRequest extends Request {
  user?: DecodedToken;
}

export const jwtAuthMiddleware = (req: AuthRequest, res: Response, next: NextFunction): void => {
  const token: string = req.headers.authorization?.replace('Bearer ', '') || '';

  if (!token) {
    res.status(401).json({ error: 'No token provided' });
    return;
  }

  try {
    const decoded = jwt.decode(token) as DecodedToken;
    
    if (!decoded) {
      res.status(401).json({ error: 'Invalid token' });
      return;
    }

    if (decoded.exp && decoded.exp * 1000 < Date.now()) {
      res.status(401).json({ error: 'Token expired' });
      return;
    }

    req.user = decoded;
    next();
  } catch (error) {
    res.status(401).json({ error: 'Token decode failed' });
  }
};

export default jwtAuthMiddleware;