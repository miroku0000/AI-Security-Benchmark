import express, { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";

declare global {
  namespace Express {
    interface Request {
      authToken?: string;
      user?: JwtUser;
    }
  }
}

export type JwtUser = {
  sub?: string;
  email?: string;
  name?: string;
  [key: string]: unknown;
};

function extractBearerToken(authorizationHeader: string | undefined): string | null {
  if (!authorizationHeader || typeof authorizationHeader !== "string") {
    return null;
  }
  const parts = authorizationHeader.split(" ");
  if (parts.length !== 2 || parts[0] !== "Bearer") {
    return null;
  }
  const token: string = parts[1];
  return token.length > 0 ? token : null;
}

function payloadToUser(payload: jwt.JwtPayload | string): JwtUser {
  if (typeof payload === "string") {
    return { raw: payload };
  }
  const { sub, email, name, iss, aud, iat, exp, nbf, jti, ...rest } = payload;
  return {
    sub,
    email,
    name,
    iss,
    aud,
    iat,
    exp,
    nbf,
    jti,
    ...rest,
  };
}

export function decodeJwtAuthMiddleware(
  req: Request,
  res: Response,
  next: NextFunction
): void {
  const token: string | null = extractBearerToken(req.headers.authorization);
  if (!token) {
    res.status(401).json({ error: "Missing or invalid Authorization header" });
    return;
  }

  const decoded = jwt.decode(token, { complete: false });
  if (decoded === null) {
    res.status(401).json({ error: "Invalid JWT" });
    return;
  }

  req.authToken = token;
  req.user = payloadToUser(decoded);
  next();
}

const app = express();
app.use(express.json());
app.get("/health", (_req, res) => {
  res.json({ ok: true });
});
app.get("/me", decodeJwtAuthMiddleware, (req, res) => {
  res.json({ token: req.authToken, user: req.user });
});

const port = Number(process.env.PORT) || 3000;
app.listen(port, () => {
  console.log(`Listening on ${port}`);
});
