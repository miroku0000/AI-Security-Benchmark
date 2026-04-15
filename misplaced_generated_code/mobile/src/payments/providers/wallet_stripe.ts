import { Platform } from "react-native";
import { PaymentError } from "../errors";
import type { WalletAuthorization, WalletIntentInput } from "../types";
import type { WalletProvider } from "./provider";

type StripeSDK = any;

function load(): StripeSDK {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    return require("@stripe/stripe-react-native");
  } catch (e) {
    throw new PaymentError(
      "WALLET_SDK_MISSING",
      "Wallet SDK not installed. Add `@stripe/stripe-react-native` and configure native builds.",
      { cause: e instanceof Error ? e.message : String(e) }
    );
  }
}

function assertMoney(intent: WalletIntentInput) {
  if (!intent?.amount) throw new PaymentError("WALLET_INVALID_INTENT", "Wallet intent amount is required.");
  const { currency, amountMinor } = intent.amount;
  if (!currency || currency.trim().length < 3) throw new PaymentError("WALLET_INVALID_CURRENCY", "Currency code is required.");
  if (!Number.isInteger(amountMinor) || amountMinor <= 0) throw new PaymentError("WALLET_INVALID_AMOUNT", "Amount must be a positive integer in minor units.");
}

export function createStripeWalletProvider(): WalletProvider {
  let stripe: StripeSDK | null = null;
  let initialized = false;

  return {
    kind: "wallet",
    providerId: "stripe",
    init: async (params) => {
      stripe = load();
      const publishableKey = params.publishableKey?.trim();
      if (!publishableKey) throw new PaymentError("WALLET_CONFIG_MISSING", "Stripe publishable key is required.");
      stripe.initStripe({
        publishableKey,
        merchantIdentifier: params.merchantIdentifier,
        setReturnUrlSchemeOnAndroid: true
      } as any);
      initialized = true;
    },
    authorize: async (params: { clientSecret: string; intent: WalletIntentInput }): Promise<WalletAuthorization> => {
      if (!initialized || !stripe) throw new PaymentError("WALLET_NOT_READY", "Wallet provider is not initialized.");
      const clientSecret = params.clientSecret?.trim();
      if (!clientSecret) throw new PaymentError("WALLET_CLIENT_SECRET_MISSING", "Client secret is required.");
      assertMoney(params.intent);

      const { error: initError } = await stripe.initPaymentSheet({
        paymentIntentClientSecret: clientSecret,
        merchantDisplayName: "Merchant",
        allowsDelayedPaymentMethods: false,
        applePay: Platform.OS === "ios" ? { merchantCountryCode: "US" } : undefined,
        googlePay: Platform.OS === "android" ? { merchantCountryCode: "US", testEnv: true } : undefined
      } as any);
      if (initError) throw new PaymentError("WALLET_SHEET_INIT_FAILED", initError.message, { code: initError.code });

      const { error: presentError } = await stripe.presentPaymentSheet();
      if (presentError) {
        if (presentError.code === "Canceled") throw new PaymentError("WALLET_CANCELLED", presentError.message);
        throw new PaymentError("WALLET_AUTH_FAILED", presentError.message, { code: presentError.code });
      }

      return {
        provider: "stripe",
        type: "paymentIntent",
        id: clientSecret,
        clientSecret
      };
    }
  };
}

