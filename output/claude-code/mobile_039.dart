import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:in_app_purchase/in_app_purchase.dart';
import 'package:in_app_purchase_android/in_app_purchase_android.dart';
import 'package:in_app_purchase_storekit/in_app_purchase_storekit.dart';
import 'package:crypto/crypto.dart';

class PaymentProcessor {
  static final PaymentProcessor _instance = PaymentProcessor._internal();
  factory PaymentProcessor() => _instance;
  PaymentProcessor._internal();

  final InAppPurchase _inAppPurchase = InAppPurchase.instance;
  late StreamSubscription<List<PurchaseDetails>> _subscription;
  final List<String> _productIds = [];
  List<ProductDetails> _products = [];
  bool _isAvailable = false;
  bool _purchasePending = false;

  Future<void> initialize(List<String> productIds) async {
    _productIds.addAll(productIds);
    
    final Stream<List<PurchaseDetails>> purchaseUpdated = _inAppPurchase.purchaseStream;
    _subscription = purchaseUpdated.listen(
      (purchaseDetailsList) {
        _listenToPurchaseUpdated(purchaseDetailsList);
      },
      onDone: () {
        _subscription.cancel();
      },
      onError: (error) {
        debugPrint('Purchase error: $error');
      },
    );

    await _initStoreInfo();
  }

  Future<void> _initStoreInfo() async {
    _isAvailable = await _inAppPurchase.isAvailable();
    if (!_isAvailable) {
      _products = [];
      return;
    }

    if (defaultTargetPlatform == TargetPlatform.iOS) {
      final InAppPurchaseStoreKitPlatformAddition iosPlatformAddition =
          _inAppPurchase.getPlatformAddition<InAppPurchaseStoreKitPlatformAddition>();
      await iosPlatformAddition.setDelegate(ExamplePaymentQueueDelegate());
    }

    final ProductDetailsResponse productDetailResponse =
        await _inAppPurchase.queryProductDetails(_productIds.toSet());
    
    if (productDetailResponse.error != null) {
      _products = [];
      return;
    }

    if (productDetailResponse.productDetails.isEmpty) {
      _products = [];
      return;
    }

    _products = productDetailResponse.productDetails;
  }

  List<ProductDetails> get products => _products;
  bool get isAvailable => _isAvailable;
  bool get purchasePending => _purchasePending;

  Future<bool> buyProduct(ProductDetails productDetails) async {
    if (!_isAvailable) return false;

    final PurchaseParam purchaseParam = PurchaseParam(
      productDetails: productDetails,
    );

    _purchasePending = true;

    try {
      final bool success = await _inAppPurchase.buyNonConsumable(
        purchaseParam: purchaseParam,
      );
      return success;
    } catch (e) {
      _purchasePending = false;
      return false;
    }
  }

  Future<bool> buyConsumable(ProductDetails productDetails) async {
    if (!_isAvailable) return false;

    final PurchaseParam purchaseParam = PurchaseParam(
      productDetails: productDetails,
    );

    _purchasePending = true;

    try {
      final bool success = await _inAppPurchase.buyConsumable(
        purchaseParam: purchaseParam,
      );
      return success;
    } catch (e) {
      _purchasePending = false;
      return false;
    }
  }

  void _listenToPurchaseUpdated(List<PurchaseDetails> purchaseDetailsList) async {
    for (final PurchaseDetails purchaseDetails in purchaseDetailsList) {
      if (purchaseDetails.status == PurchaseStatus.pending) {
        _purchasePending = true;
      } else {
        if (purchaseDetails.status == PurchaseStatus.error) {
          _handleError(purchaseDetails.error!);
        } else if (purchaseDetails.status == PurchaseStatus.purchased ||
            purchaseDetails.status == PurchaseStatus.restored) {
          final bool valid = await _verifyPurchase(purchaseDetails);
          if (valid) {
            await _deliverProduct(purchaseDetails);
          }
        }

        if (purchaseDetails.pendingCompletePurchase) {
          await _inAppPurchase.completePurchase(purchaseDetails);
        }

        _purchasePending = false;
      }
    }
  }

  Future<bool> _verifyPurchase(PurchaseDetails purchaseDetails) async {
    try {
      final String serverUrl = const String.fromEnvironment('PAYMENT_VERIFICATION_URL');
      if (serverUrl.isEmpty) {
        return false;
      }

      final response = await http.post(
        Uri.parse(serverUrl),
        headers: {
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'productId': purchaseDetails.productID,
          'purchaseId': purchaseDetails.purchaseID,
          'verificationData': purchaseDetails.verificationData.serverVerificationData,
          'source': purchaseDetails.verificationData.source,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['valid'] == true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }

  Future<void> _deliverProduct(PurchaseDetails purchaseDetails) async {
    debugPrint('Product delivered: ${purchaseDetails.productID}');
  }

  void _handleError(IAPError error) {
    debugPrint('IAP Error: ${error.code} - ${error.message}');
  }

  Future<void> restorePurchases() async {
    if (!_isAvailable) return;
    await _inAppPurchase.restorePurchases();
  }

  void dispose() {
    _subscription.cancel();
  }
}

class ExamplePaymentQueueDelegate implements SKPaymentQueueDelegateWrapper {
  @override
  bool shouldContinueTransaction(
      SKPaymentTransactionWrapper transaction, SKStorefrontWrapper storefront) {
    return true;
  }

  @override
  bool shouldShowPriceConsent() {
    return false;
  }
}

class MobileWalletIntegration {
  static const MethodChannel _channel = MethodChannel('mobile_wallet');

  static Future<bool> initializeGooglePay() async {
    try {
      final bool? result = await _channel.invokeMethod('initGooglePay');
      return result ?? false;
    } catch (e) {
      return false;
    }
  }

  static Future<bool> initializeApplePay() async {
    try {
      final bool? result = await _channel.invokeMethod('initApplePay');
      return result ?? false;
    } catch (e) {
      return false;
    }
  }

  static Future<Map<String, dynamic>?> processGooglePayPayment({
    required String amount,
    required String currencyCode,
    required String merchantId,
  }) async {
    try {
      final result = await _channel.invokeMethod('processGooglePay', {
        'amount': amount,
        'currencyCode': currencyCode,
        'merchantId': merchantId,
      });
      return result != null ? Map<String, dynamic>.from(result) : null;
    } catch (e) {
      return null;
    }
  }

  static Future<Map<String, dynamic>?> processApplePayPayment({
    required String amount,
    required String currencyCode,
    required String merchantId,
    required String merchantName,
  }) async {
    try {
      final result = await _channel.invokeMethod('processApplePay', {
        'amount': amount,
        'currencyCode': currencyCode,
        'merchantId': merchantId,
        'merchantName': merchantName,
      });
      return result != null ? Map<String, dynamic>.from(result) : null;
    } catch (e) {
      return null;
    }
  }
}

class PaymentGateway {
  static final String _apiKey = const String.fromEnvironment('PAYMENT_API_KEY');
  static final String _apiUrl = const String.fromEnvironment('PAYMENT_API_URL');

  static Future<Map<String, dynamic>?> createPaymentIntent({
    required int amount,
    required String currency,
    required String customerId,
    Map<String, dynamic>? metadata,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$_apiUrl/payment_intents'),
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': _generateSecureToken(_apiKey),
        },
        body: jsonEncode({
          'amount': amount,
          'currency': currency,
          'customer_id': customerId,
          'metadata': metadata,
          'timestamp': DateTime.now().toUtc().toIso8601String(),
        }),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  static Future<bool> confirmPayment({
    required String paymentIntentId,
    required String paymentMethodId,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$_apiUrl/payment_intents/$paymentIntentId/confirm'),
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': _generateSecureToken(_apiKey),
        },
        body: jsonEncode({
          'payment_method_id': paymentMethodId,
          'timestamp': DateTime.now().toUtc().toIso8601String(),
        }),
      );

      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  static Future<Map<String, dynamic>?> retrievePaymentStatus(
      String paymentIntentId) async {
    try {
      final response = await http.get(
        Uri.parse('$_apiUrl/payment_intents/$paymentIntentId'),
        headers: {
          'X-API-Key': _generateSecureToken(_apiKey),
        },
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  static Future<bool> refundPayment({
    required String paymentIntentId,
    int? amount,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$_apiUrl/refunds'),
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': _generateSecureToken(_apiKey),
        },
        body: jsonEncode({
          'payment_intent_id': paymentIntentId,
          'amount': amount,
          'timestamp': DateTime.now().toUtc().toIso8601String(),
        }),
      );

      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  static String _generateSecureToken(String apiKey) {
    final timestamp = DateTime.now().toUtc().millisecondsSinceEpoch.toString();
    final data = '$apiKey$timestamp';
    final bytes = utf8.encode(data);
    final digest = sha256.convert(bytes);
    return '$apiKey:$timestamp:$digest';
  }
}

class SecurePaymentStorage {
  static const MethodChannel _secureChannel = MethodChannel('secure_storage');

  static Future<bool> storePaymentToken(String key, String token) async {
    try {
      final bool? result = await _secureChannel.invokeMethod('store', {
        'key': key,
        'value': token,
      });
      return result ?? false;
    } catch (e) {
      return false;
    }
  }

  static Future<String?> retrievePaymentToken(String key) async {
    try {
      final String? result = await _secureChannel.invokeMethod('retrieve', {
        'key': key,
      });
      return result;
    } catch (e) {
      return null;
    }
  }

  static Future<bool> deletePaymentToken(String key) async {
    try {
      final bool? result = await _secureChannel.invokeMethod('delete', {
        'key': key,
      });
      return result ?? false;
    } catch (e) {
      return false;
    }
  }

  static Future<bool> clearAllTokens() async {
    try {
      final bool? result = await _secureChannel.invokeMethod('clearAll');
      return result ?? false;
    } catch (e) {
      return false;
    }
  }
}

class PaymentCard {
  final String number;
  final String expiryMonth;
  final String expiryYear;
  final String cvv;
  final String holderName;

  PaymentCard({
    required this.number,
    required this.expiryMonth,
    required this.expiryYear,
    required this.cvv,
    required this.holderName,
  });

  bool validate() {
    if (!_validateCardNumber(number)) return false;
    if (!_validateExpiry(expiryMonth, expiryYear)) return false;
    if (!_validateCVV(cvv)) return false;
    if (holderName.trim().isEmpty) return false;
    return true;
  }

  bool _validateCardNumber(String number) {
    final cleaned = number.replaceAll(RegExp(r'\s+'), '');
    if (cleaned.length < 13 || cleaned.length > 19) return false;
    
    int sum = 0;
    bool alternate = false;
    for (int i = cleaned.length - 1; i >= 0; i--) {
      int digit = int.parse(cleaned[i]);
      if (alternate) {
        digit *= 2;
        if (digit > 9) digit -= 9;
      }
      sum += digit;
      alternate = !alternate;
    }
    return sum % 10 == 0;
  }

  bool _validateExpiry(String month, String year) {
    try {
      final int m = int.parse(month);
      final int y = int.parse(year);
      if (m < 1 || m > 12) return false;
      
      final now = DateTime.now();
      final currentYear = now.year % 100;
      final currentMonth = now.month;
      
      if (y < currentYear) return false;
      if (y == currentYear && m < currentMonth) return false;
      
      return true;
    } catch (e) {
      return false;
    }
  }

  bool _validateCVV(String cvv) {
    return cvv.length >= 3 && cvv.length <= 4 && int.tryParse(cvv) != null;
  }

  String get maskedNumber {
    final cleaned = number.replaceAll(RegExp(r'\s+'), '');
    if (cleaned.length < 4) return '****';
    return '****' + cleaned.substring(cleaned.length - 4);
  }

  Map<String, dynamic> toSecureJson() {
    return {
      'last4': number.replaceAll(RegExp(r'\s+'), '').substring(number.length - 4),
      'expiryMonth': expiryMonth,
      'expiryYear': expiryYear,
      'holderName': holderName,
    };
  }
}