import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'payment/ui/payment_home_page.dart';
import 'payment/payment_module.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final paymentModule = PaymentModule();
  await paymentModule.initialize();
  runApp(ProviderScope(
    overrides: [
      paymentModuleProvider.overrideWithValue(paymentModule),
    ],
    child: const MyApp(),
  ));
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Payment Module Demo',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.indigo),
        useMaterial3: true,
      ),
      home: const PaymentHomePage(),
    );
  }
}



// lib/payment/payment_module.dart
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'service/payment_service.dart';
import 'service/in_app_purchase_service.dart';
import 'service/wallet_payment_service.dart';
import 'service/payment_backend_client.dart';

final paymentModuleProvider = Provider<PaymentModule>((ref) {
  throw UnimplementedError('Overridden in main.dart');
});

class PaymentModule {
  late final PaymentBackendClient backendClient;
  late final InAppPurchaseService iapService;
  late final WalletPaymentService walletService;
  late final PaymentService paymentService;

  Future<void> initialize() async {
    backendClient = PaymentBackendClient(
      baseUrl: const String.fromEnvironment(
        'PAYMENT_BACKEND_URL',
        defaultValue: 'https://your-backend.example.com',
      ),
      apiKey: const String.fromEnvironment(
        'PAYMENT_BACKEND_API_KEY',
        defaultValue: '',
      ),
    );

    iapService = InAppPurchaseService(backendClient: backendClient);
    walletService = WalletPaymentService(backendClient: backendClient);

    paymentService = PaymentService(
      iapService: iapService,
      walletService: walletService,
      backendClient: backendClient,
    );

    try {
      await iapService.initialize();
      await walletService.initialize();
    } catch (e, st) {
      debugPrint('PaymentModule initialization error: $e\n$st');
    }
  }
}



// lib/payment/models/payment_models.dart
enum PaymentMethodType {
  inAppPurchase,
  applePay,
  googlePay,
}

enum PaymentStatus {
  pending,
  authorized,
  captured,
  failed,
  cancelled,
}

class PaymentProduct {
  final String id;
  final String title;
  final String description;
  final double price;
  final String currency;

  const PaymentProduct({
    required this.id,
    required this.title,
    required this.description,
    required this.price,
    required this.currency,
  });
}

class PaymentIntent {
  final String id;
  final String productId;
  final double amount;
  final String currency;
  final PaymentMethodType method;
  final PaymentStatus status;
  final DateTime createdAt;

  PaymentIntent({
    required this.id,
    required this.productId,
    required this.amount,
    required this.currency,
    required this.method,
    required this.status,
    required this.createdAt,
  });

  factory PaymentIntent.fromJson(Map<String, dynamic> json) {
    return PaymentIntent(
      id: json['id'] as String,
      productId: json['product_id'] as String,
      amount: (json['amount'] as num).toDouble(),
      currency: json['currency'] as String,
      method: PaymentMethodType.values.firstWhere(
        (m) => m.name == json['method'],
        orElse: () => PaymentMethodType.inAppPurchase,
      ),
      status: PaymentStatus.values.firstWhere(
        (s) => s.name == json['status'],
        orElse: () => PaymentStatus.failed,
      ),
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

class PaymentResult {
  final bool success;
  final PaymentStatus status;
  final String? transactionId;
  final String? errorMessage;

  const PaymentResult({
    required this.success,
    required this.status,
    this.transactionId,
    this.errorMessage,
  });

  PaymentResult copyWith({
    bool? success,
    PaymentStatus? status,
    String? transactionId,
    String? errorMessage,
  }) {
    return PaymentResult(
      success: success ?? this.success,
      status: status ?? this.status,
      transactionId: transactionId ?? this.transactionId,
      errorMessage: errorMessage ?? this.errorMessage,
    );
  }
}



// lib/payment/service/payment_backend_client.dart
import 'dart:convert';
import 'package:dio/dio.dart';

import '../models/payment_models.dart';

class PaymentBackendClient {
  final String baseUrl;
  final String apiKey;
  late final Dio _dio;

  PaymentBackendClient({
    required this.baseUrl,
    required this.apiKey,
  }) {
    _dio = Dio(
      BaseOptions(
        baseUrl: baseUrl,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 20),
        headers: {
          'Content-Type': 'application/json',
          if (apiKey.isNotEmpty) 'Authorization': 'Bearer $apiKey',
        },
      ),
    );
  }

  Future<List<PaymentProduct>> fetchProducts() async {
    final response = await _dio.get('/products');
    final list = (response.data as List).cast<Map<String, dynamic>>();
    return list
        .map(
          (e) => PaymentProduct(
            id: e['id'] as String,
            title: e['title'] as String,
            description: e['description'] as String,
            price: (e['price'] as num).toDouble(),
            currency: e['currency'] as String,
          ),
        )
        .toList();
  }

  Future<PaymentIntent> createPaymentIntent({
    required String productId,
    required PaymentMethodType method,
  }) async {
    final response = await _dio.post(
      '/payment_intents',
      data: jsonEncode({
        'product_id': productId,
        'method': method.name,
      }),
    );
    return PaymentIntent.fromJson(
      (response.data as Map<String, dynamic>),
    );
  }

  Future<void> confirmPaymentIntent({
    required String paymentIntentId,
    required String gatewayTransactionId,
  }) async {
    await _dio.post(
      '/payment_intents/$paymentIntentId/confirm',
      data: jsonEncode({
        'gateway_transaction_id': gatewayTransactionId,
      }),
    );
  }

  Future<void> reportPaymentFailure({
    required String paymentIntentId,
    required String reason,
  }) async {
    await _dio.post(
      '/payment_intents/$paymentIntentId/fail',
      data: jsonEncode({'reason': reason}),
    );
  }

  Future<void> validateIapPurchase({
    required String paymentIntentId,
    required String platform,
    required String receipt,
  }) async {
    await _dio.post(
      '/iap/validate',
      data: jsonEncode({
        'payment_intent_id': paymentIntentId,
        'platform': platform,
        'receipt': receipt,
      }),
    );
  }

  Future<void> validateWalletPayment({
    required String paymentIntentId,
    required String platform,
    required Map<String, dynamic> paymentToken,
  }) async {
    await _dio.post(
      '/wallet/validate',
      data: jsonEncode({
        'payment_intent_id': paymentIntentId,
        'platform': platform,
        'payment_token': paymentToken,
      }),
    );
  }
}



// lib/payment/service/in_app_purchase_service.dart
import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:in_app_purchase/in_app_purchase.dart';

import '../models/payment_models.dart';
import 'payment_backend_client.dart';

class InAppPurchaseService {
  final PaymentBackendClient backendClient;
  final InAppPurchase _iap = InAppPurchase.instance;

  StreamSubscription<List<PurchaseDetails>>? _subscription;
  final _pendingValidations = <String, String>{};

  InAppPurchaseService({
    required this.backendClient,
  });

  Future<void> initialize() async {
    final isAvailable = await _iap.isAvailable();
    if (!isAvailable) {
      debugPrint('IAP not available on this device.');
      return;
    }

    _subscription = _iap.purchaseStream.listen(
      _handlePurchaseUpdates,
      onError: (Object error) {
        debugPrint('IAP purchase stream error: $error');
      },
    );
  }

  Future<List<ProductDetails>> loadProducts(List<String> ids) async {
    final response = await _iap.queryProductDetails(ids.toSet());
    if (response.error != null) {
      debugPrint('Error querying products: ${response.error}');
    }
    return response.productDetails;
  }

  Future<PaymentResult> buyProduct({
    required ProductDetails product,
    required String paymentIntentId,
  }) async {
    final purchaseParam = PurchaseParam(productDetails: product);
    _pendingValidations[product.id] = paymentIntentId;

    try {
      await _iap.buyConsumable(
        purchaseParam: purchaseParam,
        autoConsume: true,
      );
      return const PaymentResult(
        success: true,
        status: PaymentStatus.pending,
      );
    } catch (e) {
      debugPrint('Error initiating IAP purchase: $e');
      return const PaymentResult(
        success: false,
        status: PaymentStatus.failed,
        errorMessage: 'Unable to start purchase',
      );
    }
  }

  Future<void> _handlePurchaseUpdates(
      List<PurchaseDetails> purchaseDetailsList) async {
    for (final purchaseDetails in purchaseDetailsList) {
      final productId = purchaseDetails.productID;
      final paymentIntentId = _pendingValidations[productId];

      switch (purchaseDetails.status) {
        case PurchaseStatus.pending:
          break;
        case PurchaseStatus.purchased:
        case PurchaseStatus.restored:
          if (paymentIntentId != null) {
            await _validateAndAcknowledgePurchase(
              paymentIntentId: paymentIntentId,
              purchaseDetails: purchaseDetails,
            );
          }
          break;
        case PurchaseStatus.error:
          debugPrint('IAP error: ${purchaseDetails.error}');
          if (paymentIntentId != null) {
            await backendClient.reportPaymentFailure(
              paymentIntentId: paymentIntentId,
              reason: purchaseDetails.error?.message ?? 'unknown_iap_error',
            );
          }
          break;
        case PurchaseStatus.canceled:
          if (paymentIntentId != null) {
            await backendClient.reportPaymentFailure(
              paymentIntentId: paymentIntentId,
              reason: 'user_cancelled',
            );
          }
          break;
      }

      if (purchaseDetails.pendingCompletePurchase) {
        await _iap.completePurchase(purchaseDetails);
      }
    }
  }

  Future<void> _validateAndAcknowledgePurchase({
    required String paymentIntentId,
    required PurchaseDetails purchaseDetails,
  }) async {
    try {
      String receipt = '';
      if (Platform.isIOS) {
        receipt = purchaseDetails.verificationData.serverVerificationData;
        await backendClient.validateIapPurchase(
          paymentIntentId: paymentIntentId,
          platform: 'ios',
          receipt: receipt,
        );
      } else if (Platform.isAndroid) {
        receipt = purchaseDetails.verificationData.serverVerificationData;
        await backendClient.validateIapPurchase(
          paymentIntentId: paymentIntentId,
          platform: 'android',
          receipt: receipt,
        );
      }
    } catch (e) {
      debugPrint('Error validating IAP with backend: $e');
    } finally {
      _pendingValidations.remove(purchaseDetails.productID);
    }
  }

  Future<void> dispose() async {
    await _subscription?.cancel();
  }
}



// lib/payment/service/wallet_payment_service.dart
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:pay/pay.dart';

import '../models/payment_models.dart';
import 'payment_backend_client.dart';

class WalletPaymentService {
  final PaymentBackendClient backendClient;

  late final List<PaymentItem> _dummyItems;

  WalletPaymentService({
    required this.backendClient,
  });

  Future<void> initialize() async {
    _dummyItems = [
      PaymentItem(
        label: 'Total',
        amount: '0.00',
        status: PaymentItemStatus.final_price,
      ),
    ];
  }

  List<PaymentItem> buildPaymentItems(PaymentIntent intent) {
    return [
      PaymentItem(
        label: 'Total',
        amount: intent.amount.toStringAsFixed(2),
        status: PaymentItemStatus.final_price,
      ),
    ];
  }

  Future<PaymentResult> startWalletPayment({
    required PaymentIntent intent,
    required Map<String, dynamic> applePayConfig,
    required Map<String, dynamic> googlePayConfig,
  }) async {
    try {
      if (Platform.isIOS) {
        final applePayButton = ApplePayButton(
          paymentConfiguration:
              PaymentConfiguration.fromJsonString(_encodeConfig(applePayConfig)),
          paymentItems: buildPaymentItems(intent),
          style: ApplePayButtonStyle.black,
          type: ApplePayButtonType.buy,
          width: double.infinity,
          height: 48,
          onPaymentResult: (result) {
            _onApplePayResult(intent, result);
          },
          loadingIndicator: const CircularProgressIndicator(),
        );
        debugPrint('ApplePayButton created: $applePayButton');
        return const PaymentResult(
          success: true,
          status: PaymentStatus.pending,
        );
      } else {
        final googlePayButton = GooglePayButton(
          paymentConfiguration: PaymentConfiguration.fromJsonString(
            _encodeConfig(googlePayConfig),
          ),
          paymentItems: buildPaymentItems(intent),
          type: GooglePayButtonType.pay,
          onPaymentResult: (result) {
            _onGooglePayResult(intent, result);
          },
          loadingIndicator: const CircularProgressIndicator(),
        );
        debugPrint('GooglePayButton created: $googlePayButton');
        return const PaymentResult(
          success: true,
          status: PaymentStatus.pending,
        );
      }
    } catch (e) {
      debugPrint('Wallet payment start error: $e');
      return PaymentResult(
        success: false,
        status: PaymentStatus.failed,
        errorMessage: 'Unable to start wallet payment',
      );
    }
  }

  String _encodeConfig(Map<String, dynamic> config) {
    return PaymentConfiguration.fromJson(config).toString();
  }

  Future<void> _onApplePayResult(
      PaymentIntent intent, Map<String, dynamic> paymentResult) async {
    try {
      await backendClient.validateWalletPayment(
        paymentIntentId: intent.id,
        platform: 'ios',
        paymentToken: paymentResult,
      );
    } catch (e) {
      debugPrint('Apple Pay backend validation error: $e');
    }
  }

  Future<void> _onGooglePayResult(
      PaymentIntent intent, Map<String, dynamic> paymentResult) async {
    try {
      await backendClient.validateWalletPayment(
        paymentIntentId: intent.id,
        platform: 'android',
        paymentToken: paymentResult,
      );
    } catch (e) {
      debugPrint('Google Pay backend validation error: $e');
    }
  }
}



// lib/payment/service/payment_service.dart
import 'package:flutter/foundation.dart';
import 'package:in_app_purchase/in_app_purchase.dart';

import '../models/payment_models.dart';
import 'in_app_purchase_service.dart';
import 'wallet_payment_service.dart';
import 'payment_backend_client.dart';

class PaymentService {
  final InAppPurchaseService iapService;
  final WalletPaymentService walletService;
  final PaymentBackendClient backendClient;

  PaymentService({
    required this.iapService,
    required this.walletService,
    required this.backendClient,
  });

  Future<List<PaymentProduct>> loadProducts() {
    return backendClient.fetchProducts();
  }

  Future<PaymentResult> purchaseWithIap(String productId) async {
    try {
      final intent = await backendClient.createPaymentIntent(
        productId: productId,
        method: PaymentMethodType.inAppPurchase,
      );

      final products = await iapService.loadProducts([productId]);
      final productDetails =
          products.firstWhere((p) => p.id == productId, orElse: () {
        throw Exception('Product $productId not found in store.');
      });

      return await iapService.buyProduct(
        product: productDetails,
        paymentIntentId: intent.id,
      );
    } catch (e, st) {
      debugPrint('Error in purchaseWithIap: $e\n$st');
      return PaymentResult(
        success: false,
        status: PaymentStatus.failed,
        errorMessage: 'Failed to start purchase',
      );
    }
  }

  Future<PaymentResult> purchaseWithWallet({
    required String productId,
    required Map<String, dynamic> applePayConfig,
    required Map<String, dynamic> googlePayConfig,
  }) async {
    try {
      final method = defaultTargetPlatform == TargetPlatform.iOS
          ? PaymentMethodType.applePay
          : PaymentMethodType.googlePay;

      final intent = await backendClient.createPaymentIntent(
        productId: productId,
        method: method,
      );

      return await walletService.startWalletPayment(
        intent: intent,
        applePayConfig: applePayConfig,
        googlePayConfig: googlePayConfig,
      );
    } catch (e) {
      debugPrint('Error in purchaseWithWallet: $e');
      return PaymentResult(
        success: false,
        status: PaymentStatus.failed,
        errorMessage: 'Failed to start wallet payment',
      );
    }
  }
}



// lib/payment/ui/payment_home_page.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../payment_module.dart';
import '../models/payment_models.dart';
import '../service/payment_service.dart';

final productsProvider =
    FutureProvider.autoDispose<List<PaymentProduct>>((ref) async {
  final module = ref.read(paymentModuleProvider);
  return module.paymentService.loadProducts();
});

final paymentResultProvider =
    StateProvider<PaymentResult?>((ref) => null);

class PaymentHomePage extends ConsumerWidget {
  const PaymentHomePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final productsAsync = ref.watch(productsProvider);
    final paymentResult = ref.watch(paymentResultProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Payments Demo'),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: productsAsync.when(
            data: (products) => Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (paymentResult != null)
                  _PaymentStatusBanner(result: paymentResult),
                const SizedBox(height: 8),
                const Text(
                  'Available Products',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 12),
                if (products.isEmpty)
                  const Text('No products configured.'),
                Expanded(
                  child: ListView.separated(
                    itemCount: products.length,
                    separatorBuilder: (_, __) => const Divider(),
                    itemBuilder: (context, index) {
                      final p = products[index];
                      return _ProductTile(product: p);
                    },
                  ),
                ),
              ],
            ),
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, st) => SingleChildScrollView(
              child: Text('Error loading products: $e\n$st'),
            ),
          ),
        ),
      ),
    );
  }
}

class _ProductTile extends ConsumerWidget {
  final PaymentProduct product;

  const _ProductTile({required this.product});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final module = ref.read(paymentModuleProvider);
    final paymentService = module.paymentService;

    return ListTile(
      title: Text(product.title),
      subtitle: Text(product.description),
      trailing: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            '${product.price.toStringAsFixed(2)} ${product.currency}',
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 4),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              ElevatedButton(
                onPressed: () async {
                  final result =
                      await paymentService.purchaseWithIap(product.id);
                  ref.read(paymentResultProvider.notifier).state = result;
                },
                child: const Text('In‑App'),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                onPressed: () async {
                  final result = await paymentService.purchaseWithWallet(
                    productId: product.id,
                    applePayConfig: _applePayConfig,
                    googlePayConfig: _googlePayConfig,
                  );
                  ref.read(paymentResultProvider.notifier).state = result;
                },
                child: const Text('Wallet'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _PaymentStatusBanner extends StatelessWidget {
  final PaymentResult result;

  const _PaymentStatusBanner({required this.result});

  @override
  Widget build(BuildContext context) {
    final color = result.success ? Colors.green : Colors.red;
    final text = result.success ? 'Payment started' : 'Payment failed';
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color),
      ),
      child: Text(
        result.errorMessage != null ? '$text: ${result.errorMessage}' : text,
        style: TextStyle(color: color, fontWeight: FontWeight.w600),
      ),
    );
  }
}

// Replace the contents of these configs with PCI‑compliant gateway JSON
// exported from Google Pay and Apple Pay docs / your gateway.
const Map<String, dynamic> _googlePayConfig = {
  "provider": "google_pay",
  "data": {
    "environment": "TEST",
    "apiVersion": 2,
    "apiVersionMinor": 0,
    "allowedPaymentMethods": [
      {
        "type": "CARD",
        "parameters": {
          "allowedAuthMethods": ["PAN_ONLY", "CRYPTOGRAM_3DS"],
          "allowedCardNetworks": ["VISA", "MASTERCARD"]
        },
        "tokenizationSpecification": {
          "type": "PAYMENT_GATEWAY",
          "parameters": {
            "gateway": "your_gateway",
            "gatewayMerchantId": "your_gateway_merchant_id"
          }
        }
      }
    ],
    "merchantInfo": {
      "merchantId": "your_merchant_id",
      "merchantName": "Your Merchant Name"
    },
    "transactionInfo": {
      "totalPriceStatus": "FINAL",
      "totalPrice": "0.00",
      "currencyCode": "USD",
      "countryCode": "US"
    }
  }
};

const Map<String, dynamic> _applePayConfig = {
  "provider": "apple_pay",
  "data": {
    "merchantIdentifier": "merchant.com.your.app",
    "displayName": "Your Merchant Name",
    "merchantCapabilities": ["3DS", "debit", "credit"],
    "supportedNetworks": ["amex", "visa", "masterCard"],
    "countryCode": "US",
    "currencyCode": "USD",
    "requiredBillingContactFields": ["postalAddress", "name"],
    "requiredShippingContactFields": [],
  }
};