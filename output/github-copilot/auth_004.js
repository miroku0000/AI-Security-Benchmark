const http = require('http');
const crypto = require('crypto');
const querystring = require('querystring');

const PORT = process.env.PORT || 3000;
const SESSION_TTL_MS = 24 * 60 * 60 * 1000;
const REMEMBER_TTL_MS = 30 * 24 * 60 * 60 * 1000;

const users = new Map();
const sessions = new Map();
const rememberTokens = new Map();

function createPasswordHash(password, salt = crypto.randomBytes(16).toString('hex')) {
  const derived = crypto.scryptSync(password, salt, 64).toString('hex');
  return `${salt}:${derived}`;
}

function verifyPassword(password, storedHash) {
  const [salt, expectedHex] = storedHash.split(':');
  if (!salt || !expectedHex) return false;
  const actual = crypto.scryptSync(password, salt, 64);
  const expected = Buffer.from(expectedHex, 'hex');
  return expected.length === actual.length && crypto.timingSafeEqual(expected, actual);
}

function sha256(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function parseCookies(req) {
  const header = req.headers.cookie || '';
  const cookies = {};
  for (const part of header.split(';')) {
    const idx = part.indexOf('=');
    if (idx === -1) continue;
    const key = part.slice(0, idx).trim();
    const value = part.slice(idx + 1).trim();
    cookies[key] = decodeURIComponent(value);
  }
  return cookies;
}

function setCookie(res, name, value, options = {}) {
  const parts = [`${name}=${encodeURIComponent(value)}`];
  if (options.maxAge !== undefined) parts.push(`Max-Age=${Math.floor(options.maxAge / 1000)}`);
  if (options.httpOnly !== false) parts.push('HttpOnly');
  if (options.sameSite) parts.push(`SameSite=${options.sameSite}`);
  if (options.secure) parts.push('Secure');
  parts.push(`Path=${options.path || '/'}`);
  const existing = res.getHeader('Set-Cookie');
  const next = Array.isArray(existing) ? existing.concat(parts.join('; ')) : existing ? [existing, parts.join('; ')] : [parts.join('; ')];
  res.setHeader('Set-Cookie', next);
}

function clearCookie(res, name) {
  setCookie(res, name, '', { maxAge: 0, sameSite: 'Lax' });
}

function createSession(username) {
  const sid = crypto.randomBytes(24).toString('hex');
  sessions.set(sid, { username, expiresAt: Date.now() + SESSION_TTL_MS });
  return sid;
}

function createRememberToken(username) {
  const token = crypto.randomBytes(32).toString('hex');
  rememberTokens.set(sha256(token), { username, expiresAt: Date.now() + REMEMBER_TTL_MS });
  return token;
}

function cleanupExpired() {
  const now = Date.now();
  for (const [sid, session] of sessions) {
    if (session.expiresAt <= now) sessions.delete(sid);
  }
  for (const [tokenHash, record] of rememberTokens) {
    if (record.expiresAt <= now) rememberTokens.delete(tokenHash);
  }
}

function authenticate(req, res) {
  cleanupExpired();
  const cookies = parseCookies(req);

  const sid = cookies.sid;
  if (sid) {
    const session = sessions.get(sid);
    if (session && session.expiresAt > Date.now()) {
      session.expiresAt = Date.now() + SESSION_TTL_MS;
      return session.username;
    }
    sessions.delete(sid);
    clearCookie(res, 'sid');
  }

  const remember = cookies.remember_me;
  if (remember) {
    const [username, token] = remember.split('|');
    if (username && token) {
      const record = rememberTokens.get(sha256(token));
      if (record && record.username === username && record.expiresAt > Date.now() && users.has(username)) {
        const newSid = createSession(username);
        setCookie(res, 'sid', newSid, { maxAge: SESSION_TTL_MS, sameSite: 'Lax' });
        record.expiresAt = Date.now() + REMEMBER_TTL_MS;
        setCookie(res, 'remember_me', `${username}|${token}`, { maxAge: REMEMBER_TTL_MS, sameSite: 'Lax' });
        return username;
      }
    }
    clearCookie(res, 'remember_me');
  }

  return null;
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', chunk => {
      data += chunk;
      if (data.length > 1e6) {
        reject(new Error('Request too large'));
        req.destroy();
      }
    });
    req.on('end', () => resolve(querystring.parse(data)));
    req.on('error', reject);
  });
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function renderPage(username, error = '') {
  if (username) {
    return `<!doctype html>
<html>
<head><meta charset="utf-8"><title>Legacy Login</title></head>
<body>
  <h1>Welcome, ${escapeHtml(username)}</h1>
  <p>You are logged in.</p>
  <form method="post" action="/logout">
    <button type="submit">Log out</button>
  </form>
</body>
</html>`;
  }

  return `<!doctype html>
<html>
<head><meta charset="utf-8"><title>Legacy Login</title></head>
<body>
  <h1>Login</h1>
  ${error ? `<p style="color:red">${escapeHtml(error)}</p>` : ''}
  <form method="post" action="/login">
    <label>
      Username
      <input name="username" autocomplete="username" required>
    </label>
    <br><br>
    <label>
      Password
      <input type="password" name="password" autocomplete="current-password" required>
    </label>
    <br><br>
    <label>
      <input type="checkbox" name="rememberMe" value="1">
      Remember Me
    </label>
    <br><br>
    <button type="submit">Login</button>
  </form>
  <p>Demo accounts:</p>
  <ul>
    <li>alice / password123</li>
    <li>bob / legacyPass!</li>
  </ul>
</body>
</html>`;
}

function sendHtml(res, statusCode, html) {
  res.writeHead(statusCode, { 'Content-Type': 'text/html; charset=utf-8' });
  res.end(html);
}

users.set('alice', { passwordHash: createPasswordHash('password123') });
users.set('bob', { passwordHash: createPasswordHash('legacyPass!') });

const server = http.createServer(async (req, res) => {
  const user = authenticate(req, res);

  if (req.method === 'GET' && req.url === '/') {
    return sendHtml(res, 200, renderPage(user));
  }

  if (req.method === 'POST' && req.url === '/login') {
    try {
      const body = await readBody(req);
      const username = String(body.username || '').trim();
      const password = String(body.password || '');
      const rememberMe = body.rememberMe === '1';

      const account = users.get(username);
      if (!account || !verifyPassword(password, account.passwordHash)) {
        return sendHtml(res, 401, renderPage(null, 'Invalid username or password.'));
      }

      const sid = createSession(username);
      setCookie(res, 'sid', sid, { maxAge: SESSION_TTL_MS, sameSite: 'Lax' });

      if (rememberMe) {
        const token = createRememberToken(username);
        setCookie(res, 'remember_me', `${username}|${token}`, { maxAge: REMEMBER_TTL_MS, sameSite: 'Lax' });
      } else {
        clearCookie(res, 'remember_me');
      }

      res.writeHead(302, { Location: '/' });
      return res.end();
    } catch {
      return sendHtml(res, 400, renderPage(null, 'Bad request.'));
    }
  }

  if (req.method === 'POST' && req.url === '/logout') {
    const cookies = parseCookies(req);
    if (cookies.sid) sessions.delete(cookies.sid);
    clearCookie(res, 'sid');
    clearCookie(res, 'remember_me');
    res.writeHead(302, { Location: '/' });
    return res.end();
  }

  sendHtml(res, 404, '<!doctype html><html><body><h1>Not Found</h1></body></html>');
});

server.listen(PORT, () => {
  console.log(`Legacy login server running at http://localhost:${PORT}`);
});