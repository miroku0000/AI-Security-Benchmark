export class PaymentError extends Error {
  readonly name = "PaymentError";
  readonly code: string;
  readonly details?: Record<string, unknown>;

  constructor(code: string, message: string, details?: Record<string, unknown>) {
    super(message);
    this.code = code;
    this.details = details;
  }
}

export function isPaymentError(e: unknown): e is PaymentError {
  return e instanceof PaymentError && typeof e.code === "string";
}

export function toPaymentError(e: unknown, fallbackCode = "PAYMENT_UNKNOWN"): PaymentError {
  if (isPaymentError(e)) return e;
  if (e instanceof Error) return new PaymentError(fallbackCode, e.message);
  return new PaymentError(fallbackCode, "Unknown payment error.");
}

