const express = require('express');
const session = require('express-session');
const crypto = require('crypto');
const jwt = require('jsonwebtoken');
const jwksClient = require('jwks-rsa');

const app = express();

const OIDC_CONFIG = {
  issuer: process.env.OIDC_ISSUER || 'https://accounts.example.com',
  authorizationEndpoint: process.env.OIDC_AUTH_ENDPOINT || 'https://accounts.example.com/authorize',
  tokenEndpoint: process.env.OIDC_TOKEN_ENDPOINT || 'https://accounts.example.com/oauth/token',
  jwksUri: process.env.OIDC_JWKS_URI || 'https://accounts.example.com/.well-known/jwks.json',
  clientId: process.env.OIDC_CLIENT_ID || 'your-client-id',
  clientSecret: process.env.OIDC_CLIENT_SECRET || 'your-client-secret',
  redirectUri: process.env.OIDC_REDIRECT_URI || 'http://localhost:3000/callback',
  scope: 'openid profile email',
};

const jwksClientInstance = jwksClient({
  jwksUri: OIDC_CONFIG.jwksUri,
  cache: true,
  rateLimit: true,
});

function getSigningKey(header, callback) {
  jwksClientInstance.getSigningKey(header.kid, (err, key) => {
    if (err) return callback(err);
    const signingKey = key.getPublicKey();
    callback(null, signingKey);
  });
}

function verifyIdToken(idToken) {
  return new Promise((resolve, reject) => {
    jwt.verify(
      idToken,
      getSigningKey,
      {
        algorithms: ['RS256'],
        issuer: OIDC_CONFIG.issuer,
        audience: OIDC_CONFIG.clientId,
      },
      (err, decoded) => {
        if (err) return reject(err);
        resolve(decoded);
      }
    );
  });
}

app.use(session({
  secret: process.env.SESSION_SECRET || crypto.randomBytes(32).toString('hex'),
  resave: false,
  saveUninitialized: false,
  cookie: { secure: process.env.NODE_ENV === 'production', httpOnly: true, sameSite: 'lax' },
}));

app.get('/login', (req, res) => {
  const state = crypto.randomBytes(16).toString('hex');
  const nonce = crypto.randomBytes(16).toString('hex');
  req.session.oauthState = state;
  req.session.oauthNonce = nonce;

  const params = new URLSearchParams({
    response_type: 'code',
    client_id: OIDC_CONFIG.clientId,
    redirect_uri: OIDC_CONFIG.redirectUri,
    scope: OIDC_CONFIG.scope,
    state: state,
    nonce: nonce,
  });

  res.redirect(`${OIDC_CONFIG.authorizationEndpoint}?${params}`);
});

app.get('/callback', async (req, res) => {
  const { code, state } = req.query;

  if (!code || !state || state !== req.session.oauthState) {
    return res.status(403).send('Invalid state parameter');
  }
  delete req.session.oauthState;

  try {
    const tokenResponse = await fetch(OIDC_CONFIG.tokenEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        code: code,
        redirect_uri: OIDC_CONFIG.redirectUri,
        client_id: OIDC_CONFIG.clientId,
        client_secret: OIDC_CONFIG.clientSecret,
      }),
    });

    if (!tokenResponse.ok) {
      return res.status(502).send('Token exchange failed');
    }

    const tokens = await tokenResponse.json();

    // Verify the id_token signature and claims using JWKS — never use jwt.decode()
    // which skips verification and would allow forged tokens
    const claims = await verifyIdToken(tokens.id_token);

    if (claims.nonce !== req.session.oauthNonce) {
      return res.status(403).send('Invalid nonce');
    }
    delete req.session.oauthNonce;

    req.session.user = {
      sub: claims.sub,
      email: claims.email,
      name: claims.name,
    };

    res.redirect('/profile');
  } catch (err) {
    console.error('Authentication error:', err.message);
    res.status(401).send('Authentication failed');
  }
});

app.get('/profile', (req, res) => {
  if (!req.session.user) {
    return res.redirect('/login');
  }
  res.json({ user: req.session.user });
});

app.get('/logout', (req, res) => {
  req.session.destroy(() => {
    res.redirect('/');
  });
});

app.get('/', (req, res) => {
  if (req.session.user) {
    res.send(`<p>Hello, ${req.session.user.name}</p><a href="/profile">Profile</a> | <a href="/logout">Logout</a>`);
  } else {
    res.send('<a href="/login">Log in with OIDC</a>');
  }
});

app.listen(3000, () => console.log('Server running on http://localhost:3000'));