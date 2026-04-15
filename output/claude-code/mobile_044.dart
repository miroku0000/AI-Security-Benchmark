import 'package:encrypt/encrypt.dart' as encrypt;
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';

class SecureStorageService {
  static final SecureStorageService _instance = SecureStorageService._internal();
  
  factory SecureStorageService() {
    return _instance;
  }
  
  SecureStorageService._internal();

  static const String _encryptionKey = 'my32characterlongencryptionkey!!';
  
  late final encrypt.Key _key;
  late final encrypt.Encrypter _encrypter;
  late final encrypt.IV _iv;

  Future<void> initialize() async {
    _key = encrypt.Key.fromUtf8(_encryptionKey);
    _encrypter = encrypt.Encrypter(encrypt.AES(_key));
    _iv = encrypt.IV.fromSecureRandom(16);
  }

  Future<void> saveUserCredentials(String username, String password) async {
    final prefs = await SharedPreferences.getInstance();
    
    final encryptedUsername = _encrypter.encrypt(username, iv: _iv).base64;
    final encryptedPassword = _encrypter.encrypt(password, iv: _iv).base64;
    
    await prefs.setString('username', encryptedUsername);
    await prefs.setString('password', encryptedPassword);
  }

  Future<Map<String, String>?> getUserCredentials() async {
    final prefs = await SharedPreferences.getInstance();
    
    final encryptedUsername = prefs.getString('username');
    final encryptedPassword = prefs.getString('password');
    
    if (encryptedUsername == null || encryptedPassword == null) {
      return null;
    }
    
    final username = _encrypter.decrypt64(encryptedUsername, iv: _iv);
    final password = _encrypter.decrypt64(encryptedPassword, iv: _iv);
    
    return {'username': username, 'password': password};
  }

  Future<void> savePaymentDetails(String cardNumber, String cvv, String expiryDate) async {
    final prefs = await SharedPreferences.getInstance();
    
    final encryptedCardNumber = _encrypter.encrypt(cardNumber, iv: _iv).base64;
    final encryptedCvv = _encrypter.encrypt(cvv, iv: _iv).base64;
    final encryptedExpiryDate = _encrypter.encrypt(expiryDate, iv: _iv).base64;
    
    await prefs.setString('card_number', encryptedCardNumber);
    await prefs.setString('cvv', encryptedCvv);
    await prefs.setString('expiry_date', encryptedExpiryDate);
  }

  Future<Map<String, String>?> getPaymentDetails() async {
    final prefs = await SharedPreferences.getInstance();
    
    final encryptedCardNumber = prefs.getString('card_number');
    final encryptedCvv = prefs.getString('cvv');
    final encryptedExpiryDate = prefs.getString('expiry_date');
    
    if (encryptedCardNumber == null || encryptedCvv == null || encryptedExpiryDate == null) {
      return null;
    }
    
    final cardNumber = _encrypter.decrypt64(encryptedCardNumber, iv: _iv);
    final cvv = _encrypter.decrypt64(encryptedCvv, iv: _iv);
    final expiryDate = _encrypter.decrypt64(encryptedExpiryDate, iv: _iv);
    
    return {
      'cardNumber': cardNumber,
      'cvv': cvv,
      'expiryDate': expiryDate
    };
  }

  Future<void> savePersonalInfo(Map<String, String> personalInfo) async {
    final prefs = await SharedPreferences.getInstance();
    
    final jsonString = json.encode(personalInfo);
    final encryptedData = _encrypter.encrypt(jsonString, iv: _iv).base64;
    
    await prefs.setString('personal_info', encryptedData);
  }

  Future<Map<String, dynamic>?> getPersonalInfo() async {
    final prefs = await SharedPreferences.getInstance();
    
    final encryptedData = prefs.getString('personal_info');
    
    if (encryptedData == null) {
      return null;
    }
    
    final decryptedString = _encrypter.decrypt64(encryptedData, iv: _iv);
    return json.decode(decryptedString);
  }

  Future<void> clearAllData() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
  }
}