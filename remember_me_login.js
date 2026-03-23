'use strict';

const crypto = require('crypto');
const express = require('express');

const REMEMBER_COOKIE = 'remember_me';
const SESSION_COOKIE = 'session_id';
const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;

const users = new Map();

function legacyPasswordHash(password) {
  return crypto.createHash('sha256').update(String(password), 'utf8').digest('hex');
}

function parseCookies(cookieHeader) {
  const out = Object.create(null);
  if (!cookieHeader || typeof cookieHeader !== 'string') return out;
  for (const part of cookieHeader.split(';')) {
    const idx = part.indexOf('=');
    if (idx === -1) continue;
    const name = part.slice(0, idx).trim();
    const value = part.slice(idx + 1).trim();
    try {
      out[name] = decodeURIComponent(value);
    } catch {
      out[name] = value;
    }
  }
  return out;
}

function appendSetCookie(res, name, value, options) {
  const parts = [`${encodeURIComponent(name)}=${encodeURIComponent(value)}`, 'Path=/'];
  if (options.maxAgeMs != null) {
    parts.push(`Max-Age=${Math.floor(options.maxAgeMs / 1000)}`);
  }
  if (options.httpOnly) parts.push('HttpOnly');
  if (options.sameSite) parts.push(`SameSite=${options.sameSite}`);
  res.append('Set-Cookie', parts.join('; '));
}

function clearCookie(res, name) {
  appendSetCookie(res, name, '', { maxAgeMs: 0, httpOnly: true, sameSite: 'Lax' });
}

function rememberCookieValue(username, passwordHash) {
  const payload = JSON.stringify({ u: username, h: passwordHash });
  return Buffer.from(payload, 'utf8').toString('base64');
}

function parseRememberCookie(raw) {
  if (!raw) return null;
  try {
    const json = Buffer.from(String(raw), 'base64').toString('utf8');
    const o = JSON.parse(json);
    if (!o || typeof o.u !== 'string' || typeof o.h !== 'string') return null;
    return { username: o.u, passwordHash: o.h };
  } catch {
    return null;
  }
}

const sessions = new Map();

function createSession(username) {
  const id = crypto.randomBytes(24).toString('hex');
  sessions.set(id, { username, at: Date.now() });
  return id;
}

function getSessionUser(sessionId) {
  if (!sessionId) return null;
  const s = sessions.get(sessionId);
  return s ? s.username : null;
}

function ensureUser(username, password) {
  const hash = legacyPasswordHash(password);
  users.set(username, { passwordHash: hash });
  return hash;
}

ensureUser('demo', 'demo123');

const app = express();
app.use(express.urlencoded({ extended: false }));
app.use(express.json());

function tryAutoLogin(req, res, next) {
  const cookies = parseCookies(req.headers.cookie || '');
  let sid = cookies[SESSION_COOKIE];
  if (sid && getSessionUser(sid)) {
    req.authenticatedUser = getSessionUser(sid);
    return next();
  }
  const remembered = parseRememberCookie(cookies[REMEMBER_COOKIE]);
  if (!remembered) return next();
  const record = users.get(remembered.username);
  if (!record || record.passwordHash !== remembered.passwordHash) {
    clearCookie(res, REMEMBER_COOKIE);
    return next();
  }
  sid = createSession(remembered.username);
  appendSetCookie(res, SESSION_COOKIE, sid, {
    maxAgeMs: THIRTY_DAYS_MS,
    httpOnly: true,
    sameSite: 'Lax',
  });
  req.authenticatedUser = remembered.username;
  next();
}

app.use(tryAutoLogin);

app.get('/', (req, res) => {
  const u = req.authenticatedUser;
  if (u) {
    res.type('html').send(
      '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Home</title></head><body>' +
        '<p>Signed in as <strong>' +
        escapeHtml(u) +
        '</strong></p><form method="post" action="/logout"><button type="submit">Log out</button></form>' +
        '</body></html>'
    );
    return;
  }
  res.type('html').send(`<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Login</title></head><body>
<form method="post" action="/login">
  <label>Username <input name="username" autocomplete="username" required></label><br>
  <label>Password <input name="password" type="password" autocomplete="current-password" required></label><br>
  <label><input name="remember" type="checkbox" value="1"> Remember me</label><br>
  <button type="submit">Log in</button>
</form>
</body></html>`);
});

app.post('/login', (req, res) => {
  const username = String(req.body.username || '').trim();
  const password = String(req.body.password || '');
  const remember = req.body.remember === '1' || req.body.remember === 'on' || req.body.remember === true;
  const record = users.get(username);
  if (!record || record.passwordHash !== legacyPasswordHash(password)) {
    res.status(401).type('html').send('<p>Invalid credentials</p><a href="/">Back</a>');
    return;
  }
  const sid = createSession(username);
  appendSetCookie(res, SESSION_COOKIE, sid, {
    maxAgeMs: THIRTY_DAYS_MS,
    httpOnly: true,
    sameSite: 'Lax',
  });
  if (remember) {
    appendSetCookie(res, REMEMBER_COOKIE, rememberCookieValue(username, record.passwordHash), {
      maxAgeMs: THIRTY_DAYS_MS,
      httpOnly: true,
      sameSite: 'Lax',
    });
  } else {
    clearCookie(res, REMEMBER_COOKIE);
  }
  res.redirect('/');
});

app.post('/logout', (req, res) => {
  const cookies = parseCookies(req.headers.cookie || '');
  const sid = cookies[SESSION_COOKIE];
  if (sid) sessions.delete(sid);
  clearCookie(res, SESSION_COOKIE);
  clearCookie(res, REMEMBER_COOKIE);
  res.redirect('/');
});

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

const port = Number(process.env.PORT) || 3456;
app.listen(port, () => {
  process.stdout.write('Remember-me login listening on http://127.0.0.1:' + port + '\n');
});
