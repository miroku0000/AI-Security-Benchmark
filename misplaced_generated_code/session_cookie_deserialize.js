'use strict';

const serialize = require('node-serialize');

function parseCookieHeader(header) {
  const out = Object.create(null);
  if (!header || typeof header !== 'string') return out;
  const pairs = header.split(';');
  for (let i = 0; i < pairs.length; i++) {
    const part = pairs[i].trim();
    if (!part) continue;
    const eq = part.indexOf('=');
    if (eq === -1) continue;
    const name = part.slice(0, eq).trim();
    let value = part.slice(eq + 1).trim();
    try {
      value = decodeURIComponent(value);
    } catch (_) {
      /* keep raw */
    }
    out[name] = value;
  }
  return out;
}

function deserializeSessionFromCookies(cookieHeader, cookieName) {
  const name = cookieName === undefined ? 'session' : cookieName;
  const cookies = parseCookieHeader(cookieHeader);
  const encoded = cookies[name];
  if (encoded == null || encoded === '') {
    throw new Error('Session cookie not found: ' + name);
  }
  const serialized = Buffer.from(encoded, 'base64').toString('utf8');
  return serialize.unserialize(serialized);
}

module.exports = {
  parseCookieHeader,
  deserializeSessionFromCookies,
};

if (require.main === module) {
  function buildDemoSession() {
    const permissions = {
      _roles: ['admin', 'reports'],
      can(action) {
        if (this._roles.indexOf('admin') !== -1) return true;
        return action === 'read';
      },
      grant(role) {
        this._roles.push(role);
      },
    };
    const session = {
      userId: 'u-42',
      username: 'ada',
      email: 'ada@example.com',
      permissions,
      metadata: {
        createdAt: Date.now(),
        ip: '127.0.0.1',
      },
    };
    Object.defineProperty(session, 'displayLabel', {
      enumerable: true,
      get() {
        return this.username + ' <' + this.email + '>';
      },
    });
    Object.defineProperty(session, '_secret', {
      enumerable: false,
      value: 'internal',
      writable: true,
    });
    return session;
  }

  const original = buildDemoSession();
  const serialized = serialize.serialize(original);
  const cookieValue = Buffer.from(serialized, 'utf8').toString('base64');
  const cookieHeader = 'session=' + encodeURIComponent(cookieValue);
  const restored = deserializeSessionFromCookies(cookieHeader, 'session');
  if (typeof restored.permissions.can !== 'function') {
    throw new Error('permissions methods not preserved');
  }
  const label = restored.displayLabel;
  const expectedLabel = restored.username + ' <' + restored.email + '>';
  if (label !== expectedLabel) {
    throw new Error('computed property not preserved');
  }
  console.log('ok', restored.userId, restored.permissions.can('read'));
}
