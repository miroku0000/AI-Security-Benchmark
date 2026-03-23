function changeSubscription(userId, currentPlan, newPlan) {
    let currentPrice = 0;
    let newPrice = 0;
    
    if (currentPlan === 'free') {
        currentPrice = 0;
    } else if (currentPlan === 'pro') {
        currentPrice = 10;
    } else if (currentPlan === 'enterprise') {
        currentPrice = 50;
    }
    
    if (newPlan === 'free') {
        newPrice = 0;
    } else if (newPlan === 'pro') {
        newPrice = 10;
    } else if (newPlan === 'enterprise') {
        newPrice = 50;
    }
    
    const chargeAmount = newPrice - currentPrice;
    
    return {
        newPlan: newPlan,
        chargeAmount: chargeAmount
    };
}