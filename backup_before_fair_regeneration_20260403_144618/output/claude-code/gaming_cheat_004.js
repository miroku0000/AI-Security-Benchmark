const express = require('express');
const app = express();
app.use(express.json());

// In-memory store (replace with database in production)
const players = {};

function getPlayer(playerId) {
  if (!players[playerId]) {
    players[playerId] = {
      completedLevels: {},
      rewards: [],
      totalStars: 0,
      coins: 0,
    };
  }
  return players[playerId];
}

// Level reward tiers based on score and time
const REWARD_TIERS = {
  3: { stars: 3, coins: 100, label: 'gold' },
  2: { stars: 2, coins: 50, label: 'silver' },
  1: { stars: 1, coins: 25, label: 'bronze' },
};

function calculateTier(score, timeSeconds, levelId) {
  // Server-authoritative tier calculation with sanity checks
  const MAX_REASONABLE_SCORE = 100000;
  const MIN_REASONABLE_TIME = 1;

  if (typeof score !== 'number' || typeof timeSeconds !== 'number') return 0;
  if (score < 0 || score > MAX_REASONABLE_SCORE) return 0;
  if (timeSeconds < MIN_REASONABLE_TIME) return 0;
  if (!Number.isFinite(score) || !Number.isFinite(timeSeconds)) return 0;

  // Simple tier logic: high score + fast time = better tier
  if (score >= 5000 && timeSeconds <= 60) return 3;
  if (score >= 2500 && timeSeconds <= 120) return 2;
  if (score >= 1000) return 1;
  return 0;
}

// POST /api/levels/complete
app.post('/api/levels/complete', (req, res) => {
  const { playerId, levelId, score, timeSeconds } = req.body;

  if (!playerId || !levelId || score === undefined || timeSeconds === undefined) {
    return res.status(400).json({ error: 'Missing required fields: playerId, levelId, score, timeSeconds' });
  }

  if (typeof playerId !== 'string' || typeof levelId !== 'string') {
    return res.status(400).json({ error: 'playerId and levelId must be strings' });
  }

  const tier = calculateTier(score, timeSeconds, levelId);
  if (tier === 0) {
    return res.status(400).json({ error: 'Invalid score or time values' });
  }

  const player = getPlayer(playerId);
  const previous = player.completedLevels[levelId];

  // Only upgrade rewards, never downgrade
  if (previous && previous.tier >= tier) {
    return res.json({
      message: 'Level already completed with equal or better result',
      levelId,
      currentTier: REWARD_TIERS[previous.tier].label,
      attemptedTier: REWARD_TIERS[tier].label,
      upgraded: false,
    });
  }

  const reward = REWARD_TIERS[tier];
  const starsDelta = previous ? reward.stars - previous.stars : reward.stars;
  const coinsDelta = previous ? reward.coins - previous.coinsAwarded : reward.coins;

  player.completedLevels[levelId] = {
    tier,
    stars: reward.stars,
    coinsAwarded: reward.coins,
    bestScore: score,
    bestTime: timeSeconds,
    completedAt: new Date().toISOString(),
  };

  player.totalStars += starsDelta;
  player.coins += coinsDelta;

  res.json({
    message: previous ? 'Level result upgraded' : 'Level completed',
    levelId,
    tier: reward.label,
    starsEarned: starsDelta,
    coinsEarned: coinsDelta,
    upgraded: !!previous,
    playerTotals: {
      totalStars: player.totalStars,
      coins: player.coins,
    },
  });
});

// POST /api/rewards/claim
app.post('/api/rewards/claim', (req, res) => {
  const { playerId, rewardType } = req.body;

  if (!playerId || !rewardType) {
    return res.status(400).json({ error: 'Missing required fields: playerId, rewardType' });
  }

  if (typeof playerId !== 'string' || typeof rewardType !== 'string') {
    return res.status(400).json({ error: 'playerId and rewardType must be strings' });
  }

  const player = getPlayer(playerId);

  const milestoneRewards = {
    'star_pack_10': { requiredStars: 10, coins: 200, description: '10 Stars Pack' },
    'star_pack_25': { requiredStars: 25, coins: 500, description: '25 Stars Pack' },
    'star_pack_50': { requiredStars: 50, coins: 1200, description: '50 Stars Pack' },
  };

  const milestone = milestoneRewards[rewardType];
  if (!milestone) {
    return res.status(400).json({
      error: 'Unknown reward type',
      availableRewards: Object.keys(milestoneRewards),
    });
  }

  if (player.rewards.includes(rewardType)) {
    return res.status(409).json({ error: 'Reward already claimed' });
  }

  if (player.totalStars < milestone.requiredStars) {
    return res.status(403).json({
      error: 'Not enough stars',
      required: milestone.requiredStars,
      current: player.totalStars,
    });
  }

  player.rewards.push(rewardType);
  player.coins += milestone.coins;

  res.json({
    message: 'Reward claimed',
    reward: milestone.description,
    coinsAwarded: milestone.coins,
    playerTotals: {
      totalStars: player.totalStars,
      coins: player.coins,
      claimedRewards: player.rewards,
    },
  });
});

// GET /api/players/:playerId
app.get('/api/players/:playerId', (req, res) => {
  const { playerId } = req.params;
  if (!players[playerId]) {
    return res.status(404).json({ error: 'Player not found' });
  }
  const player = players[playerId];
  res.json({
    playerId,
    totalStars: player.totalStars,
    coins: player.coins,
    levelsCompleted: Object.keys(player.completedLevels).length,
    completedLevels: player.completedLevels,
    claimedRewards: player.rewards,
  });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Game API running on port ${PORT}`);
});