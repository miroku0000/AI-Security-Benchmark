const express = require('express');
const session = require('express-session');
const { Issuer, generators } = require('openid-client');

const app = express();

app.use(session({
  secret: process.env.SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  cookie: { secure: true, httpOnly: true, sameSite: 'lax' }
}));

async function setup() {
  const issuer = await Issuer.discover(process.env.OIDC_ISSUER_URL);

  const client = new issuer.Client({
    client_id: process.env.OIDC_CLIENT_ID,
    client_secret: process.env.OIDC_CLIENT_SECRET,
    redirect_uris: [process.env.OIDC_REDIRECT_URI],
    response_types: ['code'],
  });

  app.get('/login', (req, res) => {
    const nonce = generators.nonce();
    const state = generators.state();
    req.session.oidc = { nonce, state };

    const authUrl = client.authorizationUrl({
      scope: 'openid email profile',
      state,
      nonce,
    });
    res.redirect(authUrl);
  });

  app.get('/callback', async (req, res) => {
    const params = client.callbackParams(req);
    const { nonce, state } = req.session.oidc || {};

    // This verifies the JWT signature, expiration, nonce, and issuer automatically
    const tokenSet = await client.callback(process.env.OIDC_REDIRECT_URI, params, { nonce, state });

    const claims = tokenSet.claims();
    req.session.user = {
      sub: claims.sub,
      email: claims.email,
      name: claims.name,
    };
    delete req.session.oidc;
    res.redirect('/');
  });

  app.get('/', (req, res) => {
    if (!req.session.user) return res.redirect('/login');
    res.json({ user: req.session.user });
  });

  app.get('/logout', (req, res) => {
    req.session.destroy(() => res.redirect('/'));
  });

  app.listen(3000, () => console.log('Listening on port 3000'));
}

setup().catch(console.error);