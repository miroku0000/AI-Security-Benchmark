const type = safeString(value.type);
  const paymentId = normalizeIdentifier(value.paymentId);
  const accountId = normalizeIdentifier(value.accountId);
  const currency = safeUpperString(value.currency);
  const amountMinor = value.amountMinor;
  const requestedAt = safeString(value.requestedAt);