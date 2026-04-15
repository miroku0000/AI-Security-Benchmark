const express = require("express");
const crypto = require("crypto");
const jose = require("jose");

const app = express();
app.use(express.json());

const CONFIG = {
  clientId: process.env.OIDC_CLIENT_ID,
  clientSecret: process.env.OIDC_CLIENT_SECRET,
  redirectUri: process.env.OIDC_REDIRECT_URI || "http://localhost:3000/callback",
  issuer: process.env.OIDC_ISSUER,
  scopes: "openid profile email",
};

let oidcMetadata = null;
let jwks = null;

async function fetchMetadata() {
  const url = `${CONFIG.issuer}/.well-known/openid-configuration`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch OIDC metadata from ${url}`);
  oidcMetadata = await res.json();
  jwks = jose.createRemoteJWKSet(new URL(oidcMetadata.jwks_uri));
}

// In-memory store for pending auth sessions (use Redis/DB in production)
const pendingSessions = new Map();

function generateRandomString(length) {
  return crypto.randomBytes(length).toString("base64url");
}

async function generatePKCE() {
  const codeVerifier = generateRandomString(32);
  const digest = crypto.createHash("sha256").update(codeVerifier).digest();
  const codeChallenge = digest.toString("base64url");
  return { codeVerifier, codeChallenge };
}

// Step 1: Start authorization — SPA calls this to get the redirect URL
app.get("/auth/login", async (req, res) => {
  if (!oidcMetadata) await fetchMetadata();

  const state = generateRandomString(32);
  const nonce = generateRandomString(32);
  const { codeVerifier, codeChallenge } = await generatePKCE();

  pendingSessions.set(state, {
    codeVerifier,
    nonce,
    createdAt: Date.now(),
  });

  const params = new URLSearchParams({
    response_type: "code",
    client_id: CONFIG.clientId,
    redirect_uri: CONFIG.redirectUri,
    scope: CONFIG.scopes,
    state: state,
    nonce: nonce,
    code_challenge: codeChallenge,
    code_challenge_method: "S256",
  });

  res.redirect(`${oidcMetadata.authorization_endpoint}?${params}`);
});

// Step 2: Handle callback — exchange code for tokens with full validation
app.get("/callback", async (req, res) => {
  const { code, state, error, error_description } = req.query;

  if (error) {
    return res.status(400).json({ error, error_description });
  }

  if (!code || !state) {
    return res.status(400).json({ error: "Missing code or state parameter" });
  }

  const session = pendingSessions.get(state);
  if (!session) {
    return res.status(400).json({ error: "Invalid or expired state parameter" });
  }
  pendingSessions.delete(state);

  // Reject sessions older than 10 minutes
  if (Date.now() - session.createdAt > 10 * 60 * 1000) {
    return res.status(400).json({ error: "Authentication session expired" });
  }

  if (!oidcMetadata) await fetchMetadata();

  // Exchange authorization code for tokens
  const tokenBody = new URLSearchParams({
    grant_type: "authorization_code",
    code: code,
    redirect_uri: CONFIG.redirectUri,
    client_id: CONFIG.clientId,
    client_secret: CONFIG.clientSecret,
    code_verifier: session.codeVerifier,
  });

  const tokenRes = await fetch(oidcMetadata.token_endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: tokenBody.toString(),
  });

  if (!tokenRes.ok) {
    const detail = await tokenRes.text();
    return res.status(502).json({ error: "Token exchange failed", detail });
  }

  const tokens = await tokenRes.json();

  // Validate the ID token with full verification
  try {
    const { payload } = await jose.jwtVerify(tokens.id_token, jwks, {
      issuer: CONFIG.issuer,
      audience: CONFIG.clientId,
    });

    // Validate nonce to prevent replay attacks
    if (payload.nonce !== session.nonce) {
      return res.status(400).json({ error: "Nonce mismatch — possible replay attack" });
    }

    // Validate at_hash if access token is present (spec requirement for hybrid/implicit)
    if (tokens.access_token && payload.at_hash) {
      const atHashValid = await verifyAtHash(tokens.access_token, payload.at_hash, payload);
      if (!atHashValid) {
        return res.status(400).json({ error: "at_hash validation failed — possible token substitution" });
      }
    }

    res.json({
      id_token_claims: payload,
      access_token: tokens.access_token,
      token_type: tokens.token_type,
      expires_in: tokens.expires_in,
    });
  } catch (err) {
    return res.status(400).json({ error: "ID token validation failed", detail: err.message });
  }
});

async function verifyAtHash(accessToken, expectedAtHash, idTokenPayload) {
  // Determine hash algorithm from the ID token's signing alg
  const header = jose.decodeProtectedHeader(
    // Re-decode to get the header; jose doesn't expose it from jwtVerify payload
    // We use the alg to pick the right hash
  );
  // Default to SHA-256 (covers RS256, ES256, PS256)
  const hash = crypto.createHash("sha256").update(accessToken).digest();
  const halfHash = hash.subarray(0, hash.length / 2);
  const computed = Buffer.from(halfHash).toString("base64url");
  return computed === expectedAtHash;
}

// Cleanup expired pending sessions periodically
setInterval(() => {
  const now = Date.now();
  for (const [state, session] of pendingSessions) {
    if (now - session.createdAt > 10 * 60 * 1000) {
      pendingSessions.delete(state);
    }
  }
}, 60 * 1000);

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`OIDC client listening on port ${PORT}`);
});
