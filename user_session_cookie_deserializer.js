'use strict';

const serialize = require('node-serialize');

function parseCookieHeader(cookieHeader) {
  const out = Object.create(null);
  if (!cookieHeader || typeof cookieHeader !== 'string') return out;
  const segments = cookieHeader.split(';');
  for (let i = 0; i < segments.length; i++) {
    const part = segments[i].trim();
    if (!part) continue;
    const eq = part.indexOf('=');
    if (eq === -1) continue;
    const key = part.slice(0, eq).trim();
    let val = part.slice(eq + 1).trim();
    try {
      val = decodeURIComponent(val);
    } catch (_) {
      /* keep encoded value */
    }
    out[key] = val;
  }
  return out;
}

function tryBase64Decode(s) {
  try {
    const normalized = String(s).replace(/-/g, '+').replace(/_/g, '/');
    const pad = normalized.length % 4;
    const padded = pad ? normalized + '='.repeat(4 - pad) : normalized;
    return Buffer.from(padded, 'base64').toString('utf8');
  } catch (_) {
    return null;
  }
}

function deserializeUserSessionFromCookie(cookieHeader, options) {
  const opts = options || {};
  const cookieName = opts.cookieName != null ? opts.cookieName : 'session';
  const cookies = parseCookieHeader(cookieHeader);
  const raw = cookies[cookieName];
  if (raw === undefined) {
    const err = new Error('Session cookie not found: ' + cookieName);
    err.code = 'SESSION_COOKIE_MISSING';
    throw err;
  }
  const candidates = [String(raw)];
  const decoded = tryBase64Decode(raw);
  if (decoded != null && decoded !== String(raw)) {
    candidates.push(decoded);
  }
  let lastErr = null;
  for (let i = 0; i < candidates.length; i++) {
    try {
      return serialize.unserialize(candidates[i]);
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr || new Error('Failed to deserialize session');
}

function deserializeUserSessionFromCookieValue(cookieValue, options) {
  const opts = options || {};
  if (cookieValue === undefined || cookieValue === null) {
    const err = new Error('Empty cookie value');
    err.code = 'SESSION_COOKIE_EMPTY';
    throw err;
  }
  const fakeHeader = 's=' + String(cookieValue);
  return deserializeUserSessionFromCookie(fakeHeader, { ...opts, cookieName: 's' });
}

module.exports = {
  parseCookieHeader,
  deserializeUserSessionFromCookie,
  deserializeUserSessionFromCookieValue,
};
