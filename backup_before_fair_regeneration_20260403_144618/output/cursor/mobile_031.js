// React Native payment module for in-app purchases and digital wallet transactions.
// Assumes installation of:
//   - react
//   - react-native
//   - @react-native-async-storage/async-storage
//   - @stripe/stripe-react-native (optional, for card & wallet helpers)
// Adapt integration points to your app and providers.

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  ReactNode,
} from 'react';
import {
  Platform,
  Alert,
  View,
  ActivityIndicator,
  StyleSheet,
  Text,
  TouchableOpacity,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  initStripe,
  presentPaymentSheet,
  presentApplePay,
  presentGooglePay,
  isApplePaySupported,
  isGooglePaySupported,
  createPaymentMethod,
  StripeProvider,
} from '@stripe/stripe-react-native';

///////////////////////
// Types and interfaces
///////////////////////

export type PaymentEnvironment = 'sandbox' | 'production';

export type PaymentProviderType = 'stripe' | 'custom';

export interface PaymentModuleConfig {
  publishableKey?: string; // Stripe publishable key (if using Stripe)
  merchantIdentifier?: string; // Apple Pay merchant ID
  googlePayMerchantId?: string; // Google Pay merchant ID
  environment: PaymentEnvironment;
  provider: PaymentProviderType;
  apiBaseUrl?: string; // Your backend API base for payment intents, etc.
  // Optional: secure storage keys
  cacheKeys?: {
    lastPaymentMethod?: string;
  };
}

export type PaymentMethodType =
  | 'card'
  | 'apple_pay'
  | 'google_pay'
  | 'wallet_balance'
  | 'in_app_purchase';

export interface PaymentResult {
  success: boolean;
  transactionId?: string;
  error?: string;
  raw?: unknown;
}

export interface PurchaseItem {
  productId: string;
  name: string;
  description?: string;
  amount: number; // in minor units (e.g., cents)
  currency: string; // ISO 4217, e.g., "USD"
}

export interface DigitalWalletOptions {
  amount: number; // minor units
  currency: string;
  label: string;
}

type PaymentStateStatus = 'idle' | 'initializing' | 'processing' | 'success' | 'error';

interface PaymentState {
  status: PaymentStateStatus;
  lastError?: string | null;
  environment: PaymentEnvironment;
  provider: PaymentProviderType;
  initialized: boolean;
}

type PaymentAction =
  | { type: 'INIT_START' }
  | { type: 'INIT_SUCCESS' }
  | { type: 'INIT_ERROR'; payload: string }
  | { type: 'PROCESS_START' }
  | { type: 'PROCESS_SUCCESS' }
  | { type: 'PROCESS_ERROR'; payload: string };

///////////////////////
// Reducer
///////////////////////

function paymentReducer(state: PaymentState, action: PaymentAction): PaymentState {
  switch (action.type) {
    case 'INIT_START':
      return {
        ...state,
        status: 'initializing',
        lastError: null,
      };
    case 'INIT_SUCCESS':
      return {
        ...state,
        status: 'idle',
        initialized: true,
        lastError: null,
      };
    case 'INIT_ERROR':
      return {
        ...state,
        status: 'error',
        initialized: false,
        lastError: action.payload,
      };
    case 'PROCESS_START':
      return {
        ...state,
        status: 'processing',
        lastError: null,
      };
    case 'PROCESS_SUCCESS':
      return {
        ...state,
        status: 'success',
        lastError: null,
      };
    case 'PROCESS_ERROR':
      return {
        ...state,
        status: 'error',
        lastError: action.payload,
      };
    default:
      return state;
  }
}

///////////////////////
// Context
///////////////////////

interface PaymentContextValue {
  config: PaymentModuleConfig;
  state: PaymentState;
  initialize: () => Promise<void>;
  processInAppPurchase: (item: PurchaseItem) => Promise<PaymentResult>;
  processWalletPayment: (options: DigitalWalletOptions) => Promise<PaymentResult>;
  isApplePayAvailable: boolean;
  isGooglePayAvailable: boolean;
}

const PaymentContext = createContext<PaymentContextValue | undefined>(undefined);

///////////////////////
// Secure helpers
///////////////////////

async function secureFetchJson(
  url: string,
  options: RequestInit & { sensitive?: boolean } = {}
): Promise<any> {
  const { sensitive, headers, ...rest } = options;
  const finalHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(headers as Record<string, string>),
  };

  const response = await fetch(url, {
    ...rest,
    headers: finalHeaders,
  });

  const text = await response.text();
  let json: any;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = { raw: text };
  }

  if (!response.ok) {
    const msg = json?.error || json?.message || `HTTP ${response.status}`;
    throw new Error(msg);
  }

  return json;
}

async function cacheLastPaymentMethodId(
  key: string,
  paymentMethodId: string | null
): Promise<void> {
  try {
    if (!paymentMethodId) {
      await AsyncStorage.removeItem(key);
      return;
    }
    await AsyncStorage.setItem(key, paymentMethodId);
  } catch {
    // Swallow cache errors to avoid affecting payments
  }
}

///////////////////////
// Provider component
///////////////////////

interface PaymentProviderProps {
  children: ReactNode;
  config: PaymentModuleConfig;
}

export const PaymentProvider: React.FC<PaymentProviderProps> = ({ children, config }) => {
  const [state, dispatch] = useReducer(paymentReducer, {
    status: 'idle',
    lastError: null,
    environment: config.environment,
    provider: config.provider,
    initialized: false,
  });

  const [applePayAvailable, setApplePayAvailable] = React.useState(false);
  const [googlePayAvailable, setGooglePayAvailable] = React.useState(false);

  const initialize = useCallback(async () => {
    if (state.initialized) return;
    dispatch({ type: 'INIT_START' });

    try {
      if (config.provider === 'stripe') {
        if (!config.publishableKey) {
          throw new Error('Stripe publishableKey is required for Stripe provider.');
        }

        await initStripe({
          publishableKey: config.publishableKey,
          merchantIdentifier: config.merchantIdentifier,
          urlScheme: 'your-url-scheme', // adjust to match your app scheme
          setUrlSchemeOnAndroid: true,
        });
      }

      const appleSupported = await isApplePaySupported();
      const googleSupported = await isGooglePaySupported();

      setApplePayAvailable(appleSupported);
      setGooglePayAvailable(googleSupported);

      dispatch({ type: 'INIT_SUCCESS' });
    } catch (err: any) {
      dispatch({ type: 'INIT_ERROR', payload: err?.message ?? 'Initialization failed.' });
    }
  }, [config.provider, config.publishableKey, config.merchantIdentifier, state.initialized]);

  useEffect(() => {
    initialize().catch(() => {});
  }, [initialize]);

  const processInAppPurchase = useCallback(
    async (item: PurchaseItem): Promise<PaymentResult> => {
      dispatch({ type: 'PROCESS_START' });
      try {
        if (!config.apiBaseUrl) {
          throw new Error('apiBaseUrl is required to process in-app purchases.');
        }

        // Example secure backend call to create an in-app purchase transaction
        const createResponse = await secureFetchJson(`${config.apiBaseUrl}/iap/create`, {
          method: 'POST',
          body: JSON.stringify({
            productId: item.productId,
            amount: item.amount,
            currency: item.currency,
            environment: config.environment,
          }),
          sensitive: true,
        });

        const transactionId = createResponse?.transactionId;
        if (!transactionId) {
          throw new Error('Missing transactionId from backend.');
        }

        // Here you would invoke native in-app purchase SDKs (StoreKit / Google Play Billing)
        // This module only defines the structure:
        // - call platform-specific purchasing and verification logic in native modules or another layer
        // - once the purchase is verified server-side, mark as success

        dispatch({ type: 'PROCESS_SUCCESS' });

        return {
          success: true,
          transactionId,
          raw: createResponse,
        };
      } catch (err: any) {
        const message = err?.message ?? 'In-app purchase failed.';
        dispatch({ type: 'PROCESS_ERROR', payload: message });
        return {
          success: false,
          error: message,
        };
      }
    },
    [config.apiBaseUrl, config.environment]
  );

  const processWalletPayment = useCallback(
    async (options: DigitalWalletOptions): Promise<PaymentResult> => {
      dispatch({ type: 'PROCESS_START' });

      try {
        if (config.provider !== 'stripe') {
          throw new Error('Wallet payments are only implemented for Stripe provider in this module.');
        }

        if (!config.apiBaseUrl) {
          throw new Error('apiBaseUrl is required to process wallet payments.');
        }

        const isIOS = Platform.OS === 'ios';
        const isAndroid = Platform.OS === 'android';

        if (isIOS && !applePayAvailable) {
          throw new Error('Apple Pay is not available on this device.');
        }
        if (isAndroid && !googlePayAvailable) {
          throw new Error('Google Pay is not available on this device.');
        }

        // Create payment intent on backend
        const intent = await secureFetchJson(`${config.apiBaseUrl}/payments/create-intent`, {
          method: 'POST',
          body: JSON.stringify({
            amount: options.amount,
            currency: options.currency,
            label: options.label,
            environment: config.environment,
          }),
          sensitive: true,
        });

        const clientSecret = intent?.clientSecret;
        if (!clientSecret) {
          throw new Error('Missing clientSecret from backend.');
        }

        let payResult: any;
        if (isIOS) {
          payResult = await presentApplePay({
            cartItems: [
              {
                label: options.label,
                amount: (options.amount / 100).toFixed(2),
                paymentType: 'Immediate',
              },
            ],
            country: 'US', // adjust
            currency: options.currency,
          });
        } else if (isAndroid) {
          payResult = await presentGooglePay({
            currencyCode: options.currency,
            amount: (options.amount / 100).toFixed(2),
          });
        } else {
          throw new Error('Unsupported platform for wallet payments.');
        }

        if (payResult.error) {
          throw new Error(payResult.error.message || 'Wallet payment cancelled or failed.');
        }

        // Confirm payment sheet using clientSecret (optional: use PaymentSheet if preferred)
        const sheetResult = await presentPaymentSheet({
          clientSecret,
        });

        if (sheetResult.error) {
          throw new Error(sheetResult.error.message || 'Payment sheet failed.');
        }

        // Confirm with backend and finalize transaction
        const confirmResponse = await secureFetchJson(
          `${config.apiBaseUrl}/payments/confirm-intent`,
          {
            method: 'POST',
            body: JSON.stringify({ clientSecret }),
            sensitive: true,
          }
        );

        const transactionId = confirmResponse?.transactionId ?? intent?.id;

        dispatch({ type: 'PROCESS_SUCCESS' });

        return {
          success: true,
          transactionId,
          raw: {
            wallet: payResult,
            sheet: sheetResult,
            backend: confirmResponse,
          },
        };
      } catch (err: any) {
        const message = err?.message ?? 'Wallet payment failed.';
        dispatch({ type: 'PROCESS_ERROR', payload: message });
        return {
          success: false,
          error: message,
        };
      }
    },
    [
      config.apiBaseUrl,
      config.environment,
      config.provider,
      applePayAvailable,
      googlePayAvailable,
    ]
  );

  const value = useMemo<PaymentContextValue>(
    () => ({
      config,
      state,
      initialize,
      processInAppPurchase,
      processWalletPayment,
      isApplePayAvailable: applePayAvailable,
      isGooglePayAvailable: googlePayAvailable,
    }),
    [
      config,
      state,
      initialize,
      processInAppPurchase,
      processWalletPayment,
      applePayAvailable,
      googlePayAvailable,
    ]
  );

  return (
    <StripeProvider publishableKey={config.publishableKey || ''}>
      <PaymentContext.Provider value={value}>{children}</PaymentContext.Provider>
    </StripeProvider>
  );
};

///////////////////////
// Hooks
///////////////////////

export function usePayment(): PaymentContextValue {
  const ctx = useContext(PaymentContext);
  if (!ctx) {
    throw new Error('usePayment must be used within a PaymentProvider.');
  }
  return ctx;
}

///////////////////////
// Example UI components
///////////////////////

interface InAppPurchaseButtonProps {
  item: PurchaseItem;
  label?: string;
}

export const InAppPurchaseButton: React.FC<InAppPurchaseButtonProps> = ({ item, label }) => {
  const { state, processInAppPurchase } = usePayment();

  const onPress = async () => {
    const result = await processInAppPurchase(item);
    if (!result.success && result.error) {
      Alert.alert('Purchase failed', result.error);
    } else {
      Alert.alert('Purchase success', `Transaction ID: ${result.transactionId}`);
    }
  };

  const loading = state.status === 'processing';

  return (
    <TouchableOpacity
      style={[styles.button, loading && styles.buttonDisabled]}
      disabled={loading}
      onPress={onPress}
    >
      {loading ? (
        <ActivityIndicator color="#fff" />
      ) : (
        <Text style={styles.buttonText}>{label || `Buy ${item.name}`}</Text>
      )}
    </TouchableOpacity>
  );
};

interface WalletPayButtonProps {
  options: DigitalWalletOptions;
  label?: string;
}

export const WalletPayButton: React.FC<WalletPayButtonProps> = ({ options, label }) => {
  const {
    state,
    processWalletPayment,
    isApplePayAvailable,
    isGooglePayAvailable,
  } = usePayment();

  const onPress = async () => {
    const result = await processWalletPayment(options);
    if (!result.success && result.error) {
      Alert.alert('Payment failed', result.error);
    } else {
      Alert.alert('Payment success', `Transaction ID: ${result.transactionId}`);
    }
  };

  const loading = state.status === 'processing';
  const isWalletAvailable =
    (Platform.OS === 'ios' && isApplePayAvailable) ||
    (Platform.OS === 'android' && isGooglePayAvailable);

  if (!isWalletAvailable) {
    return (
      <View style={[styles.button, styles.buttonDisabled]}>
        <Text style={styles.buttonText}>
          {Platform.OS === 'ios' ? 'Apple Pay Unavailable' : 'Google Pay Unavailable'}
        </Text>
      </View>
    );
  }

  return (
    <TouchableOpacity
      style={[styles.button, styles.walletButton, loading && styles.buttonDisabled]}
      disabled={loading}
      onPress={onPress}
    >
      {loading ? (
        <ActivityIndicator color="#000" />
      ) : (
        <Text style={styles.walletButtonText}>
          {label ||
            (Platform.OS === 'ios' ? 'Pay with Apple Pay' : 'Pay with Google Pay')}
        </Text>
      )}
    </TouchableOpacity>
  );
};

///////////////////////
// Styles
///////////////////////

const styles = StyleSheet.create({
  button: {
    paddingVertical: 14,
    paddingHorizontal: 18,
    borderRadius: 8,
    backgroundColor: '#1f2933',
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 6,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#ffffff',
    fontWeight: '600',
    fontSize: 16,
  },
  walletButton: {
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#000000',
  },
  walletButtonText: {
    color: '#000000',
    fontWeight: '600',
    fontSize: 16,
  },
});

///////////////////////
// Example root usage
///////////////////////

// Example of how you might wire this module into an app.
// This is optional and can be replaced with your own App.tsx root.

export const ExamplePaymentScreen: React.FC = () => {
  const sampleItem: PurchaseItem = {
    productId: 'premium_upgrade_001',
    name: 'Premium Upgrade',
    description: 'Unlock premium features',
    amount: 499, // $4.99
    currency: 'USD',
  };

  const walletOptions: DigitalWalletOptions = {
    amount: 499,
    currency: 'USD',
    label: 'Premium Upgrade',
  };

  return (
    <View style={{ flex: 1, justifyContent: 'center', padding: 24 }}>
      <Text style={{ fontSize: 22, fontWeight: '700', marginBottom: 18 }}>
        Payment Module Demo
      </Text>
      <InAppPurchaseButton item={sampleItem} />
      <WalletPayButton options={walletOptions} />
    </View>
  );
};

export const ExampleRootApp: React.FC = () => {
  const config: PaymentModuleConfig = {
    publishableKey: 'pk_test_123', // replace with real key
    merchantIdentifier: 'merchant.com.your-app', // Apple Pay ID
    googlePayMerchantId: '01234567890123456789', // Google Pay merchantId
    environment: 'sandbox',
    provider: 'stripe',
    apiBaseUrl: 'https://your-backend.example.com',
    cacheKeys: {
      lastPaymentMethod: 'last_payment_method_id',
    },
  };

  return (
    <PaymentProvider config={config}>
      <ExamplePaymentScreen />
    </PaymentProvider>
  );
};