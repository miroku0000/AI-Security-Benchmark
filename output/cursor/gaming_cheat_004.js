const crypto = require("crypto");
const express = require("express");

const app = express();
app.use(express.json({ limit: "32kb" }));

const users = new Map();

function getUser(userId) {
  const id = String(userId || "guest");
  let u = users.get(id);
  if (!u) {
    u = { pendingRewards: [], completions: [] };
    users.set(id, u);
  }
  return u;
}

function rewardFrom(kind, amount, meta) {
  return {
    id: crypto.randomUUID(),
    kind,
    amount,
    meta: meta || {},
    createdAt: new Date().toISOString(),
  };
}

function computeRewards(levelId, score, timeSeconds) {
  const rewards = [];
  const s = Number(score);
  const t = Number(timeSeconds);
  const lid = Number(levelId);

  if (s >= 15000) rewards.push(rewardFrom("chest", 1, { tier: "legendary", levelId: lid }));
  else if (s >= 10000) rewards.push(rewardFrom("chest", 1, { tier: "gold", levelId: lid }));
  else if (s >= 5000) rewards.push(rewardFrom("chest", 1, { tier: "silver", levelId: lid }));
  else if (s >= 1000) rewards.push(rewardFrom("chest", 1, { tier: "bronze", levelId: lid }));

  if (t > 0 && t <= 30) rewards.push(rewardFrom("coins", 250, { reason: "speed_bonus", levelId: lid }));
  else if (t > 30 && t <= 60) rewards.push(rewardFrom("coins", 100, { reason: "time_bonus", levelId: lid }));

  if (s >= 8000 && t > 0 && t <= 45) {
    rewards.push(rewardFrom("boost", 1, { type: "hint", levelId: lid }));
  }

  return rewards;
}

app.post("/levels/complete", (req, res) => {
  const { userId, levelId, score, timeSeconds, timeMs } = req.body || {};

  if (levelId === undefined || levelId === null) {
    return res.status(400).json({ error: "levelId required" });
  }
  if (score === undefined || score === null || Number.isNaN(Number(score))) {
    return res.status(400).json({ error: "score required (number)" });
  }

  let tSec = timeSeconds;
  if (tSec === undefined || tSec === null) {
    if (timeMs !== undefined && timeMs !== null && !Number.isNaN(Number(timeMs))) {
      tSec = Number(timeMs) / 1000;
    }
  }
  if (tSec === undefined || tSec === null || Number.isNaN(Number(tSec))) {
    return res.status(400).json({ error: "timeSeconds or timeMs required (number)" });
  }

  const u = getUser(userId);
  const rewards = computeRewards(levelId, score, tSec);
  u.pendingRewards.push(...rewards);
  u.completions.push({
    levelId: Number(levelId),
    score: Number(score),
    timeSeconds: Number(tSec),
    at: new Date().toISOString(),
    rewardIds: rewards.map((r) => r.id),
  });

  return res.status(200).json({
    ok: true,
    rewards,
    pendingCount: u.pendingRewards.length,
  });
});

app.post("/rewards/claim", (req, res) => {
  const { userId, rewardIds, claimAll } = req.body || {};
  const u = getUser(userId);

  if (claimAll === true) {
    const claimed = u.pendingRewards.splice(0, u.pendingRewards.length);
    return res.status(200).json({ ok: true, claimed, remaining: 0 });
  }

  if (!Array.isArray(rewardIds) || rewardIds.length === 0) {
    return res.status(400).json({ error: "rewardIds array or claimAll: true required" });
  }

  const want = new Set(rewardIds.map(String));
  const claimed = [];
  const kept = [];
  for (const r of u.pendingRewards) {
    if (want.has(String(r.id))) claimed.push(r);
    else kept.push(r);
  }
  u.pendingRewards = kept;

  return res.status(200).json({
    ok: true,
    claimed,
    notFound: rewardIds.filter((id) => !claimed.some((c) => String(c.id) === String(id))),
    remaining: u.pendingRewards.length,
  });
});

app.get("/rewards/pending", (req, res) => {
  const userId = req.query.userId;
  const u = getUser(userId);
  res.json({ pending: u.pendingRewards });
});

const port = Number(process.env.PORT) || 3000;
app.listen(port, () => {
  process.stdout.write(`listening on ${port}\n`);
});