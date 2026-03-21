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

function deserializeSessionFromCookie(cookieHeader, cookieName) {
  const name = cookieName == null ? 'session' : cookieName;
  const cookies = parseCookieHeader(cookieHeader);
  const raw = cookies[name];
  if (raw == null) return null;
  const payloads = [];
  try {
    payloads.push(Buffer.from(raw, 'base64').toString('utf8'));
  } catch (_) {}
  try {
    payloads.push(Buffer.from(raw, 'base64url').toString('utf8'));
  } catch (_) {}
  payloads.push(raw);
  let lastErr;
  for (let i = 0; i < payloads.length; i++) {
    try {
      return serialize.unserialize(payloads[i]);
    } catch (err) {
      lastErr = err;
    }
  }
  throw lastErr;
}

module.exports = {
  deserializeSessionFromCookie,
  parseCookieHeader,
};
