export class AuthService {
  private readonly secret: string;
  private readonly algorithm: SupportedAlgorithm;
  private readonly expiresIn?: string | number;
  private readonly issuer?: string;
  private readonly audience?: string | string[];