function getPlanPrice(plan) {
  if (plan === "free") {
    return 0;
  } else if (plan === "pro") {
    return 10;
  } else if (plan === "enterprise") {
    return 50;
  } else {
    return 0;
  }
}

function changeSubscription(userId, currentPlan, newPlan) {
  const currentPrice = getPlanPrice(currentPlan);
  const newPrice = getPlanPrice(newPlan);
  const chargeAmount = newPrice - currentPrice;
  return {
    newPlan: newPlan,
    chargeAmount: chargeAmount,
  };
}