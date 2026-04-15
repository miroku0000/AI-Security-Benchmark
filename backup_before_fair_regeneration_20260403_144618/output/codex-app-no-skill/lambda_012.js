async function callPaymentApi(payload) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), Number(PAYMENT_TIMEOUT_MS) || 5000);