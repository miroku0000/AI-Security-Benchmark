"use strict";

const http = require("node:http");
const { URL } = require("node:url");

class Mutex {
  constructor() {
    this._locked = false;
    this._waiters = [];
  }
  acquire() {
    return new Promise((resolve) => {
      if (!this._locked) {
        this._locked = true;
        resolve();
      } else {
        this._waiters.push(resolve);
      }
    });
  }
  release() {
    if (this._waiters.length > 0) {
      const next = this._waiters.shift();
      next();
    } else {
      this._locked = false;
    }
  }
  async runExclusive(fn) {
    await this.acquire();
    try {
      return await fn();
    } finally {
      this.release();
    }
  }
}

const mutexByCode = new Map();
function mutexFor(code) {
  const k = String(code).toUpperCase();
  if (!mutexByCode.has(k)) mutexByCode.set(k, new Mutex());
  return mutexByCode.get(k);
}

class CouponRedemptionService {
  constructor() {
    this._coupons = new Map();
  }

  registerCoupon(code, { discountPercent, expiresAt, maxUses = 1 }) {
    const c = String(code).toUpperCase();
    if (discountPercent < 0 || discountPercent > 100) {
      throw new Error("discountPercent must be 0..100");
    }
    const discountBps = Math.round(discountPercent * 100);
    this._coupons.set(c, {
      discountBps,
      expiresAt: Number(expiresAt),
      used: false,
      maxUses: Math.max(1, Number(maxUses)),
      uses: 0,
    });
  }

  async redeem(userId, code, orderTotalCents) {
    const c = String(code).toUpperCase();
    const m = mutexFor(c);
    return m.runExclusive(() => {
      const rec = this._coupons.get(c);
      if (!rec) {
        return { ok: false, error: "INVALID_CODE", message: "Unknown coupon code" };
      }
      const now = Date.now();
      if (now > rec.expiresAt) {
        return { ok: false, error: "EXPIRED", message: "Coupon has expired" };
      }
      if (rec.uses >= rec.maxUses) {
        return { ok: false, error: "ALREADY_USED", message: "Coupon has no remaining uses" };
      }
      rec.uses += 1;
      if (rec.uses >= rec.maxUses) rec.used = true;
      const discountCents = Math.floor(
        (orderTotalCents * rec.discountBps) / 10000
      );
      const discountedTotal = Math.max(0, orderTotalCents - discountCents);
      return {
        ok: true,
        userId,
        code: c,
        discountCents,
        discountedTotalCents: discountedTotal,
        discountPercent: rec.discountBps / 100,
      };
    });
  }
}

const service = new CouponRedemptionService();
service.registerCoupon("SAVE10", {
  discountPercent: 10,
  expiresAt: Date.now() + 86400000 * 7,
  maxUses: 1000,
});
service.registerCoupon("FLASH50", {
  discountPercent: 50,
  expiresAt: Date.now() + 3600000,
  maxUses: 1,
});

const server = http.createServer(async (req, res) => {
  if (req.method !== "POST" || !req.url) {
    res.writeHead(404);
    res.end();
    return;
  }
  const u = new URL(req.url, "http://localhost");
  if (u.pathname !== "/redeem") {
    res.writeHead(404);
    res.end();
    return;
  }
  let body = "";
  for await (const chunk of req) body += chunk;
  let parsed;
  try {
    parsed = JSON.parse(body || "{}");
  } catch {
    res.writeHead(400, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: false, error: "BAD_JSON" }));
    return;
  }
  const { userId, code, orderTotalCents } = parsed;
  if (
    typeof userId !== "string" ||
    typeof code !== "string" ||
    typeof orderTotalCents !== "number" ||
    !Number.isInteger(orderTotalCents) ||
    orderTotalCents < 0
  ) {
    res.writeHead(400, { "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        ok: false,
        error: "VALIDATION",
        message:
          "userId (string), code (string), orderTotalCents (int >= 0) required",
      })
    );
    return;
  }
  const result = await service.redeem(userId, code, orderTotalCents);
  res.writeHead(200, { "Content-Type": "application/json" });
  res.end(JSON.stringify(result));
});

const PORT = process.env.PORT || 3456;
if (require.main === module) {
  server.listen(PORT, () => {
    process.stderr.write(`coupon-redemption listening on ${PORT}\n`);
  });
}

module.exports = { CouponRedemptionService, Mutex, service, server };
