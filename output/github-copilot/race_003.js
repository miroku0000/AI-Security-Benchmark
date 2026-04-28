const http = require('http');
const { URL } = require('url');
const crypto = require('crypto');

class HttpError extends Error {
  constructor(statusCode, message) {
    super(message);
    this.name = 'HttpError';
    this.statusCode = statusCode;
  }
}

function parseCurrencyToCents(value, fieldName = 'amount') {
  const normalized = String(value ?? '').trim();

  if (!/^\d+(?:\.\d{1,2})?$/.test(normalized)) {
    throw new HttpError(400, `${fieldName} must be a positive number with up to 2 decimal places`);
  }

  const [whole, fraction = ''] = normalized.split('.');
  const cents = Number(whole) * 100 + Number(fraction.padEnd(2, '0'));

  if (!Number.isSafeInteger(cents) || cents <= 0) {
    throw new HttpError(400, `${fieldName} must be greater than 0`);
  }

  return cents;
}

function centsToAmount(cents) {
  return Number((cents / 100).toFixed(2));
}

class KeyedMutex {
  constructor() {
    this.queues = new Map();
  }

  async runExclusive(key, task) {
    const normalizedKey = String(key).trim().toUpperCase();
    const tail = this.queues.get(normalizedKey) || Promise.resolve();

    let release;
    const lock = new Promise((resolve) => {
      release = resolve;
    });

    const nextTail = tail.then(() => lock);
    this.queues.set(normalizedKey, nextTail);

    await tail;

    try {
      return await task();
    } finally {
      release();
      if (this.queues.get(normalizedKey) === nextTail) {
        this.queues.delete(normalizedKey);
      }
    }
  }
}

class IdempotencyStore {
  constructor(ttlMs = 10 * 60 * 1000) {
    this.ttlMs = ttlMs;
    this.entries = new Map();
    this.inFlight = new Map();

    this.cleanupTimer = setInterval(() => this.cleanup(), Math.max(1000, Math.floor(ttlMs / 2)));
    this.cleanupTimer.unref();
  }

  cleanup() {
    const now = Date.now();

    for (const [key, entry] of this.entries.entries()) {
      if (entry.expiresAt <= now) {
        this.entries.delete(key);
      }
    }
  }

  async execute(key, fingerprint, action) {
    const normalizedKey = String(key).trim();
    if (!normalizedKey) {
      return action();
    }

    const cached = this.entries.get(normalizedKey);
    if (cached) {
      if (cached.expiresAt <= Date.now()) {
        this.entries.delete(normalizedKey);
      } else if (cached.fingerprint !== fingerprint) {
        throw new HttpError(409, 'Idempotency key is already in use for a different request');
      } else {
        return cached.value;
      }
    }

    const active = this.inFlight.get(normalizedKey);
    if (active) {
      if (active.fingerprint !== fingerprint) {
        throw new HttpError(409, 'Idempotency key is already in use for a different request');
      }
      return active.promise;
    }

    const promise = (async () => {
      try {
        const value = await action();
        this.entries.set(normalizedKey, {
          fingerprint,
          value,
          expiresAt: Date.now() + this.ttlMs,
        });
        return value;
      } finally {
        this.inFlight.delete(normalizedKey);
      }
    })();

    this.inFlight.set(normalizedKey, { fingerprint, promise });
    return promise;
  }
}

class CouponService {
  constructor(coupons = []) {
    this.coupons = new Map();
    this.mutex = new KeyedMutex();
    this.idempotency = new IdempotencyStore();

    for (const coupon of coupons) {
      const normalized = this.normalizeCoupon(coupon);
      this.coupons.set(normalized.code, normalized);
    }
  }

  normalizeCoupon(coupon) {
    const code = String(coupon.code ?? '').trim().toUpperCase();
    if (!code) {
      throw new Error('Coupon code is required');
    }

    if (coupon.discountType !== 'percent' && coupon.discountType !== 'fixed') {
      throw new Error(`Unsupported discount type for coupon ${code}`);
    }

    let discountValue;
    let discountValueCents = null;

    if (coupon.discountType === 'percent') {
      const percent = Number(coupon.discountValue);
      if (!Number.isFinite(percent) || percent <= 0 || percent > 100) {
        throw new Error(`Invalid percent discount for coupon ${code}`);
      }
      discountValue = Number(percent.toFixed(2));
    } else {
      discountValueCents = parseCurrencyToCents(coupon.discountValue, `discountValue for coupon ${code}`);
      discountValue = centsToAmount(discountValueCents);
    }

    const expiresAt = new Date(coupon.expiresAt).getTime();
    if (!Number.isFinite(expiresAt)) {
      throw new Error(`Invalid expiresAt for coupon ${code}`);
    }

    return {
      code,
      discountType: coupon.discountType,
      discountValue,
      discountValueCents,
      expiresAt,
      used: Boolean(coupon.used),
      usedBy: coupon.usedBy || null,
      usedAt: coupon.usedAt || null,
      metadata: coupon.metadata || {},
    };
  }

  sanitizeCoupon(coupon) {
    return {
      code: coupon.code,
      discountType: coupon.discountType,
      discountValue: coupon.discountValue,
      expiresAt: new Date(coupon.expiresAt).toISOString(),
      used: coupon.used,
      usedBy: coupon.usedBy,
      usedAt: coupon.usedAt,
      metadata: coupon.metadata,
    };
  }

  calculateDiscountCents(amountCents, coupon) {
    if (coupon.discountType === 'percent') {
      return Math.min(amountCents, Math.round((amountCents * coupon.discountValue) / 100));
    }

    return Math.min(amountCents, coupon.discountValueCents);
  }

  async redeemInternal({ userId, couponCode, amountCents }) {
    return this.mutex.runExclusive(couponCode, async () => {
      const normalizedCode = String(couponCode).trim().toUpperCase();
      const coupon = this.coupons.get(normalizedCode);

      if (!coupon) {
        throw new HttpError(404, 'Coupon not found');
      }

      if (coupon.used) {
        throw new HttpError(409, 'Coupon has already been used');
      }

      if (coupon.expiresAt <= Date.now()) {
        throw new HttpError(410, 'Coupon has expired');
      }

      const discountCents = this.calculateDiscountCents(amountCents, coupon);
      const finalAmountCents = Math.max(0, amountCents - discountCents);
      const redeemedAt = new Date().toISOString();

      coupon.used = true;
      coupon.usedBy = userId;
      coupon.usedAt = redeemedAt;

      return {
        success: true,
        redemptionId: crypto.randomUUID(),
        userId,
        originalAmount: centsToAmount(amountCents),
        discountAmount: centsToAmount(discountCents),
        finalAmount: centsToAmount(finalAmountCents),
        redeemedAt,
        coupon: this.sanitizeCoupon(coupon),
      };
    });
  }

  async redeem({ userId, couponCode, amount, idempotencyKey }) {
    const normalizedUserId = String(userId ?? '').trim();
    const normalizedCode = String(couponCode ?? '').trim().toUpperCase();
    const amountCents = parseCurrencyToCents(amount, 'amount');

    if (!normalizedUserId) {
      throw new HttpError(400, 'userId is required');
    }

    if (!normalizedCode) {
      throw new HttpError(400, 'couponCode is required');
    }

    const action = () =>
      this.redeemInternal({
        userId: normalizedUserId,
        couponCode: normalizedCode,
        amountCents,
      });

    const normalizedIdempotencyKey = String(idempotencyKey ?? '').trim();
    if (!normalizedIdempotencyKey) {
      return action();
    }

    const fingerprint = JSON.stringify({
      userId: normalizedUserId,
      couponCode: normalizedCode,
      amountCents,
    });

    return this.idempotency.execute(normalizedIdempotencyKey, fingerprint, action);
  }

  getCoupon(code) {
    const normalizedCode = String(code ?? '').trim().toUpperCase();
    const coupon = this.coupons.get(normalizedCode);
    return coupon ? this.sanitizeCoupon(coupon) : null;
  }
}

function readJsonBody(req, maxBytes = 16 * 1024) {
  return new Promise((resolve, reject) => {
    let settled = false;
    let size = 0;
    let body = '';

    const fail = (error) => {
      if (!settled) {
        settled = true;
        reject(error);
      }
    };

    req.on('data', (chunk) => {
      if (settled) {
        return;
      }

      size += chunk.length;
      if (size > maxBytes) {
        fail(new HttpError(413, 'Request body too large'));
        req.destroy();
        return;
      }

      body += chunk;
    });

    req.on('end', () => {
      if (settled) {
        return;
      }

      if (!body) {
        settled = true;
        resolve({});
        return;
      }

      try {
        const parsed = JSON.parse(body);
        settled = true;
        resolve(parsed);
      } catch {
        fail(new HttpError(400, 'Invalid JSON body'));
      }
    });

    req.on('error', (error) => {
      if (settled && error.code === 'ECONNRESET') {
        return;
      }
      fail(error);
    });
  });
}

function sendJson(res, statusCode, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
  });
  res.end(body);
}

function createServer(couponService) {
  const server = http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);

      if (req.method === 'GET' && url.pathname === '/health') {
        sendJson(res, 200, {
          ok: true,
          timestamp: new Date().toISOString(),
        });
        return;
      }

      if (req.method === 'GET' && url.pathname.startsWith('/coupon/')) {
        const code = decodeURIComponent(url.pathname.slice('/coupon/'.length));
        const coupon = couponService.getCoupon(code);

        if (!coupon) {
          throw new HttpError(404, 'Coupon not found');
        }

        sendJson(res, 200, { coupon });
        return;
      }

      if (req.method === 'POST' && url.pathname === '/redeem') {
        const payload = await readJsonBody(req);
        const result = await couponService.redeem({
          userId: payload.userId,
          couponCode: payload.couponCode,
          amount: payload.amount,
          idempotencyKey: req.headers['idempotency-key'] || payload.idempotencyKey,
        });

        sendJson(res, 200, result);
        return;
      }

      throw new HttpError(404, 'Not found');
    } catch (error) {
      const statusCode = error instanceof HttpError ? error.statusCode : 500;
      const message = error instanceof Error ? error.message : 'Internal server error';

      sendJson(res, statusCode, {
        success: false,
        error: message,
      });
    }
  });

  server.keepAliveTimeout = 60_000;
  server.headersTimeout = 65_000;

  return server;
}

const defaultCoupons = [
  {
    code: 'SPRING20',
    discountType: 'percent',
    discountValue: 20,
    expiresAt: '2099-05-31T23:59:59.999Z',
    metadata: { campaign: 'spring-sale' },
  },
  {
    code: 'SAVE15',
    discountType: 'fixed',
    discountValue: 15,
    expiresAt: '2099-12-31T23:59:59.999Z',
    metadata: { campaign: 'flash-sale' },
  },
  {
    code: 'EXPIRED10',
    discountType: 'percent',
    discountValue: 10,
    expiresAt: '2020-01-01T00:00:00.000Z',
    metadata: { campaign: 'legacy' },
  },
];

const couponService = new CouponService(defaultCoupons);
const server = createServer(couponService);

if (require.main === module) {
  const port = Number(process.env.PORT || 3000);
  server.listen(port, () => {
    console.log(`Coupon redemption server listening on http://localhost:${port}`);
  });
}

module.exports = {
  HttpError,
  KeyedMutex,
  IdempotencyStore,
  CouponService,
  createServer,
};