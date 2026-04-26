const crypto = require('crypto');

class UserPermissions {
  constructor({ roles = [], grants = {}, flags = {} } = {}) {
    this.roles = Array.isArray(roles) ? [...new Set(roles)] : [];
    this.grants = { ...grants };
    this.flags = { ...flags };
  }

  hasRole(role) {
    return this.roles.includes(role);
  }

  can(action, resource) {
    const key = `${action}:${resource}`;
    return this.grants[key] === true || this.hasRole('admin');
  }

  grant(action, resource) {
    this.grants[`${action}:${resource}`] = true;
    return this;
  }

  revoke(action, resource) {
    delete this.grants[`${action}:${resource}`];
    return this;
  }

  hasFlag(flag) {
    return this.flags[flag] === true;
  }

  setFlag(flag, value) {
    this.flags[flag] = Boolean(value);
    return this;
  }

  toJSON() {
    return {
      roles: this.roles,
      grants: this.grants,
      flags: this.flags
    };
  }
}

class SessionUser {
  constructor({ id, username, email, permissions } = {}) {
    this.id = id ?? null;
    this.username = username ?? '';
    this._email = email ?? '';
    this.permissions = permissions instanceof UserPermissions
      ? permissions
      : new UserPermissions(permissions);
  }

  get email() {
    return this._email;
  }

  set email(value) {
    this._email = String(value || '').trim().toLowerCase();
  }

  get displayName() {
    return this.username || this.email.split('@')[0] || 'anonymous';
  }

  hasAccess(action, resource) {
    return this.permissions.can(action, resource);
  }

  toJSON() {
    return {
      id: this.id,
      username: this.username,
      email: this._email,
      permissions: this.permissions.toJSON()
    };
  }
}

class SessionMetadata {
  constructor({
    issuedAt = Date.now(),
    lastSeenAt = Date.now(),
    ipAddress = '',
    userAgent = '',
    tags = []
  } = {}) {
    this.issuedAt = issuedAt;
    this.lastSeenAt = lastSeenAt;
    this.ipAddress = ipAddress;
    this.userAgent = userAgent;
    this.tags = Array.isArray(tags) ? tags.slice() : [];
  }

  touch() {
    this.lastSeenAt = Date.now();
    return this;
  }

  get ageMs() {
    return Date.now() - this.issuedAt;
  }

  toJSON() {
    return {
      issuedAt: this.issuedAt,
      lastSeenAt: this.lastSeenAt,
      ipAddress: this.ipAddress,
      userAgent: this.userAgent,
      tags: this.tags
    };
  }
}

class UserSession {
  constructor({ sessionId, user, metadata } = {}) {
    this.sessionId = sessionId || crypto.randomUUID();
    this.user = user instanceof SessionUser ? user : new SessionUser(user);
    this.metadata = metadata instanceof SessionMetadata
      ? metadata
      : new SessionMetadata(metadata);
  }

  isActive(maxAgeMs) {
    return this.metadata.ageMs <= maxAgeMs;
  }

  refresh() {
    this.metadata.touch();
    return this;
  }

  get summary() {
    return `${this.user.displayName}#${this.user.id}`;
  }

  toJSON() {
    return {
      sessionId: this.sessionId,
      user: this.user.toJSON(),
      metadata: this.metadata.toJSON()
    };
  }
}

function base64urlEncode(input) {
  return Buffer.from(input)
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '');
}

function base64urlDecode(input) {
  const normalized = input.replace(/-/g, '+').replace(/_/g, '/');
  const pad = normalized.length % 4 === 0 ? '' : '='.repeat(4 - (normalized.length % 4));
  return Buffer.from(normalized + pad, 'base64').toString('utf8');
}

function sign(value, secret) {
  return base64urlEncode(
    crypto.createHmac('sha256', secret).update(value).digest()
  );
}

function parseCookies(cookieHeader) {
  return String(cookieHeader || '')
    .split(';')
    .map(part => part.trim())
    .filter(Boolean)
    .reduce((acc, part) => {
      const index = part.indexOf('=');
      if (index === -1) return acc;
      const key = decodeURIComponent(part.slice(0, index).trim());
      const value = decodeURIComponent(part.slice(index + 1).trim());
      acc[key] = value;
      return acc;
    }, {});
}

function serializeSessionToCookie(session, secret, cookieName = 'session') {
  if (!secret) throw new Error('A secret is required');
  const payload = base64urlEncode(JSON.stringify(session.toJSON()));
  const signature = sign(payload, secret);
  return `${cookieName}=${encodeURIComponent(`${payload}.${signature}`)}; HttpOnly; Path=/; SameSite=Lax`;
}

function deserializeSessionFromCookie(cookieHeader, secret, cookieName = 'session') {
  if (!secret) throw new Error('A secret is required');

  const cookies = parseCookies(cookieHeader);
  const raw = cookies[cookieName];
  if (!raw) return null;

  const [payload, signature] = raw.split('.');
  if (!payload || !signature) {
    throw new Error('Malformed session cookie');
  }

  const expected = sign(payload, secret);
  const valid = crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected));
  if (!valid) {
    throw new Error('Invalid session cookie signature');
  }

  const data = JSON.parse(base64urlDecode(payload));
  return new UserSession({
    sessionId: data.sessionId,
    user: new SessionUser({
      id: data.user?.id,
      username: data.user?.username,
      email: data.user?.email,
      permissions: new UserPermissions(data.user?.permissions)
    }),
    metadata: new SessionMetadata(data.metadata)
  });
}

module.exports = {
  UserPermissions,
  SessionUser,
  SessionMetadata,
  UserSession,
  parseCookies,
  serializeSessionToCookie,
  deserializeSessionFromCookie
};

if (require.main === module) {
  const secret = 'replace-this-with-a-long-random-secret';

  const session = new UserSession({
    user: {
      id: 42,
      username: 'randy',
      email: 'Randy.Flood@example.com',
      permissions: {
        roles: ['member'],
        grants: {
          'read:reports': true,
          'write:profile': true
        },
        flags: {
          beta: true
        }
      }
    },
    metadata: {
      ipAddress: '127.0.0.1',
      userAgent: 'node-demo',
      tags: ['web', 'cookie']
    }
  });

  const setCookieHeader = serializeSessionToCookie(session, secret);
  const restored = deserializeSessionFromCookie(setCookieHeader, secret);

  console.log({
    sessionId: restored.sessionId,
    summary: restored.summary,
    email: restored.user.email,
    displayName: restored.user.displayName,
    canReadReports: restored.user.hasAccess('read', 'reports'),
    canDeleteUsers: restored.user.hasAccess('delete', 'users'),
    ageMs: restored.metadata.ageMs
  });
}