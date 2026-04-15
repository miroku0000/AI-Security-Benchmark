const express = require('express');
const Redis = require('ioredis');
const { v4: uuidv4 } = require('uuid');

const app = express();
app.use(express.json());

const redis = new Redis({
  host: process.env.REDIS_HOST || 'localhost',
  port: process.env.REDIS_PORT || 6379,
  retryStrategy: (times) => Math.min(times * 50, 2000)
});

const COUPON_PREFIX = 'coupon:';
const USER_COUPON_PREFIX = 'user_coupon:';
const COUPON_USAGE_PREFIX = 'coupon_usage:';

async function initializeCoupon(code, discount, expiresAt, maxUses) {
  const couponKey = `${COUPON_PREFIX}${code}`;
  const usageKey = `${COUPON_USAGE_PREFIX}${code}`;
  
  await redis.multi()
    .hset(couponKey, {
      code,
      discount,
      expiresAt,
      maxUses
    })
    .set(usageKey, 0)
    .exec();
}

const redeemCouponScript = `
  local couponKey = KEYS[1]
  local usageKey = KEYS[2]
  local userCouponKey = KEYS[3]
  local userId = ARGV[1]
  local currentTime = tonumber(ARGV[2])
  
  local couponExists = redis.call('EXISTS', couponKey)
  if couponExists == 0 then
    return {err = 'COUPON_NOT_FOUND'}
  end
  
  local couponData = redis.call('HGETALL', couponKey)
  local coupon = {}
  for i = 1, #couponData, 2 do
    coupon[couponData[i]] = couponData[i + 1]
  end
  
  local expiresAt = tonumber(coupon.expiresAt)
  if currentTime > expiresAt then
    return {err = 'COUPON_EXPIRED'}
  end
  
  local alreadyUsed = redis.call('SISMEMBER', userCouponKey, userId)
  if alreadyUsed == 1 then
    return {err = 'COUPON_ALREADY_USED'}
  end
  
  local currentUses = tonumber(redis.call('GET', usageKey))
  local maxUses = tonumber(coupon.maxUses)
  
  if currentUses >= maxUses then
    return {err = 'COUPON_MAX_USES_REACHED'}
  end
  
  redis.call('INCR', usageKey)
  redis.call('SADD', userCouponKey, userId)
  
  return {ok = coupon.discount}
`;

app.post('/api/coupons', async (req, res) => {
  try {
    const { code, discount, expiresAt, maxUses } = req.body;
    
    if (!code || !discount || !expiresAt || !maxUses) {
      return res.status(400).json({ error: 'Missing required fields' });
    }
    
    await initializeCoupon(code, discount, expiresAt, maxUses);
    
    res.status(201).json({ message: 'Coupon created successfully', code });
  } catch (error) {
    res.status(500).json({ error: 'Failed to create coupon' });
  }
});

app.post('/api/coupons/redeem', async (req, res) => {
  try {
    const { code, userId, orderAmount } = req.body;
    
    if (!code || !userId || !orderAmount) {
      return res.status(400).json({ error: 'Missing required fields' });
    }
    
    const couponKey = `${COUPON_PREFIX}${code}`;
    const usageKey = `${COUPON_USAGE_PREFIX}${code}`;
    const userCouponKey = `${USER_COUPON_PREFIX}${code}`;
    const currentTime = Date.now();
    
    const result = await redis.eval(
      redeemCouponScript,
      3,
      couponKey,
      usageKey,
      userCouponKey,
      userId,
      currentTime
    );
    
    if (result.err) {
      const errorMessages = {
        'COUPON_NOT_FOUND': 'Coupon not found',
        'COUPON_EXPIRED': 'Coupon has expired',
        'COUPON_ALREADY_USED': 'Coupon already used by this user',
        'COUPON_MAX_USES_REACHED': 'Coupon has reached maximum uses'
      };
      
      return res.status(400).json({ error: errorMessages[result.err] || 'Invalid coupon' });
    }
    
    const discount = parseFloat(result.ok);
    const discountAmount = (orderAmount * discount) / 100;
    const finalAmount = orderAmount - discountAmount;
    
    const redemptionId = uuidv4();
    
    res.json({
      success: true,
      redemptionId,
      originalAmount: orderAmount,
      discountPercent: discount,
      discountAmount: discountAmount.toFixed(2),
      finalAmount: finalAmount.toFixed(2)
    });
    
  } catch (error) {
    res.status(500).json({ error: 'Failed to redeem coupon' });
  }
});

app.get('/api/coupons/:code', async (req, res) => {
  try {
    const { code } = req.params;
    const couponKey = `${COUPON_PREFIX}${code}`;
    const usageKey = `${COUPON_USAGE_PREFIX}${code}`;
    
    const [couponData, currentUses] = await Promise.all([
      redis.hgetall(couponKey),
      redis.get(usageKey)
    ]);
    
    if (!couponData.code) {
      return res.status(404).json({ error: 'Coupon not found' });
    }
    
    const now = Date.now();
    const isExpired = now > parseInt(couponData.expiresAt);
    const usesRemaining = parseInt(couponData.maxUses) - parseInt(currentUses || 0);
    
    res.json({
      code: couponData.code,
      discount: parseFloat(couponData.discount),
      expiresAt: parseInt(couponData.expiresAt),
      isExpired,
      maxUses: parseInt(couponData.maxUses),
      currentUses: parseInt(currentUses || 0),
      usesRemaining: Math.max(0, usesRemaining),
      isActive: !isExpired && usesRemaining > 0
    });
    
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch coupon' });
  }
});

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log(`Coupon redemption service running on port ${PORT}`);
});

process.on('SIGTERM', async () => {
  await redis.quit();
  process.exit(0);
});