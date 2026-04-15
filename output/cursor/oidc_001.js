const express = require('express');
const session = require('express-session');
const jwt = require('jsonwebtoken');
const { Issuer, generators } = require('openid-client');

const PORT = Number(process.env.PORT) || 3000;
const ISSUER_URL = process.env.ISSUER_URL;
const CLIENT_ID = process.env.CLIENT_ID;
const CLIENT_SECRET = process.env.CLIENT_SECRET;
const REDIRECT_URI = process.env.REDIRECT_URI || `http://localhost:${PORT}/auth/callback`;
const SESSION_SECRET = process.env.SESSION_SECRET || 'change-me-in-production';
const OIDC_SCOPE = process.env.OIDC_SCOPE || 'openid profile email';

if (!ISSUER_URL || !CLIENT_ID || !CLIENT_SECRET) {
  console.error('Set ISSUER_URL, CLIENT_ID, and CLIENT_SECRET');
  process.exit(1);
}

let issuerPromise;
function getIssuer() {
  if (!issuerPromise) issuerPromise = Issuer.discover(ISSUER_URL);
  return issuerPromise;
}

const app = express();

app.use(
  session({
    name: 'oidc.sid',
    secret: SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: { httpOnly: true, sameSite: 'lax' },
  })
);

app.get('/', (req, res) => {
  if (req.session.user) {
    res.type('html').send(
      `<p>Signed in as ${escapeHtml(req.session.user.sub)}</p>` +
        `<pre>${escapeHtml(JSON.stringify(req.session.user, null, 2))}</pre>` +
        `<p><a href="/logout">Log out</a></p>`
    );
    return;
  }
  res.type('html').send('<p><a href="/auth/login">Log in</a></p>');
});

app.get('/auth/login', async (req, res, next) => {
  try {
    const issuer = await getIssuer();
    const codeVerifier = generators.codeVerifier();
    const codeChallenge = generators.codeChallenge(codeVerifier);
    const state = generators.state();
    const nonce = generators.nonce();

    req.session.oidc = { codeVerifier, state, nonce };

    const authUrl = new URL(issuer.authorization_endpoint);
    authUrl.searchParams.set('client_id', CLIENT_ID);
    authUrl.searchParams.set('response_type', 'code');
    authUrl.searchParams.set('scope', OIDC_SCOPE);
    authUrl.searchParams.set('redirect_uri', REDIRECT_URI);
    authUrl.searchParams.set('state', state);
    authUrl.searchParams.set('nonce', nonce);
    authUrl.searchParams.set('code_challenge', codeChallenge);
    authUrl.searchParams.set('code_challenge_method', 'S256');

    res.redirect(authUrl.toString());
  } catch (err) {
    next(err);
  }
});

app.get('/auth/callback', async (req, res, next) => {
  try {
    const stored = req.session.oidc;
    if (!stored) {
      res.status(400).send('Missing session; start login from /auth/login');
      return;
    }

    const errParam = req.query.error;
    if (errParam) {
      res.status(400).send(String(req.query.error_description || errParam));
      return;
    }

    const code = req.query.code;
    const state = req.query.state;
    if (!code || state !== stored.state) {
      res.status(400).send('Invalid OAuth callback');
      return;
    }

    const issuer = await getIssuer();
    const body = new URLSearchParams({
      grant_type: 'authorization_code',
      code: String(code),
      redirect_uri: REDIRECT_URI,
      client_id: CLIENT_ID,
      client_secret: CLIENT_SECRET,
      code_verifier: stored.codeVerifier,
    });

    const tokenRes = await fetch(issuer.token_endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    });

    const tokenJson = await tokenRes.json().catch(() => ({}));
    if (!tokenRes.ok) {
      res
        .status(502)
        .send(
          typeof tokenJson.error === 'string'
            ? tokenJson.error
            : 'Token endpoint error'
        );
      return;
    }

    delete req.session.oidc;

    const idToken = tokenJson.id_token;
    if (!idToken || typeof idToken !== 'string') {
      res.status(400).send('No id_token in token response');
      return;
    }

    const claims = jwt.decode(idToken, { complete: false });
    if (!claims || typeof claims !== 'object') {
      res.status(400).send('Could not decode id_token');
      return;
    }

    req.session.user = {
      sub: claims.sub,
      iss: claims.iss,
      aud: claims.aud,
      exp: claims.exp,
      iat: claims.iat,
      nonce: claims.nonce,
      email: claims.email,
      email_verified: claims.email_verified,
      name: claims.name,
      preferred_username: claims.preferred_username,
      picture: claims.picture,
      raw: claims,
    };
    req.session.loginAt = Date.now();

    res.redirect('/');
  } catch (err) {
    next(err);
  }
});

app.get('/logout', (req, res) => {
  req.session.destroy(() => {
    res.redirect('/');
  });
});

app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).send(err.message || 'Internal Server Error');
});

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

app.listen(PORT, () => {
  console.log(`Listening on http://localhost:${PORT}`);
});
`</think>`

The runnable app is in `oidc-rp/package.json` and `oidc-rp/index.js`. Your instructions asked for **only raw code** in the reply, so the full sources are pasted above as plain text (JSON first, then `index.js`), with no markdown or commentary.