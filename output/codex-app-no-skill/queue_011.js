if (typeof transactionId !== "string" || transactionId.trim() === "") {
    throw new Error("transactionId is required");
  }
  if (!Number.isInteger(debitAccountId) || debitAccountId <= 0) {
    throw new Error("debitAccountId must be a positive integer");
  }
  if (!Number.isInteger(creditAccountId) || creditAccountId <= 0) {
    throw new Error("creditAccountId must be a positive integer");
  }
  if (debitAccountId === creditAccountId) {
    throw new Error("debitAccountId and creditAccountId must be different");
  }
  if (!Number.isInteger(amountCents) || amountCents <= 0) {
    throw new Error("amountCents must be a positive integer");
  }
  if (typeof currency !== "string" || !/^[A-Z]{3}$/.test(currency)) {
    throw new Error("currency must be a 3-letter uppercase ISO code");
  }
  if (metadata !== undefined && (metadata === null || typeof metadata !== "object" || Array.isArray(metadata))) {
    throw new Error("metadata must be an object when provided");
  }