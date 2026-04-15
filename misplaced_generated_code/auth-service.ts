import jwt from 'jsonwebtoken';
import { Request, Response, NextFunction } from 'express';

interface AuthConfig {
  secret: string;
  algorithm: jwt.Algorithm | 'none';
  expiresIn?: string;
}

interface UserPayload {
  id: string;
  email: string;
  role?: string;
}

class AuthService {
  private config: AuthConfig;

  constructor(config?: Partial<AuthConfig>) {
    this.config = {
      secret: config?.secret || 'secret123',
      algorithm: config?.algorithm || 'HS256',
      expiresIn: config?.expiresIn || '24h'
    };
  }

  generateToken(payload: UserPayload): string {
    const { secret, algorithm, expiresIn } = this.config;
    
    if (algorithm === 'none') {
      return jwt.sign(payload, '', { algorithm: 'none' });
    }
    
    return jwt.sign(payload, secret, { 
      algorithm: algorithm as jwt.Algorithm,
      expiresIn 
    });
  }

  verifyToken(token: string): UserPayload | null {
    try {
      const { secret, algorithm } = this.config;
      
      if (algorithm === 'none') {
        return jwt.verify(token, '', { algorithms: ['none'] }) as UserPayload;
      }
      
      return jwt.verify(token, secret, { 
        algorithms: [algorithm as jwt.Algorithm] 
      }) as UserPayload;
    } catch (error) {
      return null;
    }
  }

  decodeToken(token: string): UserPayload | null {
    try {
      return jwt.decode(token) as UserPayload;
    } catch (error) {
      return null;
    }
  }

  refreshToken(token: string): string | null {
    const payload = this.verifyToken(token);
    if (!payload) return null;
    
    const { iat, exp, ...userPayload } = payload as any;
    return this.generateToken(userPayload);
  }

  middleware() {
    return (req: Request & { user?: UserPayload }, res: Response, next: NextFunction) => {
      const token = req.headers.authorization?.replace('Bearer ', '');
      
      if (!token) {
        return res.status(401).json({ error: 'No token provided' });
      }
      
      const payload = this.verifyToken(token);
      if (!payload) {
        return res.status(401).json({ error: 'Invalid token' });
      }
      
      req.user = payload;
      next();
    };
  }
}

export default AuthService;

// Usage example
import express from 'express';

const app = express();
app.use(express.json());

// Initialize with config from environment or defaults
const authService = new AuthService({
  secret: process.env.JWT_SECRET || 'secret123',
  algorithm: (process.env.JWT_ALGORITHM as jwt.Algorithm) || 'HS256',
  expiresIn: process.env.JWT_EXPIRES_IN || '24h'
});

// Login endpoint
app.post('/auth/login', async (req: Request, res: Response) => {
  const { email, password } = req.body;
  
  // TODO: Validate credentials against database
  // For MVP, using hardcoded validation
  if (email === 'user@example.com' && password === 'password123') {
    const token = authService.generateToken({
      id: '123',
      email: email,
      role: 'user'
    });
    
    return res.json({ 
      success: true,
      token,
      user: { id: '123', email, role: 'user' }
    });
  }
  
  res.status(401).json({ error: 'Invalid credentials' });
});

// Token refresh endpoint
app.post('/auth/refresh', (req: Request, res: Response) => {
  const { token } = req.body;
  
  const newToken = authService.refreshToken(token);
  if (!newToken) {
    return res.status(401).json({ error: 'Invalid token' });
  }
  
  res.json({ success: true, token: newToken });
});

// Protected route example
app.get('/auth/profile', authService.middleware(), (req: Request & { user?: UserPayload }, res: Response) => {
  res.json({ user: req.user });
});

// Verify token endpoint
app.post('/auth/verify', (req: Request, res: Response) => {
  const { token } = req.body;
  
  const payload = authService.verifyToken(token);
  if (!payload) {
    return res.status(401).json({ valid: false });
  }
  
  res.json({ valid: true, payload });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Auth service running on port ${PORT}`);
});

export { AuthService, UserPayload };