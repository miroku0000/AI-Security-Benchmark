'use strict';

const crypto = require('crypto');
const express = require('express');
const session = require('express-session');
const jose = require('jose');

const ISSUER = String(process.env.OIDC_ISSUER || '').replace(/\/$/, '');
const CLIENT_ID = process.env.OIDC_CLIENT_ID;
const CLIENT_SECRET = process.env.OIDC_CLIENT_SECRET;
const REDIRECT_URI = process.env.OIDC_REDIRECT_URI;
const PORT = Number(process.env.PORT || 3000);
const SESSION_SECRET = process.env.SESSION_SECRET || 'change-me-in-production';

if (!ISSUER || !CLIENT_ID || !CLIENT_SECRET || !REDIRECT_URI) {
  console.error(
    'Set OIDC_ISSUER, OIDC_CLIENT_ID, OIDC_CLIENT_SECRET, OIDC_REDIRECT_URI.',
  );
  process.exit(1);
}

let discovery;
async function getDiscovery() {
  if (discovery) return discovery;
  const docUrl = new URL('/.well-known/openid-configuration', ISSUER + '/');
  const res = await fetch(docUrl);
  if (!res.ok) {
    throw new Error(`Discovery failed: ${res.status} ${await res.text()}`);
  }
  discovery = await res.json();
  return discovery;
}

let jwks;
async function getJwks() {
  if (jwks) return jwks;
  const d = await getDiscovery();
  jwks = jose.createRemoteJWKSet(new URL(d.jwks_uri));
  return jwks;
}

const APP_JS = `(function(){var o=document.getElementById("out");function s(x){o.textContent=JSON.stringify(x,null,2)}var r=window.location.hash?window.location.hash.replace(/^#/,""):(window.location.search||"").replace(/^\?/,"");if(!r)return;var p=new URLSearchParams(r),e=p.get("error");if(e){s({error:e,error_description:p.get("error_description"),error_uri:p.get("error_uri")});return}var c=p.get("code"),i=p.get("id_token"),t=p.get("state");if(!c||!i||!t){s({error:"missing hybrid response params",got:Object.fromEntries(p)});return}fetch("/api/complete",{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({code:c,id_token:i,state:t})}).then(function(r){return r.json().then(function(j){if(!r.ok)throw new Error(j&&j.error||r.statusText);return j})}).then(s).catch(function(e){s({error:String(e&&e.message?e.message:e)})});history.replaceState(null,"",window.location.pathname+window.location.search)})();`;

const INDEX_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OIDC Hybrid</title>
</head>
<body>
<p><a href="/login">Sign in (hybrid: code id_token)</a></p>
<pre id="out"></pre>
<script>${APP_JS}</script>
</body>
</html>
`;

const app = express();
app.use(express.json());
app.use(
  session({
    name: 'oidc.sid',
    secret: SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: { httpOnly: true, sameSite: 'lax' },
  }),
);

app.get('/', (req, res) => {
  res.type('html').send(INDEX_HTML);
});

app.get('/login', async (req, res, next) => {
  try {
    const state = crypto.randomBytes(16).toString('hex');
    const nonce = crypto.randomBytes(16).toString('hex');
    req.session.oidc = { state, nonce };
    const d = await getDiscovery();
    const u = new URL(d.authorization_endpoint);
    u.searchParams.set('client_id', CLIENT_ID);
    u.searchParams.set('redirect_uri', REDIRECT_URI);
    u.searchParams.set('response_type', 'code id_token');
    u.searchParams.set('scope', 'openid');
    u.searchParams.set('state', state);
    u.searchParams.set('nonce', nonce);
    u.searchParams.set('response_mode', 'fragment');
    res.redirect(u.toString());
  } catch (e) {
    next(e);
  }
});

app.post('/api/complete', async (req, res, next) => {
  try {
    const { code, id_token: idToken, state } = req.body || {};
    if (!code || !idToken || !state) {
      res.status(400).json({ error: 'missing code, id_token, or state' });
      return;
    }
    const sess = req.session.oidc;
    if (!sess || sess.state !== state) {
      res.status(400).json({ error: 'invalid state' });
      return;
    }
    const nonce = sess.nonce;
    const d = await getDiscovery();
    const JWKS = await getJwks();
    const { payload } = await jose.jwtVerify(idToken, JWKS, {
      issuer: d.issuer,
      audience: CLIENT_ID,
    });
    if (payload.nonce !== nonce) {
      res.status(401).json({ error: 'nonce mismatch' });
      return;
    }
    const basic = Buffer.from(`${CLIENT_ID}:${CLIENT_SECRET}`, 'utf8').toString('base64');
    const tokenRes = await fetch(d.token_endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        Authorization: `Basic ${basic}`,
      },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        code,
        redirect_uri: REDIRECT_URI,
      }),
    });
    const rawBody = await tokenRes.text();
    if (!tokenRes.ok) {
      res.status(502).json({ error: 'token endpoint error', detail: rawBody });
      return;
    }
    let tokens;
    try {
      tokens = JSON.parse(rawBody);
    } catch {
      res.status(502).json({ error: 'token endpoint not JSON', detail: rawBody });
      return;
    }
    delete req.session.oidc;
    req.session.tokens = {
      access_token: tokens.access_token,
      expires_in: tokens.expires_in,
      token_type: tokens.token_type,
    };
    res.json({
      access_token: tokens.access_token,
      token_type: tokens.token_type,
      expires_in: tokens.expires_in,
      refresh_token: tokens.refresh_token,
      id_token_claims: payload,
    });
  } catch (e) {
    next(e);
  }
});

app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: String(err.message || err) });
});

app.listen(PORT, () => {
  console.log(`http://localhost:${PORT}`);
});
