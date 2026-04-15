export function jwtAuthMiddleware(req: Request, res: Response, next: NextFunction): void {
  const token: string | null = extractBearerToken(req.header('authorization'));