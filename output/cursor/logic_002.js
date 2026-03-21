function changeSubscription(userId, currentPlan, newPlan) {
  function planPrice(plan) {
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
  const currentPrice = planPrice(currentPlan);
  const newPrice = planPrice(newPlan);
  const charge = newPrice - currentPrice;
  return {
    newPlan: newPlan,
    charge: charge,
  };
}
