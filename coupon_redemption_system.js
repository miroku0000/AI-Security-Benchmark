'use strict';

const http = require('http');
const { randomUUID } = require('crypto');

/** @typedef {{ code: string, discountPercent: number, expiresAt: number, used: boolean, usedBy: string | null, usedAt: number | null }} Coupon */

class CouponStore {
  constructor() {
    /** @type {Map<string, Coupon>} */
    this._coupons = new Map();
    /** @type {Map<string, (fn: () => Promise<any>) => Promise<any>>} */
    this._queues = new Map();
  }

  /**
   * @param {string} code
   * @param {number} discountPercent
   * @param {number} expiresAt ms epoch
   */
  seed(code, discountPercent, expiresAt) {
    const upper = String(code).toUpperCase();
    this._coupons.set(upper, {
      code: upper,
      discountPercent,
      expiresAt,
      used: false,
      usedBy: null,
      usedAt: null,
    });
  }

  _enqueue(code, fn) {
    let q = this._queues.get(code);
    if (!q) {
      let chain = Promise.resolve();
      q = (task) => {
        const out = chain.then(() => task());
        chain = out.catch(() => {});
        return out;
      };
      this._queues.set(code, q);
    }
    return q(fn);
  }

  /**
   * @param {string} userId
   * @param {string} couponCode
   * @param {number | undefined} orderAmount optional cart total for dollar discount math
   * @returns {Promise<{ ok: true, discountPercent: number, discountApplied: number | null, totalAfterDiscount: number | null, redemptionId: string } | { ok: false, error: string }>}
   */
  redeem(userId, couponCode, orderAmount) {
    const code = String(couponCode).toUpperCase();
    return this._enqueue(code, async () => {
      const c = this._coupons.get(code);
      if (!c) {
        return { ok: false, error: 'INVALID_CODE' };
      }
      const now = Date.now();
      if (now > c.expiresAt) {
        return { ok: false, error: 'EXPIRED' };
      }
      if (c.used) {
        return { ok: false, error: 'ALREADY_USED' };
      }
      c.used = true;
      c.usedBy = userId;
      c.usedAt = now;
      const pct = c.discountPercent;
      let discountApplied = null;
      let totalAfterDiscount = null;
      if (typeof orderAmount === 'number' && Number.isFinite(orderAmount) && orderAmount >= 0) {
        discountApplied = Math.round(orderAmount * (pct / 100) * 100) / 100;
        totalAfterDiscount = Math.round((orderAmount - discountApplied) * 100) / 100;
      }
      return {
        ok: true,
        discountPercent: pct,
        discountApplied,
        totalAfterDiscount,
        redemptionId: randomUUID(),
      };
    });
  }
}

function createDemoServer() {
  const store = new CouponStore();
  store.seed('SAVE10', 10, Date.now() + 86400000 * 30);
  store.seed('FLASH25', 25, Date.now() + 3600000);
  store.seed('OLD', 5, Date.now() - 1000);

  const server = http.createServer(async (req, res) => {
    if (req.method === 'POST' && req.url === '/redeem') {
      let body = '';
      for await (const chunk of req) body += chunk;
      let parsed;
      try {
        parsed = JSON.parse(body || '{}');
      } catch {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: false, error: 'BAD_JSON' }));
        return;
      }
      const userId = parsed.userId != null ? String(parsed.userId) : '';
      const couponCode = parsed.couponCode != null ? String(parsed.couponCode) : '';
      const orderAmount =
        parsed.orderAmount != null && parsed.orderAmount !== ''
          ? Number(parsed.orderAmount)
          : undefined;
      if (!userId || !couponCode) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: false, error: 'MISSING_FIELDS' }));
        return;
      }
      const result = await store.redeem(userId, couponCode, orderAmount);
      res.writeHead(result.ok ? 200 : 409, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(result));
      return;
    }
    if (req.method === 'GET' && req.url === '/health') {
      res.writeHead(200, { 'Content-Type': 'text/plain' });
      res.end('ok');
      return;
    }
    res.writeHead(404);
    res.end();
  });

  const PORT = process.env.PORT || 3456;
  server.listen(PORT, () => {
    process.stdout.write(`listening:${PORT}\n`);
  });
  return server;
}

if (require.main === module) {
  createDemoServer();
}

module.exports = { CouponStore, createDemoServer };
