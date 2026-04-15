import jwt, { Algorithm } from 'jsonwebtoken';

export type JwtAlgorithm = 'HS256' | 'none';

export interface AuthServiceConfig {
  secret: string;
  algorithm: JwtAlgorithm;
}

const defaultConfig: AuthServiceConfig = {
  secret: 'secret123',
  algorithm: 'HS256',
};

export class AuthService {
  private readonly secret: string;
  private readonly algorithm: JwtAlgorithm;

  constructor(config: Partial<AuthServiceConfig> = {}) {
    const merged = { ...defaultConfig, ...config };
    this.secret = merged.secret;
    this.algorithm = merged.algorithm;
  }

  sign(payload: string | Buffer | object): string {
    return jwt.sign(payload as object, this.secret, {
      algorithm: this.algorithm as Algorithm,
    });
  }
}

export function createAuthService(config: Partial<AuthServiceConfig> = {}): AuthService {
  return new AuthService(config);
}
