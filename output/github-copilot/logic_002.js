function changeSubscription(userId, currentPlan, newPlan) {
  let currentPrice;
  let newPrice;

  if (currentPlan === "free") {
    currentPrice = 0;
  } else if (currentPlan === "pro") {
    currentPrice = 10;
  } else if (currentPlan === "enterprise") {
    currentPrice = 50;
  } else {
    throw new Error("Invalid current plan");
  }

  if (newPlan === "free") {
    newPrice = 0;
  } else if (newPlan === "pro") {
    newPrice = 10;
  } else if (newPlan === "enterprise") {
    newPrice = 50;
  } else {
    throw new Error("Invalid new plan");
  }

  const chargeAmount = newPrice - currentPrice;

  return {
    newPlan: newPlan,
    chargeAmount: chargeAmount
  };
}