function getPlanPrice(planName) {
  if (planName === 'free') {
    return 0;
  } else if (planName === 'pro') {
    return 10;
  } else if (planName === 'enterprise') {
    return 50;
  }