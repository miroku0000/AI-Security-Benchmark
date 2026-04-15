import type { InAppProduct, IapPurchaseInput, IapReceipt, WalletAuthorization, WalletIntentInput } from "../types";

export type IapProvider = {
  kind: "iap";
  init: (params?: { environment?: "sandbox" | "production" }) => Promise<void>;
  end: () => Promise<void>;
  listProducts: (productIds: string[]) => Promise<InAppProduct[]>;
  purchase: (input: IapPurchaseInput) => Promise<IapReceipt>;
  finish: (receipt: IapReceipt) => Promise<void>;
};

export type WalletProvider = {
  kind: "wallet";
  providerId: string;
  init: (params: { publishableKey?: string; merchantIdentifier?: string; countryCode?: string }) => Promise<void>;
  authorize: (params: { clientSecret: string; intent: WalletIntentInput }) => Promise<WalletAuthorization>;
};

