export type CurrencyCode = string;

export type PaymentEnvironment = "sandbox" | "production";

export type PaymentMethod = "iap" | "wallet";

export type PaymentStatus = "created" | "pending" | "authorized" | "captured" | "failed" | "cancelled" | "refunded";

export type RiskSignal = {
  deviceId?: string;
  appInstanceId?: string;
  platform: "ios" | "android" | "web" | "unknown";
  osVersion?: string;
  appVersion?: string;
  locale?: string;
  timezone?: string;
};

export type Money = {
  currency: CurrencyCode;
  amountMinor: number;
};

export type InAppProduct = {
  productId: string;
  title?: string;
  description?: string;
  price?: string;
  priceAmountMicros?: string;
  priceCurrencyCode?: string;
};

export type PurchaseRecord = {
  provider: PaymentMethod;
  id: string;
  createdAtMs: number;
  status: PaymentStatus;
  raw?: Record<string, unknown>;
};

export type IapPurchaseInput = {
  productId: string;
  accountUserId?: string;
  obfuscatedAccountId?: string;
  obfuscatedProfileId?: string;
};

export type IapReceipt = {
  platform: "ios" | "android";
  productId: string;
  transactionId?: string;
  purchaseToken?: string;
  receipt?: string;
  originalJson?: string;
  signatureAndroid?: string;
};

export type WalletIntentInput = {
  amount: Money;
  description?: string;
  customerId?: string;
  merchantReference?: string;
};

export type WalletAuthorization = {
  provider: string;
  type: "paymentMethod" | "paymentIntent" | "token";
  id: string;
  clientSecret?: string;
  raw?: Record<string, unknown>;
};

export type BackendVerifyIapRequest = {
  env: PaymentEnvironment;
  receipt: IapReceipt;
  risk: RiskSignal;
};

export type BackendVerifyIapResponse = {
  ok: true;
  status: PaymentStatus;
  record: PurchaseRecord;
} | {
  ok: false;
  status: PaymentStatus;
  errorCode: string;
  message: string;
};

export type BackendCreateWalletIntentRequest = {
  env: PaymentEnvironment;
  intent: WalletIntentInput;
  risk: RiskSignal;
};

export type BackendCreateWalletIntentResponse = {
  ok: true;
  provider: string;
  clientSecret: string;
  intentId?: string;
} | {
  ok: false;
  errorCode: string;
  message: string;
};

export type BackendCaptureWalletIntentRequest = {
  env: PaymentEnvironment;
  provider: string;
  authorization: WalletAuthorization;
  risk: RiskSignal;
};

export type BackendCaptureWalletIntentResponse = {
  ok: true;
  status: PaymentStatus;
  record: PurchaseRecord;
} | {
  ok: false;
  status: PaymentStatus;
  errorCode: string;
  message: string;
};

