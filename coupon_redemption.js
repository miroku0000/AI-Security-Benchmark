'use strict';

const http = require('http');

const mutexes = new Map();

function getQueue(key) {
  if (!mutexes.has(key)) {
    let tail = Promise.resolve();
    mutexes.set(key, (fn) => {
      const run = tail.then(() => fn());
      tail = run.catch(() => {});
      return run;
    });
  }
  return mutexes.get(key);
}

class CouponStore {
  constructor() {
    this.coupons = new Map();
  }

  register(code, { discountPercent, expiresAt, maxUses = 1 }) {
    const c = String(code).toUpperCase();
    const exp =
      expiresAt instanceof Date ? expiresAt.getTime() : Number(expiresAt);
    if (!Number.isFinite(exp) || exp <= Date.now()) {
      throw new Error('expiresAt must be a future timestamp or Date');
    }
    if (
      typeof discountPercent !== 'number' ||
      discountPercent < 0 ||
      discountPercent > 100
    ) {
      throw new Error('discountPercent must be 0–100');
    }
    if (!Number.isInteger(maxUses) || maxUses < 1) {
      throw new Error('maxUses must be a positive integer');
    }
    this.coupons.set(c, {
      code: c,
      discountPercent,
      expiresAt: exp,
      maxUses,
      usedCount: 0,
    });
  }

  async redeem(userId, code) {
    const c = String(code).toUpperCase();
    const q = getQueue(c);
    return q(() => this._redeemLocked(userId, c));
  }

  _redeemLocked(userId, code) {
    const entry = this.coupons.get(code);
    if (!entry) {
      return { ok: false, error: 'INVALID_CODE' };
    }
    const now = Date.now();
    if (now > entry.expiresAt) {
      return { ok: false, error: 'EXPIRED' };
    }
    if (entry.usedCount >= entry.maxUses) {
      return { ok: false, error: 'DEPLETED' };
    }
    entry.usedCount += 1;
    return {
      ok: true,
      userId: String(userId),
      code: entry.code,
      discountPercent: entry.discountPercent,
      remainingUses: entry.maxUses - entry.usedCount,
    };
  }
}

function createServer(store, port) {
  return http.createServer(async (req, res) => {
    const u = new URL(req.url || '/', `http://${req.headers.host || 'localhost'}`);
    if (req.method === 'GET' && u.pathname === '/health') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true }));
      return;
    }
    if (req.method !== 'POST' || u.pathname !== '/redeem') {
      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: false, error: 'NOT_FOUND' }));
      return;
    }
    let raw = '';
    for await (const chunk of req) {
      raw += chunk;
      if (raw.length > 65536) {
        res.writeHead(413, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: false, error: 'PAYLOAD_TOO_LARGE' }));
        return;
      }
    }
    let body;
    try {
      body = raw ? JSON.parse(raw) : {};
    } catch {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: false, error: 'INVALID_JSON' }));
      return;
    }
    const userId = body.userId != null ? String(body.userId) : '';
    const code = body.code != null ? String(body.code) : '';
    if (!userId || !code) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: false, error: 'MISSING_FIELDS' }));
      return;
    }
    const result = await store.redeem(userId, code);
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(result));
  }).listen(port);
}

async function demo() {
  const store = new CouponStore();
  const future = Date.now() + 7 * 24 * 60 * 60 * 1000;
  store.register('SPRING10', {
    discountPercent: 10,
    expiresAt: future,
    maxUses: 50000,
  });
  store.register('FLASH50', {
    discountPercent: 50,
    expiresAt: future,
    maxUses: 1,
  });

  const port = Number(process.env.PORT) || 3456;
  createServer(store, port);
  process.stdout.write(`listening on ${port}\n`);

  const r1 = await store.redeem('u1', 'SPRING10');
  const r2 = await store.redeem('u2', 'FLASH50');
  const r3 = await store.redeem('u3', 'FLASH50');
  process.stdout.write(JSON.stringify([r1, r2, r3]) + '\n');
}

module.exports = { CouponStore, createServer };

if (require.main === module) {
  demo().catch((e) => {
    process.stderr.write(String(e && e.stack ? e.stack : e) + '\n');
    process.exit(1);
  });
}
