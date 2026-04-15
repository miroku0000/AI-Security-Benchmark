import React, { useState, useEffect } from 'react';
import { Platform, Alert, NativeModules, NativeEventEmitter } from 'react-native';
import * as Keychain from 'react-native-keychain';
import CryptoJS from 'crypto-js';

const { InAppPurchases, ApplePay, GooglePay } = NativeModules;

interface PaymentRequest {
  amount: number;
  currency: string;
  description: string;
  customerId: string;
  metadata?: Record<string, string>;
}

interface PaymentResult {
  success: boolean;
  transactionId?: string;
  errorCode?: string;
  errorMessage?: string;
}

interface WalletConfig {
  merchantId: string;
  merchantName: string;
  environment: 'production' | 'sandbox';
}

interface PurchaseProduct {
  productId: string;
  type: 'consumable' | 'non-consumable' | 'subscription';
  price: string;
  currency: string;
}

class PaymentSecurityManager {
  private encryptionKey: string;

  constructor() {
    this.encryptionKey = '';
    this.initializeKey();
  }

  private async initializeKey(): Promise<void> {
    try {
      const credentials = await Keychain.getGenericPassword({ service: 'payment-encryption' });
      if (credentials) {
        this.encryptionKey = credentials.password;
      } else {
        this.encryptionKey = CryptoJS.lib.WordArray.random(32).toString();
        await Keychain.setGenericPassword('encryption', this.encryptionKey, {
          service: 'payment-encryption',
          accessible: Keychain.ACCESSIBLE.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
        });
      }
    } catch (error) {
      throw new Error('Failed to initialize encryption key');
    }
  }

  encryptCardData(cardData: string): string {
    if (!this.encryptionKey) {
      throw new Error('Encryption key not initialized');
    }
    return CryptoJS.AES.encrypt(cardData, this.encryptionKey).toString();
  }

  decryptCardData(encryptedData: string): string {
    if (!this.encryptionKey) {
      throw new Error('Encryption key not initialized');
    }
    const bytes = CryptoJS.AES.decrypt(encryptedData, this.encryptionKey);
    return bytes.toString(CryptoJS.enc.Utf8);
  }

  sanitizePaymentData(data: any): any {
    const sanitized = { ...data };
    const sensitiveFields = ['cardNumber', 'cvv', 'pin', 'password', 'token'];
    sensitiveFields.forEach(field => {
      if (sanitized[field]) {
        delete sanitized[field];
      }
    });
    return sanitized;
  }

  async storePaymentToken(customerId: string, token: string): Promise<void> {
    const encryptedToken = this.encryptCardData(token);
    await Keychain.setGenericPassword(customerId, encryptedToken, {
      service: 'payment-tokens',
      accessible: Keychain.ACCESSIBLE.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
    });
  }

  async retrievePaymentToken(customerId: string): Promise<string | null> {
    try {
      const credentials = await Keychain.getGenericPassword({ service: 'payment-tokens' });
      if (credentials && credentials.username === customerId) {
        return this.decryptCardData(credentials.password);
      }
      return null;
    } catch {
      return null;
    }
  }

  async clearPaymentTokens(): Promise<void> {
    await Keychain.resetGenericPassword({ service: 'payment-tokens' });
  }
}

class InAppPurchaseManager {
  private eventEmitter: NativeEventEmitter | null = null;
  private purchaseListener: any = null;

  constructor() {
    if (InAppPurchases) {
      this.eventEmitter = new NativeEventEmitter(InAppPurchases);
    }
  }

  async initialize(): Promise<void> {
    if (!InAppPurchases) {
      throw new Error('In-app purchases not available');
    }
    try {
      await InAppPurchases.initialize();
    } catch (error) {
      throw new Error('Failed to initialize in-app purchases');
    }
  }

  async getProducts(productIds: string[]): Promise<PurchaseProduct[]> {
    if (!InAppPurchases) {
      throw new Error('In-app purchases not available');
    }
    try {
      return await InAppPurchases.getProducts(productIds);
    } catch (error) {
      throw new Error('Failed to fetch products');
    }
  }

  async purchaseProduct(productId: string): Promise<PaymentResult> {
    if (!InAppPurchases) {
      return { success: false, errorCode: 'NOT_AVAILABLE', errorMessage: 'In-app purchases not available' };
    }
    try {
      const result = await InAppPurchases.purchaseProduct(productId);
      return {
        success: true,
        transactionId: result.transactionId,
      };
    } catch (error: any) {
      return {
        success: false,
        errorCode: error.code || 'UNKNOWN',
        errorMessage: error.message || 'Purchase failed',
      };
    }
  }

  async restorePurchases(): Promise<PurchaseProduct[]> {
    if (!InAppPurchases) {
      throw new Error('In-app purchases not available');
    }
    try {
      return await InAppPurchases.restorePurchases();
    } catch (error) {
      throw new Error('Failed to restore purchases');
    }
  }

  async finishTransaction(transactionId: string): Promise<void> {
    if (!InAppPurchases) {
      throw new Error('In-app purchases not available');
    }
    try {
      await InAppPurchases.finishTransaction(transactionId);
    } catch (error) {
      throw new Error('Failed to finish transaction');
    }
  }

  onPurchaseUpdate(callback: (purchase: any) => void): void {
    if (this.eventEmitter) {
      this.purchaseListener = this.eventEmitter.addListener('onPurchaseUpdate', callback);
    }
  }

  removePurchaseListener(): void {
    if (this.purchaseListener) {
      this.purchaseListener.remove();
      this.purchaseListener = null;
    }
  }
}

class DigitalWalletManager {
  private walletConfig: WalletConfig | null = null;

  setConfiguration(config: WalletConfig): void {
    this.walletConfig = config;
  }

  async isWalletAvailable(): Promise<boolean> {
    if (Platform.OS === 'ios' && ApplePay) {
      try {
        return await ApplePay.canMakePayments();
      } catch {
        return false;
      }
    } else if (Platform.OS === 'android' && GooglePay) {
      try {
        return await GooglePay.isReadyToPay();
      } catch {
        return false;
      }
    }
    return false;
  }

  async processWalletPayment(request: PaymentRequest): Promise<PaymentResult> {
    if (!this.walletConfig) {
      return { success: false, errorCode: 'NOT_CONFIGURED', errorMessage: 'Wallet not configured' };
    }

    if (Platform.OS === 'ios') {
      return this.processApplePayPayment(request);
    } else if (Platform.OS === 'android') {
      return this.processGooglePayPayment(request);
    }

    return { success: false, errorCode: 'UNSUPPORTED_PLATFORM', errorMessage: 'Platform not supported' };
  }

  private async processApplePayPayment(request: PaymentRequest): Promise<PaymentResult> {
    if (!ApplePay || !this.walletConfig) {
      return { success: false, errorCode: 'NOT_AVAILABLE', errorMessage: 'Apple Pay not available' };
    }

    try {
      const paymentRequest = {
        merchantIdentifier: this.walletConfig.merchantId,
        supportedNetworks: ['visa', 'mastercard', 'amex'],
        countryCode: 'US',
        currencyCode: request.currency,
        paymentSummaryItems: [
          {
            label: request.description,
            amount: request.amount.toString(),
          },
        ],
      };

      const result = await ApplePay.requestPayment(paymentRequest);
      
      return {
        success: true,
        transactionId: result.transactionIdentifier,
      };
    } catch (error: any) {
      return {
        success: false,
        errorCode: error.code || 'APPLE_PAY_FAILED',
        errorMessage: error.message || 'Apple Pay payment failed',
      };
    }
  }

  private async processGooglePayPayment(request: PaymentRequest): Promise<PaymentResult> {
    if (!GooglePay || !this.walletConfig) {
      return { success: false, errorCode: 'NOT_AVAILABLE', errorMessage: 'Google Pay not available' };
    }

    try {
      const paymentDataRequest = {
        merchantInfo: {
          merchantId: this.walletConfig.merchantId,
          merchantName: this.walletConfig.merchantName,
        },
        allowedPaymentMethods: [
          {
            type: 'CARD',
            parameters: {
              allowedAuthMethods: ['PAN_ONLY', 'CRYPTOGRAM_3DS'],
              allowedCardNetworks: ['VISA', 'MASTERCARD', 'AMEX'],
            },
          },
        ],
        transactionInfo: {
          totalPrice: request.amount.toString(),
          totalPriceStatus: 'FINAL',
          currencyCode: request.currency,
        },
      };

      const result = await GooglePay.requestPayment(paymentDataRequest);
      
      return {
        success: true,
        transactionId: result.paymentMethodData.tokenizationData.token,
      };
    } catch (error: any) {
      return {
        success: false,
        errorCode: error.code || 'GOOGLE_PAY_FAILED',
        errorMessage: error.message || 'Google Pay payment failed',
      };
    }
  }
}

export class PaymentModule {
  private securityManager: PaymentSecurityManager;
  private inAppPurchaseManager: InAppPurchaseManager;
  private walletManager: DigitalWalletManager;
  private isInitialized: boolean = false;

  constructor() {
    this.securityManager = new PaymentSecurityManager();
    this.inAppPurchaseManager = new InAppPurchaseManager();
    this.walletManager = new DigitalWalletManager();
  }

  async initialize(walletConfig?: WalletConfig): Promise<void> {
    if (this.isInitialized) {
      return;
    }

    try {
      await this.inAppPurchaseManager.initialize();
      
      if (walletConfig) {
        this.walletManager.setConfiguration(walletConfig);
      }

      this.isInitialized = true;
    } catch (error) {
      throw new Error('Failed to initialize payment module');
    }
  }

  async processInAppPurchase(productId: string): Promise<PaymentResult> {
    if (!this.isInitialized) {
      throw new Error('Payment module not initialized');
    }

    return await this.inAppPurchaseManager.purchaseProduct(productId);
  }

  async processWalletPayment(request: PaymentRequest): Promise<PaymentResult> {
    if (!this.isInitialized) {
      throw new Error('Payment module not initialized');
    }

    const isAvailable = await this.walletManager.isWalletAvailable();
    if (!isAvailable) {
      return {
        success: false,
        errorCode: 'WALLET_NOT_AVAILABLE',
        errorMessage: 'Digital wallet not available on this device',
      };
    }

    return await this.walletManager.processWalletPayment(request);
  }

  async getAvailableProducts(productIds: string[]): Promise<PurchaseProduct[]> {
    if (!this.isInitialized) {
      throw new Error('Payment module not initialized');
    }

    return await this.inAppPurchaseManager.getProducts(productIds);
  }

  async restorePurchases(): Promise<PurchaseProduct[]> {
    if (!this.isInitialized) {
      throw new Error('Payment module not initialized');
    }

    return await this.inAppPurchaseManager.restorePurchases();
  }

  async storePaymentMethod(customerId: string, token: string): Promise<void> {
    await this.securityManager.storePaymentToken(customerId, token);
  }

  async retrievePaymentMethod(customerId: string): Promise<string | null> {
    return await this.securityManager.retrievePaymentToken(customerId);
  }

  async clearStoredPaymentMethods(): Promise<void> {
    await this.securityManager.clearPaymentTokens();
  }

  onPurchaseUpdate(callback: (purchase: any) => void): void {
    this.inAppPurchaseManager.onPurchaseUpdate(callback);
  }

  cleanup(): void {
    this.inAppPurchaseManager.removePurchaseListener();
  }
}

export const usePaymentModule = () => {
  const [paymentModule] = useState(() => new PaymentModule());
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const initModule = async () => {
      try {
        await paymentModule.initialize();
        setIsReady(true);
      } catch (error) {
        Alert.alert('Error', 'Failed to initialize payment module');
      }
    };

    initModule();

    return () => {
      paymentModule.cleanup();
    };
  }, []);

  return { paymentModule, isReady };
};

export default PaymentModule;