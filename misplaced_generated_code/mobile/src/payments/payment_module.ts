import { PaymentError, toPaymentError } from "./errors";
import type { IapProvider, WalletProvider } from "./providers/provider";
import type {
  IapPurchaseInput,
  PaymentEnvironment,
  PurchaseRecord,
  WalletAuthorization,
  WalletIntentInput
} from "./types";
import { PaymentBackendClient, type PaymentBackendConfig } from "./client";

export type PaymentModuleConfig = {
  backend: PaymentBackendConfig;
  iapProvider?: IapProvider;
  walletProvider?: WalletProvider;
};

export class PaymentModule {
  private readonly backend: PaymentBackendClient;
  private readonly env: PaymentEnvironment;
  private readonly iap?: IapProvider;
  private readonly wallet?: WalletProvider;

  constructor(config: PaymentModuleConfig) {
    this.backend = new PaymentBackendClient(config.backend);
    this.env = config.backend.env;
    this.iap = config.iapProvider;
    this.wallet = config.walletProvider;
  }

  async init(): Promise<void> {
    const tasks: Promise<void>[] = [];
    if (this.iap) tasks.push(this.iap.init({ environment: this.env }));
    if (this.wallet) tasks.push(this.wallet.init({}));
    await Promise.all(tasks);
  }

  async shutdown(): Promise<void> {
    const tasks: Promise<void>[] = [];
    if (this.iap) tasks.push(this.iap.end());
    await Promise.all(tasks);
  }

  async purchaseIap(input: IapPurchaseInput): Promise<PurchaseRecord> {
    if (!this.iap) throw new PaymentError("IAP_NOT_CONFIGURED", "No in-app purchase provider configured.");
    try {
      const receipt = await this.iap.purchase(input);
      const verify = await this.backend.verifyIapReceipt({ receipt });

      if (!verify.ok) {
        throw new PaymentError(verify.errorCode || "IAP_VERIFY_FAILED", verify.message || "Receipt verification failed.", {
          status: verify.status
        });
      }

      await this.iap.finish(receipt);
      return verify.record;
    } catch (e) {
      throw toPaymentError(e, "IAP_FAILED");
    }
  }

  async startWalletIntent(intent: WalletIntentInput): Promise<{ provider: string; clientSecret: string; intentId?: string }> {
    try {
      const res = await this.backend.createWalletIntent(intent);
      if (!res.ok) throw new PaymentError(res.errorCode || "WALLET_INTENT_FAILED", res.message || "Failed to create wallet intent.");
      return { provider: res.provider, clientSecret: res.clientSecret, intentId: res.intentId };
    } catch (e) {
      throw toPaymentError(e, "WALLET_INTENT_FAILED");
    }
  }

  async authorizeWallet(params: { clientSecret: string; intent: WalletIntentInput }): Promise<WalletAuthorization> {
    if (!this.wallet) throw new PaymentError("WALLET_NOT_CONFIGURED", "No wallet provider configured.");
    try {
      return await this.wallet.authorize(params);
    } catch (e) {
      throw toPaymentError(e, "WALLET_AUTH_FAILED");
    }
  }

  async captureWallet(params: { provider: string; authorization: WalletAuthorization }): Promise<PurchaseRecord> {
    try {
      const res = await this.backend.captureWallet(params);
      if (!res.ok) throw new PaymentError(res.errorCode || "WALLET_CAPTURE_FAILED", res.message || "Failed to capture wallet payment.", { status: res.status });
      return res.record;
    } catch (e) {
      throw toPaymentError(e, "WALLET_CAPTURE_FAILED");
    }
  }
}

