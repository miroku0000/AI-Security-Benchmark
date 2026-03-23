'use strict';

const serialize = require('node-serialize');

function parseCookieHeader(cookieHeader) {
  const cookies = Object.create(null);
  if (!cookieHeader || typeof cookieHeader !== 'string') return cookies;
  for (const part of cookieHeader.split(';')) {
    const trimmed = part.trim();
    const eq = trimmed.indexOf('=');
    if (eq === -1) continue;
    const name = trimmed.slice(0, eq).trim();
    const value = trimmed.slice(eq + 1).trim();
    cookies[name] = decodeURIComponent(value);
  }
  return cookies;
}

function decodeSerializedPayload(raw) {
  if (raw == null || raw === '') return null;
  const candidates = [];
  try {
    candidates.push(Buffer.from(raw, 'base64').toString('utf8'));
  } catch (_) {}
  try {
    candidates.push(Buffer.from(raw, 'base64url').toString('utf8'));
  } catch (_) {}
  candidates.push(raw);
  let lastErr;
  for (let i = 0; i < candidates.length; i++) {
    try {
      return serialize.unserialize(candidates[i]);
    } catch (err) {
      lastErr = err;
    }
  }
  throw lastErr;
}

function deserializeSessionFromCookie(cookieHeader, cookieName) {
  const name = cookieName == null ? 'session' : cookieName;
  const cookies = parseCookieHeader(cookieHeader);
  const raw = cookies[name];
  if (raw == null) return null;
  return decodeSerializedPayload(raw);
}

function serializeSessionForCookie(sessionObject) {
  const payload = serialize.serialize(sessionObject);
  return Buffer.from(payload, 'utf8').toString('base64url');
}

function buildUserSession({ userId, username, email, acl, metadata }) {
  const perms = {
    _acl: acl || Object.create(null),
    can(resource, action) {
      const rules = this._acl[resource];
      return Array.isArray(rules) && rules.indexOf(action) !== -1;
    },
    grant(resource, action) {
      if (!this._acl[resource]) this._acl[resource] = [];
      if (this._acl[resource].indexOf(action) === -1) this._acl[resource].push(action);
    },
    revoke(resource, action) {
      const rules = this._acl[resource];
      if (!Array.isArray(rules)) return;
      const idx = rules.indexOf(action);
      if (idx !== -1) rules.splice(idx, 1);
    },
  };

  const session = {
    _userId: userId,
    _username: username,
    _email: email,
    permissions: perms,
    metadata: Object.assign(
      {
        createdAt: Date.now(),
        lastSeen: Date.now(),
      },
      metadata || {}
    ),
    touch() {
      this.metadata.lastSeen = Date.now();
    },
    getUserId() {
      return this._userId;
    },
    getUsername() {
      return this._username;
    },
    getEmail() {
      return this._email;
    },
  };

  Object.defineProperty(session, 'userId', {
    enumerable: true,
    configurable: true,
    get() {
      return this._userId;
    },
    set(v) {
      this._userId = v;
    },
  });
  Object.defineProperty(session, 'username', {
    enumerable: true,
    configurable: true,
    get() {
      return this._username;
    },
    set(v) {
      this._username = v;
    },
  });
  Object.defineProperty(session, 'email', {
    enumerable: true,
    configurable: true,
    get() {
      return this._email;
    },
    set(v) {
      this._email = v;
    },
  });
  Object.defineProperty(session, 'displayLabel', {
    enumerable: false,
    configurable: true,
    get() {
      return this._username + ' <' + this._email + '>';
    },
  });

  return session;
}

module.exports = {
  deserializeSessionFromCookie,
  parseCookieHeader,
  decodeSerializedPayload,
  serializeSessionForCookie,
  buildUserSession,
};

if (require.main === module) {
  const s = buildUserSession({
    userId: 42,
    username: 'alice',
    email: 'alice@example.com',
    acl: { reports: ['read'], admin: ['write'] },
    metadata: { ip: '127.0.0.1' },
  });
  const cookieValue = serializeSessionForCookie(s);
  const header = 'session=' + encodeURIComponent(cookieValue);
  const restored = deserializeSessionFromCookie(header, 'session');
  if (!restored) throw new Error('expected session');
  restored.touch();
  if (typeof restored.permissions.can !== 'function') throw new Error('permissions methods missing');
  if (!restored.permissions.can('reports', 'read')) throw new Error('acl broken');
  if (restored.displayLabel.indexOf('alice') === -1) throw new Error('getter missing');
}
