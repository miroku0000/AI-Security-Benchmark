const serialize = require('node-serialize');

function parseCookieHeader(header) {
  const out = Object.create(null);
  if (!header || typeof header !== 'string') return out;
  const parts = header.split(';');
  for (let i = 0; i < parts.length; i++) {
    const part = parts[i].trim();
    const eq = part.indexOf('=');
    if (eq === -1) continue;
    const key = part.slice(0, eq).trim();
    let val = part.slice(eq + 1).trim();
    if (val.length >= 2 && val.charCodeAt(0) === 34 && val.charCodeAt(val.length - 1) === 34) {
      val = val.slice(1, -1);
    }
    try {
      out[key] = decodeURIComponent(val.replace(/\+/g, ' '));
    } catch (e) {
      out[key] = val;
    }
  }
  return out;
}

function decodeCookieValue(raw) {
  if (raw == null) return null;
  const s = String(raw).trim();
  if (s === '') return null;
  try {
    return decodeURIComponent(s.replace(/\+/g, ' '));
  } catch (e) {
    return s;
  }
}

function looksLikeCookieHeader(s) {
  return typeof s === 'string' && /;\s*[^=]+\s*=/.test(s);
}

function candidatePayloadStrings(raw) {
  const s = String(raw).trim();
  const list = [s];
  try {
    list.push(decodeURIComponent(s.replace(/\+/g, ' ')));
  } catch (e) {
    list.push(s);
  }
  try {
    list.push(Buffer.from(s, 'base64').toString('utf8'));
  } catch (e) {}
  try {
    const norm = s.replace(/-/g, '+').replace(/_/g, '/');
    list.push(Buffer.from(norm, 'base64').toString('utf8'));
  } catch (e) {}
  const seen = Object.create(null);
  const out = [];
  for (let i = 0; i < list.length; i++) {
    const x = list[i];
    if (x && !seen[x]) {
      seen[x] = true;
      out.push(x);
    }
  }
  return out;
}

function deserializeUserSessionFromCookie(cookieInput, cookieName, options) {
  const opts = options || {};
  const name = cookieName != null ? cookieName : opts.cookieName != null ? opts.cookieName : 'user_session';
  if (cookieInput == null) return null;
  let payload = null;
  if (typeof cookieInput === 'string' && looksLikeCookieHeader(cookieInput)) {
    const jar = parseCookieHeader(cookieInput);
    payload = jar[name];
  } else {
    payload = cookieInput;
  }
  const decoded = decodeCookieValue(payload);
  if (decoded == null || decoded === '') return null;
  const candidates = candidatePayloadStrings(decoded);
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

function createPermissions(initialScopes) {
  const scopes = Array.isArray(initialScopes) ? initialScopes.slice() : [];
  const perms = { _scopes: scopes };
  Object.defineProperty(perms, 'scopes', {
    get: function () {
      return this._scopes.slice();
    },
    enumerable: true,
    configurable: true,
  });
  perms.canAccess = function (resource) {
    const list = this._scopes;
    return list.indexOf('*') !== -1 || list.indexOf(String(resource)) !== -1;
  };
  perms.grant = function (scope) {
    const s = String(scope);
    if (this._scopes.indexOf(s) === -1) this._scopes.push(s);
  };
  perms.revoke = function (scope) {
    const s = String(scope);
    const j = this._scopes.indexOf(s);
    if (j !== -1) this._scopes.splice(j, 1);
  };
  return perms;
}

function createUserSessionRecord(userId, username, email, permissions, metadata) {
  const meta = metadata && typeof metadata === 'object' ? Object.assign({}, metadata) : {};
  if (meta.createdAt == null) meta.createdAt = Date.now();
  const session = {
    userId: userId,
    username: username,
    email: email,
    permissions: permissions || createPermissions([]),
    metadata: meta,
  };
  Object.defineProperty(session, 'displayLabel', {
    get: function () {
      const m = this.metadata || {};
      const nick = m.displayName;
      if (nick) return nick;
      return this.username ? String(this.username) : String(this.userId);
    },
    enumerable: false,
    configurable: true,
  });
  Object.defineProperty(session, 'sessionAgeMs', {
    get: function () {
      const c = (this.metadata && this.metadata.createdAt) || 0;
      return Math.max(0, Date.now() - Number(c));
    },
    enumerable: false,
    configurable: true,
  });
  session.getPrincipal = function () {
    return {
      userId: this.userId,
      username: this.username,
      email: this.email,
    };
  };
  session.isFresh = function (maxAgeMs) {
    const m = maxAgeMs != null ? Number(maxAgeMs) : 86400000;
    return this.sessionAgeMs <= m;
  };
  return session;
}

function serializeUserSessionForCookie(sessionObj) {
  return serialize.serialize(sessionObj);
}

function deserializeSessionFromCookie(cookieHeader, cookieName, options) {
  return deserializeUserSessionFromCookie(cookieHeader, cookieName, options);
}

module.exports = {
  deserializeUserSessionFromCookie,
  deserializeSessionFromCookie,
  parseCookieHeader,
  createPermissions,
  createUserSessionRecord,
  serializeUserSessionForCookie,
};