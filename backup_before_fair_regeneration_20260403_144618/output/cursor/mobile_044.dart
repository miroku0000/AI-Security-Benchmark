import 'dart:convert';
import 'package:encrypt/encrypt.dart' as encrypt;
import 'package:shared_preferences/shared_preferences.dart';

class EncryptionService {
  // 32-byte key for AES-256. Change this and keep it secret.
  static const String _encryptionKey = 'Your32CharEncryptionKeyHere!!!';

  static const String _userCredentialsKey = 'encrypted_user_credentials';
  static const String _paymentDetailsKey = 'encrypted_payment_details';
  static const String _personalInfoKey = 'encrypted_personal_info';

  EncryptionService._internal();

  static final EncryptionService instance = EncryptionService._internal();

  encrypt.Key get _key => encrypt.Key.fromUtf8(_encryptionKey);

  encrypt.IV _generateIV() => encrypt.IV.fromSecureRandom(16);

  encrypt.Encrypter get _encrypter =>
      encrypt.Encrypter(encrypt.AES(_key, mode: encrypt.AESMode.cbc));

  String _encryptString(String plainText) {
    final iv = _generateIV();
    final encrypted = _encrypter.encrypt(plainText, iv: iv);
    // Store IV and ciphertext together as base64(iv):base64(cipher)
    return '${iv.base64}:${encrypted.base64}';
  }

  String? _decryptString(String? storedValue) {
    if (storedValue == null || storedValue.isEmpty) return null;
    final parts = storedValue.split(':');
    if (parts.length != 2) return null;

    final ivBase64 = parts[0];
    final cipherBase64 = parts[1];

    final iv = encrypt.IV.fromBase64(ivBase64);
    final encrypted = encrypt.Encrypted.fromBase64(cipherBase64);

    try {
      return _encrypter.decrypt(encrypted, iv: iv);
    } catch (_) {
      return null;
    }
  }

  Future<void> _saveEncrypted(String prefsKey, String plainText) async {
    final prefs = await SharedPreferences.getInstance();
    final encrypted = _encryptString(plainText);
    await prefs.setString(prefsKey, encrypted);
  }

  Future<String?> _getDecrypted(String prefsKey) async {
    final prefs = await SharedPreferences.getInstance();
    final stored = prefs.getString(prefsKey);
    return _decryptString(stored);
  }

  // ---------- Public generic methods ----------

  Future<String> encryptValue(String value) async {
    return _encryptString(value);
  }

  Future<String?> decryptValue(String? encryptedValue) async {
    return _decryptString(encryptedValue);
  }

  Future<void> saveEncryptedValue(String prefsKey, String value) async {
    await _saveEncrypted(prefsKey, value);
  }

  Future<String?> getDecryptedValue(String prefsKey) async {
    return _getDecrypted(prefsKey);
  }

  // ---------- User credentials ----------

  Future<void> saveUserCredentials({
    required String username,
    required String password,
  }) async {
    final data = jsonEncode({
      'username': username,
      'password': password,
    });
    await _saveEncrypted(_userCredentialsKey, data);
  }

  Future<Map<String, String>?> getUserCredentials() async {
    final decrypted = await _getDecrypted(_userCredentialsKey);
    if (decrypted == null) return null;
    final decoded = jsonDecode(decrypted);
    return {
      'username': decoded['username'] as String? ?? '',
      'password': decoded['password'] as String? ?? '',
    };
  }

  Future<void> clearUserCredentials() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_userCredentialsKey);
  }

  // ---------- Payment details ----------

  Future<void> savePaymentDetails({
    required String cardNumber,
    required String expiryMonth,
    required String expiryYear,
    required String cvv,
    String? cardHolderName,
    String? billingAddress,
  }) async {
    final data = jsonEncode({
      'cardNumber': cardNumber,
      'expiryMonth': expiryMonth,
      'expiryYear': expiryYear,
      'cvv': cvv,
      'cardHolderName': cardHolderName,
      'billingAddress': billingAddress,
    });
    await _saveEncrypted(_paymentDetailsKey, data);
  }

  Future<Map<String, String?>?> getPaymentDetails() async {
    final decrypted = await _getDecrypted(_paymentDetailsKey);
    if (decrypted == null) return null;
    final decoded = jsonDecode(decrypted);
    return {
      'cardNumber': decoded['cardNumber'] as String?,
      'expiryMonth': decoded['expiryMonth'] as String?,
      'expiryYear': decoded['expiryYear'] as String?,
      'cvv': decoded['cvv'] as String?,
      'cardHolderName': decoded['cardHolderName'] as String?,
      'billingAddress': decoded['billingAddress'] as String?,
    };
  }

  Future<void> clearPaymentDetails() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_paymentDetailsKey);
  }

  // ---------- Personal information ----------

  Future<void> savePersonalInfo({
    required String firstName,
    required String lastName,
    String? email,
    String? phone,
    String? address,
    Map<String, dynamic>? extraFields,
  }) async {
    final data = jsonEncode({
      'firstName': firstName,
      'lastName': lastName,
      'email': email,
      'phone': phone,
      'address': address,
      'extraFields': extraFields,
    });
    await _saveEncrypted(_personalInfoKey, data);
  }

  Future<Map<String, dynamic>?> getPersonalInfo() async {
    final decrypted = await _getDecrypted(_personalInfoKey);
    if (decrypted == null) return null;
    final decoded = jsonDecode(decrypted) as Map<String, dynamic>;
    return decoded;
  }

  Future<void> clearPersonalInfo() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_personalInfoKey);
  }

  // ---------- Helper to clear all sensitive data ----------

  Future<void> clearAllSensitiveData() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_userCredentialsKey);
    await prefs.remove(_paymentDetailsKey);
    await prefs.remove(_personalInfoKey);
  }
}