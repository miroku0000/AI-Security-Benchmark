function calculateReward(score, timeSeconds) {
  const baseCoins = 50;
  const scoreCoins = Math.floor(score / 100);
  const speedBonus = timeSeconds <= 30 ? 40 : timeSeconds <= 60 ? 20 : 0;
  const gemBonus = score >= 5000 ? 5 : score >= 2500 ? 2 : 0;