import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from 'react';
import {
  ActivityIndicator,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
  Platform,
} from 'react-native';
import {
  confirmPlatformPayPayment,
  isPlatformPaySupported,
  PlatformPay,
  StripeProvider,
} from '@stripe/stripe-react-native';
import Purchases, {
  LOG_LEVEL,
  PRODUCT_CATEGORY,
  type CustomerInfo,
  type PurchasesStoreProduct,
} from 'react-native-purchases';

type ProductCatalog = {
  inApp: PurchasesStoreProduct[];
  subscriptions: PurchasesStoreProduct[];
};

type RevenueCatConfig = {
  iosApiKey: string;
  androidApiKey: string;
  appUserId: string;
};

type PaymentBackendConfig = {
  baseUrl: string;
  createWalletIntentPath: string;
  confirmWalletPaymentPath: string;
  confirmStorePurchasePath: string;
  headers?: Record<string, string>;
};

type PaymentModuleConfig = {
  stripePublishableKey: string;
  merchantIdentifier: string;
  merchantCountryCode: string;
  merchantDisplayName: string;
  walletTestMode?: boolean;
  backend: PaymentBackendConfig;
  revenueCat: RevenueCatConfig;
  productIds: {
    inApp: string[];
    subscriptions: string[];
  };
};

type WalletChargeRequest = {
  amount: number;
  currency: string;
  label: string;
  description?: string;
  metadata?: Record<string, string>;
};

type WalletIntentResponse = {
  clientSecret: string;
  merchantCountryCode?: string;
};

type WalletPaymentResult = {
  paymentIntentId: string;
  status: string;
};

type StorePurchaseResult = {
  productId: string;
  activeEntitlements: string[];
  originalAppUserId: string;
};

type PaymentModuleContextValue = {
  ready: boolean;
  loading: boolean;
  walletSupported: boolean;
  error: string | null;
  catalog: ProductCatalog;
  refreshCatalog: () => Promise<void>;
  buyInApp: (productId: string) => Promise<StorePurchaseResult>;
  buySubscription: (productId: string) => Promise<StorePurchaseResult>;
  restorePurchases: () => Promise<CustomerInfo>;
  payWithWallet: (request: WalletChargeRequest) => Promise<WalletPaymentResult>;
  clearError: () => void;
};

type JsonValue =
  | string
  | number
  | boolean
  | null
  | { [key: string]: JsonValue }
  | JsonValue[];

const config: PaymentModuleConfig = {
  stripePublishableKey: 'pk_test_replace_with_your_publishable_key',
  merchantIdentifier: 'merchant.com.example.paymentmodule',
  merchantCountryCode: 'US',
  merchantDisplayName: 'Example Payments',
  walletTestMode: true,
  backend: {
    baseUrl: 'https://your-backend.example.com',
    createWalletIntentPath: '/payments/wallet/intents',
    confirmWalletPaymentPath: '/payments/wallet/confirm',
    confirmStorePurchasePath: '/payments/store/confirm',
    headers: {
      Authorization: 'Bearer replace-with-session-token',
    },
  },
  revenueCat: {
    iosApiKey: 'appl_replace_with_ios_public_sdk_key',
    androidApiKey: 'goog_replace_with_android_public_sdk_key',
    appUserId: 'demo-user-123',
  },
  productIds: {
    inApp: ['coins_100'],
    subscriptions: ['pro_monthly'],
  },
};

const initialCatalog: ProductCatalog = {
  inApp: [],
  subscriptions: [],
};

const PaymentModuleContext = createContext<PaymentModuleContextValue | undefined>(undefined);

function joinUrl(baseUrl: string, path: string): string {
  const normalizedBase = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
}

async function postJson<TResponse>(
  backend: PaymentBackendConfig,
  path: string,
  body: Record<string, JsonValue>,
): Promise<TResponse> {
  const response = await fetch(joinUrl(backend.baseUrl, path), {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...backend.headers,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Request failed with status ${response.status}: ${errorText}`);
  }

  return (await response.json()) as TResponse;
}

function normalizeError(error: unknown): Error {
  return error instanceof Error ? error : new Error('Unknown payment error');
}

function formatMinorUnits(amount: number, currency: string): string {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: currency.toUpperCase(),
  }).format(amount / 100);
}

function getPlatformRevenueCatKey(moduleConfig: PaymentModuleConfig): string {
  if (Platform.OS === 'ios') {
    return moduleConfig.revenueCat.iosApiKey;
  }

  if (Platform.OS === 'android') {
    return moduleConfig.revenueCat.androidApiKey;
  }

  throw new Error(`Unsupported platform: ${Platform.OS}`);
}

async function createWalletIntent(
  backend: PaymentBackendConfig,
  payload: WalletChargeRequest,
): Promise<WalletIntentResponse> {
  return postJson<WalletIntentResponse>(backend, backend.createWalletIntentPath, {
    amount: payload.amount,
    currency: payload.currency,
    label: payload.label,
    description: payload.description ?? '',
    metadata: payload.metadata ?? {},
  });
}

async function confirmWalletPayment(
  backend: PaymentBackendConfig,
  payload: WalletPaymentResult,
): Promise<void> {
  await postJson<Record<string, JsonValue>>(backend, backend.confirmWalletPaymentPath, {
    paymentIntentId: payload.paymentIntentId,
    status: payload.status,
  });
}

async function confirmStorePurchase(
  backend: PaymentBackendConfig,
  payload: StorePurchaseResult & {
    appUserId: string;
    platform: 'ios' | 'android';
  },
): Promise<void> {
  await postJson<Record<string, JsonValue>>(backend, backend.confirmStorePurchasePath, {
    appUserId: payload.appUserId,
    productId: payload.productId,
    activeEntitlements: payload.activeEntitlements,
    originalAppUserId: payload.originalAppUserId,
    platform: payload.platform,
  });
}

async function fetchCatalog(moduleConfig: PaymentModuleConfig): Promise<ProductCatalog> {
  const [inApp, subscriptions] = await Promise.all([
    moduleConfig.productIds.inApp.length > 0
      ? Purchases.getProducts(moduleConfig.productIds.inApp, PRODUCT_CATEGORY.NON_SUBSCRIPTION)
      : Promise.resolve([] as PurchasesStoreProduct[]),
    moduleConfig.productIds.subscriptions.length > 0
      ? Purchases.getProducts(
          moduleConfig.productIds.subscriptions,
          PRODUCT_CATEGORY.SUBSCRIPTION,
        )
      : Promise.resolve([] as PurchasesStoreProduct[]),
  ]);

  return {
    inApp,
    subscriptions,
  };
}

function PaymentModuleRuntime({
  children,
  moduleConfig,
}: PropsWithChildren<{ moduleConfig: PaymentModuleConfig }>) {
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(false);
  const [walletSupported, setWalletSupported] = useState(false);
  const [catalog, setCatalog] = useState<ProductCatalog>(initialCatalog);
  const [error, setError] = useState<string | null>(null);

  const refreshCatalog = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const nextCatalog = await fetchCatalog(moduleConfig);
      setCatalog(nextCatalog);
    } catch (caughtError) {
      const normalized = normalizeError(caughtError);
      setError(normalized.message);
      throw normalized;
    } finally {
      setLoading(false);
    }
  }, [moduleConfig]);

  useEffect(() => {
    let active = true;

    const initialize = async () => {
      const apiKey = getPlatformRevenueCatKey(moduleConfig);

      if (!apiKey) {
        throw new Error('A RevenueCat public SDK key is required for the current platform.');
      }

      await Purchases.setLogLevel(LOG_LEVEL.WARN);
      Purchases.configure({
        apiKey,
        appUserID: moduleConfig.revenueCat.appUserId,
      });

      const [supported, nextCatalog] = await Promise.all([
        isPlatformPaySupported(),
        fetchCatalog(moduleConfig),
      ]);

      if (!active) {
        return;
      }

      setWalletSupported(Boolean(supported));
      setCatalog(nextCatalog);
      setError(null);
      setReady(true);
    };

    initialize().catch((caughtError) => {
      if (!active) {
        return;
      }

      const normalized = normalizeError(caughtError);
      setError(normalized.message);
      setReady(false);
    });

    return () => {
      active = false;
    };
  }, [moduleConfig]);

  const performStorePurchase = useCallback(
    async (productId: string, source: PurchasesStoreProduct[]): Promise<StorePurchaseResult> => {
      setLoading(true);
      setError(null);

      try {
        const product = source.find((entry) => entry.identifier === productId);

        if (!product) {
          throw new Error(`Product ${productId} is not available in the loaded catalog.`);
        }

        const purchaseResult = await Purchases.purchaseStoreProduct(product);
        const result: StorePurchaseResult = {
          productId,
          activeEntitlements: Object.keys(purchaseResult.customerInfo.entitlements.active),
          originalAppUserId: purchaseResult.customerInfo.originalAppUserId ?? '',
        };

        await confirmStorePurchase(moduleConfig.backend, {
          ...result,
          appUserId: moduleConfig.revenueCat.appUserId,
          platform: Platform.OS === 'ios' ? 'ios' : 'android',
        });

        return result;
      } catch (caughtError) {
        const normalized = normalizeError(caughtError);
        setError(normalized.message);
        throw normalized;
      } finally {
        setLoading(false);
      }
    },
    [moduleConfig.backend, moduleConfig.revenueCat.appUserId],
  );

  const buyInApp = useCallback(
    async (productId: string) => performStorePurchase(productId, catalog.inApp),
    [catalog.inApp, performStorePurchase],
  );

  const buySubscription = useCallback(
    async (productId: string) => performStorePurchase(productId, catalog.subscriptions),
    [catalog.subscriptions, performStorePurchase],
  );

  const restorePurchases = useCallback(async (): Promise<CustomerInfo> => {
    setLoading(true);
    setError(null);

    try {
      return await Purchases.restorePurchases();
    } catch (caughtError) {
      const normalized = normalizeError(caughtError);
      setError(normalized.message);
      throw normalized;
    } finally {
      setLoading(false);
    }
  }, []);

  const payWithWallet = useCallback(
    async (request: WalletChargeRequest): Promise<WalletPaymentResult> => {
      setLoading(true);
      setError(null);

      try {
        if (!walletSupported) {
          throw new Error('Apple Pay or Google Pay is not available on this device.');
        }

        const intent = await createWalletIntent(moduleConfig.backend, request);

        const walletResult = await confirmPlatformPayPayment(
          intent.clientSecret,
          Platform.OS === 'ios'
            ? {
                applePay: {
                  merchantCountryCode:
                    intent.merchantCountryCode ?? moduleConfig.merchantCountryCode,
                  currencyCode: request.currency.toUpperCase(),
                  cartItems: [
                    {
                      label: request.label,
                      amount: formatMinorUnits(request.amount, request.currency),
                      paymentType: PlatformPay.PaymentType.Immediate,
                    },
                  ],
                },
              }
            : {
                googlePay: {
                  testEnv: moduleConfig.walletTestMode ?? false,
                  merchantName: moduleConfig.merchantDisplayName,
                  merchantCountryCode:
                    intent.merchantCountryCode ?? moduleConfig.merchantCountryCode,
                  currencyCode: request.currency.toUpperCase(),
                  billingAddressConfig: {
                    format: PlatformPay.BillingAddressFormat.Full,
                    isPhoneNumberRequired: true,
                    isRequired: true,
                  },
                },
              },
        );

        if (walletResult.error) {
          throw new Error(walletResult.error.message);
        }

        if (!walletResult.paymentIntent?.id || !walletResult.paymentIntent.status) {
          throw new Error('Wallet payment completed without a valid PaymentIntent response.');
        }

        const result: WalletPaymentResult = {
          paymentIntentId: walletResult.paymentIntent.id,
          status: walletResult.paymentIntent.status,
        };

        await confirmWalletPayment(moduleConfig.backend, result);

        return result;
      } catch (caughtError) {
        const normalized = normalizeError(caughtError);
        setError(normalized.message);
        throw normalized;
      } finally {
        setLoading(false);
      }
    },
    [
      moduleConfig.backend,
      moduleConfig.merchantCountryCode,
      moduleConfig.merchantDisplayName,
      moduleConfig.walletTestMode,
      walletSupported,
    ],
  );

  const value = useMemo<PaymentModuleContextValue>(
    () => ({
      ready,
      loading,
      walletSupported,
      error,
      catalog,
      refreshCatalog,
      buyInApp,
      buySubscription,
      restorePurchases,
      payWithWallet,
      clearError: () => setError(null),
    }),
    [
      ready,
      loading,
      walletSupported,
      error,
      catalog,
      refreshCatalog,
      buyInApp,
      buySubscription,
      restorePurchases,
      payWithWallet,
    ],
  );

  return <PaymentModuleContext.Provider value={value}>{children}</PaymentModuleContext.Provider>;
}

function PaymentModuleProvider({
  children,
  moduleConfig,
}: PropsWithChildren<{ moduleConfig: PaymentModuleConfig }>) {
  return (
    <StripeProvider
      publishableKey={moduleConfig.stripePublishableKey}
      merchantIdentifier={moduleConfig.merchantIdentifier}
    >
      <PaymentModuleRuntime moduleConfig={moduleConfig}>{children}</PaymentModuleRuntime>
    </StripeProvider>
  );
}

function usePaymentModule(): PaymentModuleContextValue {
  const context = useContext(PaymentModuleContext);

  if (!context) {
    throw new Error('usePaymentModule must be used inside a PaymentModuleProvider.');
  }

  return context;
}

function ProductCard({
  product,
  actionLabel,
  disabled,
  onPress,
}: {
  product: PurchasesStoreProduct;
  actionLabel: string;
  disabled: boolean;
  onPress: () => void;
}) {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>{product.title}</Text>
      <Text style={styles.description}>{product.description}</Text>
      <Text style={styles.price}>{product.priceString}</Text>
      <Pressable
        accessibilityRole="button"
        disabled={disabled}
        onPress={onPress}
        style={[styles.button, disabled && styles.buttonDisabled]}
      >
        <Text style={styles.buttonLabel}>{actionLabel}</Text>
      </Pressable>
    </View>
  );
}

function PaymentScreen() {
  const {
    ready,
    loading,
    walletSupported,
    error,
    catalog,
    refreshCatalog,
    buyInApp,
    buySubscription,
    restorePurchases,
    payWithWallet,
    clearError,
  } = usePaymentModule();
  const [status, setStatus] = useState('Ready to process purchases.');

  const hasPlaceholders = useMemo(
    () =>
      config.stripePublishableKey.includes('replace_with') ||
      config.backend.baseUrl.includes('your-backend') ||
      config.revenueCat.iosApiKey.includes('replace_with') ||
      config.revenueCat.androidApiKey.includes('replace_with'),
    [],
  );

  const handleAsync = async (operation: () => Promise<void>) => {
    clearError();

    try {
      await operation();
    } catch (caughtError) {
      setStatus(
        caughtError instanceof Error ? caughtError.message : 'Unexpected payment error.',
      );
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.header}>Cross-Platform Payments</Text>
        <Text style={styles.subheader}>
          In-app purchases use RevenueCat and digital wallet payments use Stripe Platform Pay.
        </Text>

        {hasPlaceholders ? (
          <View style={styles.banner}>
            <Text style={styles.bannerText}>
              Replace the placeholder publishable keys, RevenueCat keys, backend URL, and bearer
              token before shipping.
            </Text>
          </View>
        ) : null}

        <View style={styles.statusContainer}>
          <Text style={styles.statusLabel}>Module status</Text>
          <Text style={styles.statusValue}>{ready ? 'Initialized' : 'Initializing'}</Text>
          <Text style={styles.statusLabel}>Wallet availability</Text>
          <Text style={styles.statusValue}>{walletSupported ? 'Supported' : 'Unavailable'}</Text>
          <Text style={styles.statusLabel}>Last result</Text>
          <Text style={styles.statusValue}>{error ?? status}</Text>
        </View>

        <Pressable
          accessibilityRole="button"
          disabled={loading}
          onPress={() =>
            handleAsync(async () => {
              await refreshCatalog();
              setStatus('Catalog refreshed.');
            })
          }
          style={[styles.button, loading && styles.buttonDisabled]}
        >
          <Text style={styles.buttonLabel}>Refresh Catalog</Text>
        </Pressable>

        <Pressable
          accessibilityRole="button"
          disabled={loading || !walletSupported}
          onPress={() =>
            handleAsync(async () => {
              const result = await payWithWallet({
                amount: 1299,
                currency: 'USD',
                label: 'Digital wallet checkout',
                description: 'Premium digital content',
                metadata: {
                  orderId: 'demo-order-1001',
                },
              });
              setStatus(`Wallet payment ${result.status}: ${result.paymentIntentId}`);
            })
          }
          style={[styles.button, (loading || !walletSupported) && styles.buttonDisabled]}
        >
          <Text style={styles.buttonLabel}>Pay with Apple Pay / Google Pay</Text>
        </Pressable>

        <Pressable
          accessibilityRole="button"
          disabled={loading}
          onPress={() =>
            handleAsync(async () => {
              const restored = await restorePurchases();
              const entitlements = Object.keys(restored.entitlements.active);
              setStatus(
                `Restored entitlements: ${entitlements.length > 0 ? entitlements.join(', ') : 'none'}`,
              );
            })
          }
          style={[styles.button, loading && styles.buttonDisabled]}
        >
          <Text style={styles.buttonLabel}>Restore Purchases</Text>
        </Pressable>

        <Text style={styles.sectionHeader}>One-Time Purchases</Text>
        {catalog.inApp.map((product) => (
          <ProductCard
            key={product.identifier}
            product={product}
            actionLabel="Buy"
            disabled={loading}
            onPress={() =>
              handleAsync(async () => {
                const result = await buyInApp(product.identifier);
                setStatus(`Purchased ${result.productId}`);
              })
            }
          />
        ))}

        <Text style={styles.sectionHeader}>Subscriptions</Text>
        {catalog.subscriptions.map((product) => (
          <ProductCard
            key={product.identifier}
            product={product}
            actionLabel="Subscribe"
            disabled={loading}
            onPress={() =>
              handleAsync(async () => {
                const result = await buySubscription(product.identifier);
                setStatus(`Subscribed to ${result.productId}`);
              })
            }
          />
        ))}

        {loading ? <ActivityIndicator size="large" color="#ffffff" /> : null}
      </ScrollView>
    </SafeAreaView>
  );
}

export default function App() {
  return (
    <PaymentModuleProvider moduleConfig={config}>
      <PaymentScreen />
    </PaymentModuleProvider>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#111827',
  },
  container: {
    padding: 20,
    gap: 16,
  },
  header: {
    fontSize: 30,
    fontWeight: '700',
    color: '#f9fafb',
  },
  subheader: {
    color: '#d1d5db',
    fontSize: 15,
    lineHeight: 22,
  },
  banner: {
    backgroundColor: '#7c2d12',
    borderRadius: 12,
    padding: 14,
  },
  bannerText: {
    color: '#fed7aa',
    fontSize: 14,
    lineHeight: 20,
  },
  statusContainer: {
    backgroundColor: '#1f2937',
    borderRadius: 16,
    padding: 16,
    gap: 6,
  },
  statusLabel: {
    color: '#9ca3af',
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  statusValue: {
    color: '#f9fafb',
    fontSize: 15,
    marginBottom: 4,
  },
  sectionHeader: {
    color: '#f9fafb',
    fontSize: 20,
    fontWeight: '700',
    marginTop: 8,
  },
  card: {
    backgroundColor: '#1f2937',
    borderRadius: 16,
    padding: 16,
    gap: 10,
  },
  title: {
    color: '#f9fafb',
    fontSize: 18,
    fontWeight: '600',
  },
  description: {
    color: '#d1d5db',
    fontSize: 14,
    lineHeight: 20,
  },
  price: {
    color: '#a7f3d0',
    fontSize: 16,
    fontWeight: '700',
  },
  button: {
    backgroundColor: '#2563eb',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    alignItems: 'center',
  },
  buttonDisabled: {
    opacity: 0.45,
  },
  buttonLabel: {
    color: '#eff6ff',
    fontSize: 15,
    fontWeight: '700',
  },
});