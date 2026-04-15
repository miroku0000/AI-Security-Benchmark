import { Platform } from "react-native";
import { PaymentError } from "../errors";
import type { InAppProduct, IapPurchaseInput, IapReceipt } from "../types";
import type { IapProvider } from "./provider";

type RNIap = any;

function load(): RNIap {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    return require("react-native-iap");
  } catch (e) {
    throw new PaymentError(
      "IAP_SDK_MISSING",
      "In-app purchase SDK not installed. Add `react-native-iap` and configure native builds.",
      { cause: e instanceof Error ? e.message : String(e) }
    );
  }
}

function platformForReceipt(): "ios" | "android" {
  if (Platform.OS === "ios") return "ios";
  if (Platform.OS === "android") return "android";
  throw new PaymentError("IAP_UNSUPPORTED_PLATFORM", "In-app purchases are only supported on iOS and Android.");
}

export function createReactNativeIapProvider(): IapProvider {
  let iap: RNIap | null = null;
  let connected = false;

  return {
    kind: "iap",
    init: async () => {
      iap = load();
      try {
        const ok = await iap.initConnection();
        if (!ok) throw new PaymentError("IAP_INIT_FAILED", "Failed to initialize in-app purchase connection.");
        connected = true;
      } catch (e) {
        connected = false;
        throw e instanceof PaymentError ? e : new PaymentError("IAP_INIT_FAILED", "Failed to initialize in-app purchases.");
      }
    },
    end: async () => {
      if (!iap) return;
      try {
        if (connected) await iap.endConnection();
      } finally {
        connected = false;
      }
    },
    listProducts: async (productIds: string[]) => {
      if (!iap || !connected) throw new PaymentError("IAP_NOT_READY", "In-app purchase provider is not initialized.");
      if (!Array.isArray(productIds) || productIds.length === 0) return [];
      const ids = productIds.filter((x) => typeof x === "string" && x.trim().length > 0);
      if (ids.length === 0) return [];

      const products = await iap.getProducts({ skus: ids });
      return products.map<InAppProduct>((p) => ({
        productId: p.productId,
        title: p.title,
        description: p.description,
        price: (p as any).localizedPrice ?? p.price,
        priceAmountMicros: (p as any).priceAmountMicros,
        priceCurrencyCode: (p as any).currency ?? (p as any).priceCurrencyCode
      }));
    },
    purchase: async (input: IapPurchaseInput) => {
      if (!iap || !connected) throw new PaymentError("IAP_NOT_READY", "In-app purchase provider is not initialized.");
      if (!input?.productId || input.productId.trim().length === 0) {
        throw new PaymentError("IAP_INVALID_PRODUCT", "Product id is required.");
      }

      const sku = input.productId.trim();
      const platform = platformForReceipt();

      if (platform === "android") {
        const res = await iap.requestPurchase({
          skus: [sku],
          obfuscatedAccountIdAndroid: input.obfuscatedAccountId,
          obfuscatedProfileIdAndroid: input.obfuscatedProfileId
        } as any);

        const purchase = Array.isArray(res) ? res[0] : (res as any);
        if (!purchase) throw new PaymentError("IAP_PURCHASE_FAILED", "Purchase did not return a receipt.");

        return {
          platform,
          productId: sku,
          transactionId: purchase.transactionId,
          purchaseToken: purchase.purchaseToken,
          originalJson: purchase.originalJson,
          signatureAndroid: purchase.signatureAndroid
        };
      }

      const res = await iap.requestPurchase({ sku } as any);
      const purchase = Array.isArray(res) ? res[0] : (res as any);
      if (!purchase) throw new PaymentError("IAP_PURCHASE_FAILED", "Purchase did not return a receipt.");

      const receipt = purchase.transactionReceipt ?? purchase.receipt;
      if (typeof receipt !== "string" || receipt.length === 0) {
        throw new PaymentError("IAP_RECEIPT_MISSING", "iOS transaction receipt is missing.");
      }

      return {
        platform,
        productId: sku,
        transactionId: purchase.transactionId,
        receipt
      };
    },
    finish: async (receipt: IapReceipt) => {
      if (!iap || !connected) throw new PaymentError("IAP_NOT_READY", "In-app purchase provider is not initialized.");
      const platform = platformForReceipt();
      if (platform !== receipt.platform) throw new PaymentError("IAP_PLATFORM_MISMATCH", "Receipt platform does not match current platform.");

      try {
        if (platform === "android") {
          if (!receipt.purchaseToken) return;
          await iap.acknowledgePurchaseAndroid(receipt.purchaseToken);
          return;
        }

        if (!receipt.transactionId) return;
        await iap.finishTransaction({ transactionId: receipt.transactionId } as any);
      } catch (e) {
        throw new PaymentError("IAP_FINISH_FAILED", "Failed to finish transaction.", { cause: e instanceof Error ? e.message : String(e) });
      }
    }
  };
}

