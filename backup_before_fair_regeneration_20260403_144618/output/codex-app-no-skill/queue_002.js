async function processCharge(event) {
  const amount = toNumber(event.amount);
  const currency = event.currency || 'USD';
  const paymentMethodId = event.paymentMethodId || 'unknown';
  const customerId = event.customerId || 'unknown';