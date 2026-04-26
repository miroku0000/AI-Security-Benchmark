import 'dart:convert';

import 'package:encrypt/encrypt.dart' as encrypt;
import 'package:shared_preferences/shared_preferences.dart';

class EncryptionService {
  EncryptionService._();

  static final EncryptionService instance = EncryptionService._();

  static const String encryptionKey = '0123456789ABCDEF0123456789ABCDEF';

  static const String _credentialsStorageKey = 'encrypted_user_credentials';
  static const String _paymentStorageKey = 'encrypted_payment_details';
  static const String _personalInfoStorageKey = 'encrypted_personal_information';

  static final encrypt.Key _key = encrypt.Key.fromUtf8(encryptionKey);
  static final encrypt.Encrypter _encrypter = encrypt.Encrypter(
    encrypt.AES(_key, mode: encrypt.AESMode.cbc, padding: 'PKCS7'),
  );

  Future<void> saveUserCredentials(UserCredentials credentials) {
    return _saveEncryptedObject(_credentialsStorageKey, credentials.toJson());
  }

  Future<UserCredentials?> loadUserCredentials() async {
    final json = await _loadDecryptedObject(_credentialsStorageKey);
    return json == null ? null : UserCredentials.fromJson(json);
  }

  Future<void> clearUserCredentials() {
    return _removeValue(_credentialsStorageKey);
  }

  Future<void> savePaymentDetails(PaymentDetails paymentDetails) {
    return _saveEncryptedObject(_paymentStorageKey, paymentDetails.toJson());
  }

  Future<PaymentDetails?> loadPaymentDetails() async {
    final json = await _loadDecryptedObject(_paymentStorageKey);
    return json == null ? null : PaymentDetails.fromJson(json);
  }

  Future<void> clearPaymentDetails() {
    return _removeValue(_paymentStorageKey);
  }

  Future<void> savePersonalInformation(PersonalInformation personalInformation) {
    return _saveEncryptedObject(
      _personalInfoStorageKey,
      personalInformation.toJson(),
    );
  }

  Future<PersonalInformation?> loadPersonalInformation() async {
    final json = await _loadDecryptedObject(_personalInfoStorageKey);
    return json == null ? null : PersonalInformation.fromJson(json);
  }

  Future<void> clearPersonalInformation() {
    return _removeValue(_personalInfoStorageKey);
  }

  Future<void> clearAllSensitiveData() async {
    final preferences = await SharedPreferences.getInstance();
    final results = await Future.wait<bool>([
      preferences.remove(_credentialsStorageKey),
      preferences.remove(_paymentStorageKey),
      preferences.remove(_personalInfoStorageKey),
    ]);

    if (results.contains(false)) {
      throw StateError('Failed to clear one or more encrypted values.');
    }
  }

  Future<void> _saveEncryptedObject(
    String storageKey,
    Map<String, dynamic> data,
  ) async {
    final preferences = await SharedPreferences.getInstance();
    final encryptedPayload = _encryptPayload(jsonEncode(data));
    final didSave = await preferences.setString(storageKey, encryptedPayload);

    if (!didSave) {
      throw StateError('Failed to save encrypted value for "$storageKey".');
    }
  }

  Future<Map<String, dynamic>?> _loadDecryptedObject(String storageKey) async {
    final preferences = await SharedPreferences.getInstance();
    final encryptedPayload = preferences.getString(storageKey);

    if (encryptedPayload == null) {
      return null;
    }

    final decryptedJson = _decryptPayload(encryptedPayload);
    return Map<String, dynamic>.from(jsonDecode(decryptedJson) as Map);
  }

  Future<void> _removeValue(String storageKey) async {
    final preferences = await SharedPreferences.getInstance();
    final didRemove = await preferences.remove(storageKey);

    if (!didRemove) {
      throw StateError('Failed to remove encrypted value for "$storageKey".');
    }
  }

  String _encryptPayload(String plainText) {
    final iv = encrypt.IV.fromSecureRandom(16);
    final encrypted = _encrypter.encrypt(plainText, iv: iv);

    return jsonEncode({
      'iv': iv.base64,
      'cipherText': encrypted.base64,
    });
  }

  String _decryptPayload(String encryptedPayload) {
    final payload = Map<String, dynamic>.from(
      jsonDecode(encryptedPayload) as Map,
    );

    final ivBase64 = payload['iv'] as String?;
    final cipherTextBase64 = payload['cipherText'] as String?;

    if (ivBase64 == null || cipherTextBase64 == null) {
      throw const FormatException('Invalid encrypted payload.');
    }

    return _encrypter.decrypt64(
      cipherTextBase64,
      iv: encrypt.IV.fromBase64(ivBase64),
    );
  }
}

class UserCredentials {
  const UserCredentials({
    required this.username,
    required this.password,
  });

  final String username;
  final String password;

  Map<String, dynamic> toJson() => {
        'username': username,
        'password': password,
      };

  factory UserCredentials.fromJson(Map<String, dynamic> json) {
    return UserCredentials(
      username: json['username'] as String,
      password: json['password'] as String,
    );
  }
}

class PaymentDetails {
  const PaymentDetails({
    required this.cardHolderName,
    required this.cardNumber,
    required this.expiryDate,
    required this.cvv,
    required this.billingZipCode,
  });

  final String cardHolderName;
  final String cardNumber;
  final String expiryDate;
  final String cvv;
  final String billingZipCode;

  Map<String, dynamic> toJson() => {
        'cardHolderName': cardHolderName,
        'cardNumber': cardNumber,
        'expiryDate': expiryDate,
        'cvv': cvv,
        'billingZipCode': billingZipCode,
      };

  factory PaymentDetails.fromJson(Map<String, dynamic> json) {
    return PaymentDetails(
      cardHolderName: json['cardHolderName'] as String,
      cardNumber: json['cardNumber'] as String,
      expiryDate: json['expiryDate'] as String,
      cvv: json['cvv'] as String,
      billingZipCode: json['billingZipCode'] as String,
    );
  }
}

class PersonalInformation {
  const PersonalInformation({
    required this.firstName,
    required this.lastName,
    required this.email,
    required this.phoneNumber,
    required this.addressLine1,
    this.addressLine2,
    required this.city,
    required this.state,
    required this.postalCode,
    required this.country,
  });

  final String firstName;
  final String lastName;
  final String email;
  final String phoneNumber;
  final String addressLine1;
  final String? addressLine2;
  final String city;
  final String state;
  final String postalCode;
  final String country;

  Map<String, dynamic> toJson() => {
        'firstName': firstName,
        'lastName': lastName,
        'email': email,
        'phoneNumber': phoneNumber,
        'addressLine1': addressLine1,
        'addressLine2': addressLine2,
        'city': city,
        'state': state,
        'postalCode': postalCode,
        'country': country,
      };

  factory PersonalInformation.fromJson(Map<String, dynamic> json) {
    return PersonalInformation(
      firstName: json['firstName'] as String,
      lastName: json['lastName'] as String,
      email: json['email'] as String,
      phoneNumber: json['phoneNumber'] as String,
      addressLine1: json['addressLine1'] as String,
      addressLine2: json['addressLine2'] as String?,
      city: json['city'] as String,
      state: json['state'] as String,
      postalCode: json['postalCode'] as String,
      country: json['country'] as String,
    );
  }
}