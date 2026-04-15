import { createApiClient } from "../networking/client";
import { PaymentError } from "./errors";
import { collectRiskSignal } from "./risk";
import type {
  BackendCaptureWalletIntentRequest,
  BackendCaptureWalletIntentResponse,
  BackendCreateWalletIntentRequest,
  BackendCreateWalletIntentResponse,
  BackendVerifyIapRequest,
  BackendVerifyIapResponse,
  PaymentEnvironment,
  WalletAuthorization,
  WalletIntentInput
} from "./types";

export type PaymentBackendConfig = {
  baseUrl: string;
  env: PaymentEnvironment;
  getAuthToken?: () => string | undefined | Promise<string | undefined>;
  endpoints?: {
    verifyIap?: string;
    createWalletIntent?: string;
    captureWallet?: string;
  };
};

export class PaymentBackendClient {
  private readonly config: PaymentBackendConfig;
  private readonly api: ReturnType<typeof createApiClient>;

  constructor(config: PaymentBackendConfig) {
    if (!config?.baseUrl) throw new PaymentError("PAYMENT_BACKEND_CONFIG", "Payment backend baseUrl is required.");
    this.config = {
      ...config,
      endpoints: {
        verifyIap: config.endpoints?.verifyIap ?? "/payments/iap/verify",
        createWalletIntent: config.endpoints?.createWalletIntent ?? "/payments/wallet/intent",
        captureWallet: config.endpoints?.captureWallet ?? "/payments/wallet/capture"
      }
    };
    this.api = createApiClient({
      baseUrl: this.config.baseUrl,
      getAuthToken: this.config.getAuthToken
    });
  }

  async verifyIapReceipt(req: Omit<BackendVerifyIapRequest, "env" | "risk">): Promise<BackendVerifyIapResponse> {
    const risk = await collectRiskSignal();
    const body: BackendVerifyIapRequest = { env: this.config.env, receipt: req.receipt, risk };
    const res = await this.api.request<BackendVerifyIapResponse>({
      method: "POST",
      path: this.config.endpoints?.verifyIap,
      body
    });
    return res.data;
  }

  async createWalletIntent(intent: WalletIntentInput): Promise<BackendCreateWalletIntentResponse> {
    const risk = await collectRiskSignal();
    const body: BackendCreateWalletIntentRequest = { env: this.config.env, intent, risk };
    const res = await this.api.request<BackendCreateWalletIntentResponse>({
      method: "POST",
      path: this.config.endpoints?.createWalletIntent,
      body
    });
    return res.data;
  }

  async captureWallet(params: { provider: string; authorization: WalletAuthorization }): Promise<BackendCaptureWalletIntentResponse> {
    const risk = await collectRiskSignal();
    const body: BackendCaptureWalletIntentRequest = {
      env: this.config.env,
      provider: params.provider,
      authorization: params.authorization,
      risk
    };
    const res = await this.api.request<BackendCaptureWalletIntentResponse>({
      method: "POST",
      path: this.config.endpoints?.captureWallet,
      body
    });
    return res.data;
  }
}

