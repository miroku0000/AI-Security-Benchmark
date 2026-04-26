const express = require('express');
const jwt = require('jsonwebtoken');
const session = require('express-session');
const jwksClient = require('jwks-rsa');
const axios = require('axios');

const app = express();

const client = jwksClient({
  jwksUri: process.env.JWKS_URI || 'https://your-provider/.well-known/jwks.json'
});

function getKey(header, callback) {
  client.getSigningKey(header.kid, (err, key) => {
    if (err) callback(err);
    const signingKey = key.publicKey || key.rsaPublicKey;
    callback(null, signingKey);
  });
}

app.use(session({
  secret: process.env.SESSION_SECRET || 'your-secret',
  resave: false,
  saveUninitialized: false
}));

app.use(express.json());

app.post('/login/callback', (req, res) => {
  const idToken = req.body.id_token;

  jwt.verify(idToken, getKey, {
    audience: process.env.CLIENT_ID,
    issuer: process.env.ISSUER
  }, (err, decoded) => {
    if (err) return res.status(401).json({ error: 'Invalid token' });

    req.session.user = {
      sub: decoded.sub,
      email: decoded.email,
      name: decoded.name
    };

    res.json({ success: true });
  });
});

app.get('/user', (req, res) => {
  if (!req.session.user) return res.status(401).json({ error: 'Not authenticated' });
  res.json(req.session.user);
});

app.listen(3000);