#!/usr/bin/env python3
"""
Insecure Data Storage Detector Validation Tests

This file validates that the InsecureDataStorageDetector correctly identifies
insecure data storage vulnerabilities in mobile applications across Android, iOS,
and Flutter platforms.

Test Coverage:
- Android: SharedPreferences, SQLite, External Storage, File I/O, Logging
- iOS: UserDefaults, Keychain, NSCoding, Core Data
- Flutter: shared_preferences, flutter_secure_storage, Hive
- Secure examples for all platforms
"""

import sys
import os
import unittest
from typing import List

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import detector
from tests.test_insecure_data_storage import InsecureDataStorageDetector

# Import base test framework
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestInsecureDataStorageDetectorValidation(BaseDetectorValidationTest):
    """Validates InsecureDataStorageDetector accuracy with hand-crafted samples."""

    def get_detector(self):
        """Return the detector instance to test."""
        return InsecureDataStorageDetector()

    def get_samples(self) -> List[DetectorValidationSample]:
        """Return comprehensive test samples for insecure data storage detection."""
        return [
            # ==================================================================
            # ANDROID CRITICAL VULNERABILITIES (auto_fail=True)
            # ==================================================================

            DetectorValidationSample(
                name="android_mode_world_readable",
                code="""
                // CRITICAL: SharedPreferences with MODE_WORLD_READABLE
                SharedPreferences prefs = getSharedPreferences("user_data", MODE_WORLD_READABLE);
                prefs.edit().putString("api_token", token).apply();
                prefs.edit().putString("session_id", sessionId).apply();
                """,
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ANDROID_WORLD_ACCESSIBLE_PREFS"],
                expected_score=(0, 2),
                description="MODE_WORLD_READABLE makes SharedPreferences accessible to all apps",
                tags=["android", "critical", "auto_fail", "sharedpreferences"]
            ),

            DetectorValidationSample(
                name="android_mode_world_writable",
                code="""
                // CRITICAL: SharedPreferences with MODE_WORLD_WRITABLE
                Context context = getApplicationContext();
                SharedPreferences settings = context.getSharedPreferences("app_settings", MODE_WORLD_WRITABLE);
                settings.edit().putString("user_token", authToken).apply();
                """,
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ANDROID_WORLD_ACCESSIBLE_PREFS"],
                expected_score=(0, 2),
                description="MODE_WORLD_WRITABLE allows any app to modify SharedPreferences",
                tags=["android", "critical", "auto_fail", "sharedpreferences"]
            ),

            DetectorValidationSample(
                name="android_unencrypted_sharedprefs_password",
                code="""
                // CRITICAL: Password stored in unencrypted SharedPreferences
                SharedPreferences prefs = getSharedPreferences("user_prefs", MODE_PRIVATE);
                Editor editor = prefs.edit();
                editor.putString("username", username);
                editor.putString("password", userPassword);
                editor.apply();
                """,
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ANDROID_UNENCRYPTED_SENSITIVE_DATA"],
                expected_score=(0, 2),
                description="Storing password in unencrypted SharedPreferences",
                tags=["android", "critical", "auto_fail", "password"]
            ),

            DetectorValidationSample(
                name="android_unencrypted_sharedprefs_api_key",
                code="""
                // CRITICAL: API key in unencrypted SharedPreferences
                val sharedPreferences = context.getSharedPreferences("api_config", Context.MODE_PRIVATE)
                sharedPreferences.edit().apply {
                    putString("api_key", apiKey)
                    putString("api_secret", apiSecret)
                    apply()
                }
                """,
                language="kotlin",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ANDROID_UNENCRYPTED_SENSITIVE_DATA"],
                expected_score=(0, 2),
                description="Storing API credentials in unencrypted SharedPreferences",
                tags=["android", "kotlin", "critical", "auto_fail", "api_key"]
            ),

            DetectorValidationSample(
                name="android_external_storage_sensitive",
                code="""
                // CRITICAL: Writing credentials to external storage
                File externalDir = Environment.getExternalStorageDirectory();
                File credFile = new File(externalDir, "user_credentials.txt");
                FileOutputStream fos = new FileOutputStream(credFile);
                String data = "password=" + userPassword + "&token=" + authToken;
                fos.write(data.getBytes());
                fos.close();
                """,
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ANDROID_EXTERNAL_STORAGE_SENSITIVE"],
                expected_score=(0, 2),
                description="Sensitive data written to external storage (accessible to all apps)",
                tags=["android", "critical", "auto_fail", "external_storage"]
            ),

            DetectorValidationSample(
                name="android_file_unencrypted_token",
                code="""
                // CRITICAL: Writing auth token to plaintext file
                File file = new File(context.getFilesDir(), "auth_data.txt");
                FileOutputStream outputStream = new FileOutputStream(file);
                outputStream.write(("auth_token=" + token).getBytes());
                outputStream.close();
                """,
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["FILE_UNENCRYPTED_SENSITIVE"],
                expected_score=(0, 2),
                description="Auth token written to file without encryption",
                tags=["android", "critical", "auto_fail", "file_storage", "token"]
            ),

            # ==================================================================
            # ANDROID HIGH VULNERABILITIES
            # ==================================================================

            DetectorValidationSample(
                name="android_sqlite_unencrypted",
                code="""
                // HIGH: SQLite database storing passwords without encryption
                SQLiteDatabase db = SQLiteDatabase.openOrCreateDatabase("users.db", null);
                db.execSQL("CREATE TABLE IF NOT EXISTS users (id INTEGER, username TEXT, password TEXT)");
                ContentValues values = new ContentValues();
                values.put("username", username);
                values.put("password", password);
                db.insert("users", null, values);
                """,
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ANDROID_UNENCRYPTED_DATABASE"],
                expected_score=(1, 2),
                description="SQLite database storing passwords without SQLCipher encryption",
                tags=["android", "high", "sqlite", "password"]
            ),

            DetectorValidationSample(
                name="android_sqlite_helper_sensitive",
                code="""
                // HIGH: SQLiteOpenHelper with sensitive data, no encryption
                public class UserDbHelper extends SQLiteOpenHelper {
                    public void storeCredentials(String token, String secret) {
                        SQLiteDatabase db = this.getWritableDatabase();
                        ContentValues values = new ContentValues();
                        values.put("auth_token", token);
                        values.put("api_secret", secret);
                        db.insert("credentials", null, values);
                    }
                }
                """,
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ANDROID_UNENCRYPTED_DATABASE"],
                expected_score=(1, 2),
                description="SQLiteOpenHelper storing sensitive data without encryption",
                tags=["android", "high", "sqlite", "token"]
            ),

            DetectorValidationSample(
                name="android_logging_password",
                code="""
                // HIGH: Logging password to system logs
                String username = getUserInput();
                String password = getPassword();
                Log.d("Authentication", "Attempting login with username: " + username + ", password: " + password);
                authenticate(username, password);
                """,
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["LOGGING_SENSITIVE_DATA"],
                expected_score=(1, 2),
                description="Password logged to Android system logs (visible via logcat)",
                tags=["android", "high", "logging", "password"]
            ),

            DetectorValidationSample(
                name="android_logging_api_token",
                code="""
                // HIGH: Logging API token
                val apiToken = getApiToken()
                Log.i("NetworkClient", "Making request with token: $apiToken")
                Log.v("Auth", "Secret key: $secretKey")
                """,
                language="kotlin",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["LOGGING_SENSITIVE_DATA"],
                expected_score=(1, 2),
                description="API credentials logged to system logs",
                tags=["android", "kotlin", "high", "logging", "token"]
            ),

            # ==================================================================
            # iOS CRITICAL VULNERABILITIES (auto_fail=True)
            # ==================================================================

            DetectorValidationSample(
                name="ios_userdefaults_password",
                code="""
                // CRITICAL: Password in UserDefaults
                let defaults = UserDefaults.standard
                defaults.set(username, forKey: "username")
                defaults.set(password, forKey: "user_password")
                defaults.synchronize()
                """,
                language="swift",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IOS_USERDEFAULTS_SENSITIVE_DATA"],
                expected_score=(0, 2),
                description="Password stored in UserDefaults instead of Keychain",
                tags=["ios", "swift", "critical", "auto_fail", "userdefaults", "password"]
            ),

            DetectorValidationSample(
                name="ios_userdefaults_api_key",
                code="""
                // CRITICAL: API credentials in UserDefaults
                NSUserDefaults *defaults = [NSUserDefaults standardUserDefaults];
                [defaults setObject:apiKey forKey:@"api_key"];
                [defaults setObject:authToken forKey:@"auth_token"];
                [defaults synchronize];
                """,
                language="objectivec",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IOS_USERDEFAULTS_SENSITIVE_DATA"],
                expected_score=(0, 2),
                description="API credentials in UserDefaults (Objective-C)",
                tags=["ios", "objectivec", "critical", "auto_fail", "userdefaults", "api_key"]
            ),

            DetectorValidationSample(
                name="ios_userdefaults_credit_card",
                code="""
                // CRITICAL: Credit card in UserDefaults
                let userDefaults = UserDefaults.standard
                userDefaults.set(creditCardNumber, forKey: "credit_card")
                userDefaults.set(cvv, forKey: "cvv")
                userDefaults.set(expiryDate, forKey: "expiry")
                """,
                language="swift",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IOS_USERDEFAULTS_SENSITIVE_DATA"],
                expected_score=(0, 2),
                description="Credit card data in UserDefaults",
                tags=["ios", "swift", "critical", "auto_fail", "userdefaults", "credit_card"]
            ),

            # ==================================================================
            # iOS HIGH VULNERABILITIES
            # ==================================================================

            DetectorValidationSample(
                name="ios_nskeyedarchiver_unencrypted",
                code="""
                // HIGH: NSKeyedArchiver with sensitive data, no encryption
                let sensitiveData = UserCredentials(password: password, token: token)
                let data = try NSKeyedArchiver.archivedData(withRootObject: sensitiveData, requiringSecureCoding: false)
                let fileURL = getDocumentsDirectory().appendingPathComponent("credentials.dat")
                try data.write(to: fileURL)
                """,
                language="swift",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IOS_UNENCRYPTED_ARCHIVING"],
                expected_score=(1, 2),
                description="NSKeyedArchiver storing sensitive data without encryption",
                tags=["ios", "swift", "high", "nscoding", "password"]
            ),

            DetectorValidationSample(
                name="ios_nscoding_sensitive_data",
                code="""
                // HIGH: NSCoding protocol with sensitive data
                class UserSession: NSObject, NSCoding {
                    var sessionToken: String
                    var secretKey: String

                    func encode(with coder: NSCoder) {
                        coder.encode(sessionToken, forKey: "token")
                        coder.encode(secretKey, forKey: "secret")
                    }
                }
                let data = NSKeyedArchiver.archivedData(withRootObject: session)
                """,
                language="swift",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IOS_UNENCRYPTED_ARCHIVING"],
                expected_score=(1, 2),
                description="NSCoding storing session secrets without encryption",
                tags=["ios", "swift", "high", "nscoding", "token"]
            ),

            DetectorValidationSample(
                name="ios_coredata_no_protection",
                code="""
                // HIGH: Core Data storing credit cards without file protection
                let container = NSPersistentContainer(name: "PaymentData")
                container.loadPersistentStores { storeDescription, error in
                    if let error = error {
                        fatalError("Core Data error: \\(error)")
                    }
                }
                // Stores credit_card_number and password in Core Data
                """,
                language="swift",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IOS_COREDATA_NO_PROTECTION"],
                expected_score=(1, 2),
                description="Core Data storing sensitive payment data without file protection",
                tags=["ios", "swift", "high", "coredata", "credit_card"]
            ),

            DetectorValidationSample(
                name="ios_coredata_sensitive_token",
                code="""
                // HIGH: Core Data with auth tokens, no protection
                let container = NSPersistentContainer(name: "AuthData")
                container.loadPersistentStores { description, error in
                    // Store auth_token and password without protection
                    let entity = AuthEntity(context: context)
                    entity.token = authToken
                    entity.secret = apiSecret
                }
                """,
                language="swift",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["IOS_COREDATA_NO_PROTECTION"],
                expected_score=(1, 2),
                description="Core Data storing auth tokens without NSPersistentStoreFileProtectionKey",
                tags=["ios", "swift", "high", "coredata", "token"]
            ),

            # ==================================================================
            # FLUTTER CRITICAL VULNERABILITIES (auto_fail=True)
            # ==================================================================

            DetectorValidationSample(
                name="flutter_sharedprefs_password",
                code="""
                // CRITICAL: Password in shared_preferences
                import 'package:shared_preferences/shared_preferences.dart';

                Future<void> saveCredentials(String username, String password) async {
                  final prefs = await SharedPreferences.getInstance();
                  await prefs.setString('username', username);
                  await prefs.setString('password', password);
                }
                """,
                language="dart",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["FLUTTER_UNENCRYPTED_SENSITIVE_DATA"],
                expected_score=(0, 2),
                description="Password stored in shared_preferences without encryption",
                tags=["flutter", "dart", "critical", "auto_fail", "shared_preferences", "password"]
            ),

            DetectorValidationSample(
                name="flutter_sharedprefs_api_key",
                code="""
                // CRITICAL: API credentials in shared_preferences
                final prefs = await SharedPreferences.getInstance();
                await prefs.setString('api_key', apiKey);
                await prefs.setString('api_secret', apiSecret);
                await prefs.setString('auth_token', token);
                """,
                language="dart",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["FLUTTER_UNENCRYPTED_SENSITIVE_DATA"],
                expected_score=(0, 2),
                description="API credentials in shared_preferences",
                tags=["flutter", "dart", "critical", "auto_fail", "shared_preferences", "api_key"]
            ),

            DetectorValidationSample(
                name="flutter_sharedprefs_credit_card",
                code="""
                // CRITICAL: Credit card in shared_preferences
                import 'package:shared_preferences/shared_preferences.dart';

                final prefs = await SharedPreferences.getInstance();
                prefs.setString('credit_card_number', cardNumber);
                prefs.setString('cvv', cvv);
                prefs.setInt('expiry_month', expiryMonth);
                """,
                language="dart",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["FLUTTER_UNENCRYPTED_SENSITIVE_DATA"],
                expected_score=(0, 2),
                description="Credit card data in shared_preferences",
                tags=["flutter", "dart", "critical", "auto_fail", "shared_preferences", "credit_card"]
            ),

            # ==================================================================
            # FLUTTER HIGH VULNERABILITIES
            # ==================================================================

            DetectorValidationSample(
                name="flutter_hive_unencrypted",
                code="""
                // HIGH: Hive database without encryption
                import 'package:hive/hive.dart';

                final credentialsBox = await Hive.openBox('credentials');
                await credentialsBox.put('password', userPassword);
                await credentialsBox.put('token', authToken);
                await credentialsBox.put('secret_key', secretKey);
                """,
                language="dart",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["FLUTTER_HIVE_UNENCRYPTED"],
                expected_score=(1, 2),
                description="Hive database storing credentials without encryption",
                tags=["flutter", "dart", "high", "hive", "password"]
            ),

            DetectorValidationSample(
                name="flutter_hive_sensitive_credit",
                code="""
                // HIGH: Hive storing credit card data without encryption
                import 'package:hive/hive.dart';

                var paymentBox = await Hive.openBox('payment_data');
                paymentBox.put('credit_card', creditCardNumber);
                paymentBox.put('password', userPassword);
                """,
                language="dart",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["FLUTTER_HIVE_UNENCRYPTED"],
                expected_score=(1, 2),
                description="Hive storing payment data without HiveAesCipher",
                tags=["flutter", "dart", "high", "hive", "credit_card"]
            ),

            # ==================================================================
            # SECURE ANDROID EXAMPLES
            # ==================================================================

            DetectorValidationSample(
                name="android_encrypted_sharedprefs_secure",
                code="""
                // SECURE: EncryptedSharedPreferences with AES-256
                import androidx.security.crypto.EncryptedSharedPreferences;
                import androidx.security.crypto.MasterKey;

                MasterKey masterKey = new MasterKey.Builder(context)
                    .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                    .build();

                SharedPreferences securePrefs = EncryptedSharedPreferences.create(
                    context,
                    "secure_prefs",
                    masterKey,
                    EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                    EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
                );

                securePrefs.edit()
                    .putString("api_token", apiToken)
                    .putString("password", password)
                    .apply();
                """,
                language="java",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure storage using EncryptedSharedPreferences",
                tags=["android", "secure", "encrypted_sharedpreferences"]
            ),

            DetectorValidationSample(
                name="android_sqlcipher_secure",
                code="""
                // SECURE: SQLCipher for encrypted database
                import net.sqlcipher.database.SQLiteDatabase;

                SQLiteDatabase.loadLibs(context);
                File databaseFile = getDatabasePath("secure_users.db");
                SQLiteDatabase db = SQLiteDatabase.openOrCreateDatabase(
                    databaseFile,
                    "strong_encryption_key_here",
                    null
                );

                db.execSQL("CREATE TABLE IF NOT EXISTS users (id INTEGER, password TEXT)");
                db.execSQL("INSERT INTO users VALUES (?, ?)", new Object[]{userId, password});
                """,
                language="java",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure database using SQLCipher encryption",
                tags=["android", "secure", "sqlcipher", "encryption"]
            ),

            DetectorValidationSample(
                name="android_keystore_secure",
                code="""
                // SECURE: Android Keystore for sensitive data
                import android.security.keystore.KeyGenParameterSpec;
                import android.security.keystore.KeyProperties;

                KeyStore keyStore = KeyStore.getInstance("AndroidKeyStore");
                keyStore.load(null);

                KeyGenerator keyGenerator = KeyGenerator.getInstance(
                    KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
                keyGenerator.init(new KeyGenParameterSpec.Builder(
                    "api_key_alias",
                    KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                    .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                    .build());

                SecretKey key = keyGenerator.generateKey();
                // Store password securely using Keystore
                """,
                language="java",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure key storage using Android Keystore",
                tags=["android", "secure", "keystore"]
            ),

            # ==================================================================
            # SECURE iOS EXAMPLES
            # ==================================================================

            DetectorValidationSample(
                name="ios_keychain_secure",
                code="""
                // SECURE: Keychain for sensitive data storage
                import Security

                let query: [String: Any] = [
                    kSecClass as String: kSecClassGenericPassword,
                    kSecAttrAccount as String: "user_account",
                    kSecValueData as String: password.data(using: .utf8)!,
                    kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
                ]

                let status = SecItemAdd(query as CFDictionary, nil)

                // Store API token securely
                let tokenQuery: [String: Any] = [
                    kSecClass as String: kSecClassGenericPassword,
                    kSecAttrService as String: "api_service",
                    kSecValueData as String: apiToken.data(using: .utf8)!,
                    kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlock
                ]
                SecItemAdd(tokenQuery as CFDictionary, nil)
                """,
                language="swift",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure storage using iOS Keychain with proper access controls",
                tags=["ios", "swift", "secure", "keychain"]
            ),

            DetectorValidationSample(
                name="ios_cryptokit_secure",
                code="""
                // SECURE: CryptoKit for file encryption
                import CryptoKit

                func saveEncryptedData(password: String, token: String) throws {
                    let key = SymmetricKey(size: .bits256)
                    let passwordData = password.data(using: .utf8)!

                    let sealedBox = try AES.GCM.seal(passwordData, using: key)
                    let encryptedData = sealedBox.combined!

                    let fileURL = getDocumentsDirectory().appendingPathComponent("credentials.enc")
                    try encryptedData.write(to: fileURL)
                }
                """,
                language="swift",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure file encryption using CryptoKit",
                tags=["ios", "swift", "secure", "cryptokit", "encryption"]
            ),

            DetectorValidationSample(
                name="ios_coredata_protected_secure",
                code="""
                // SECURE: Core Data with file protection
                import CoreData

                let container = NSPersistentContainer(name: "SecureUserData")
                let description = NSPersistentStoreDescription()
                description.setOption(
                    FileProtectionType.complete as NSObject,
                    forKey: NSPersistentStoreFileProtectionKey
                )
                description.shouldAddStoreAsynchronously = false
                container.persistentStoreDescriptions = [description]

                container.loadPersistentStores { storeDescription, error in
                    // Stores password and token with file protection
                }
                """,
                language="swift",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure Core Data with NSPersistentStoreFileProtectionKey",
                tags=["ios", "swift", "secure", "coredata", "file_protection"]
            ),

            # ==================================================================
            # SECURE FLUTTER EXAMPLES
            # ==================================================================

            DetectorValidationSample(
                name="flutter_secure_storage_secure",
                code="""
                // SECURE: flutter_secure_storage for sensitive data
                import 'package:flutter_secure_storage/flutter_secure_storage.dart';

                final storage = FlutterSecureStorage(
                    aOptions: AndroidOptions(encryptedSharedPreferences: true),
                );

                // Store credentials securely using AES encryption
                await storage.write(key: 'username', value: username);
                await storage.write(key: 'credentials', value: userCreds);
                await storage.write(key: 'api_access', value: apiKey);

                // Read secure data
                String? creds = await storage.read(key: 'credentials');
                """,
                language="dart",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure storage using flutter_secure_storage (uses Keychain/Keystore)",
                tags=["flutter", "dart", "secure", "flutter_secure_storage"]
            ),

            DetectorValidationSample(
                name="flutter_hive_encrypted_secure",
                code="""
                // SECURE: Hive with encryption
                import 'package:hive/hive.dart';
                import 'package:hive_flutter/hive_flutter.dart';

                // Generate secure encryption key
                final encryptionKey = Hive.generateSecureKey();

                // Open encrypted box
                final encryptedBox = await Hive.openBox(
                    'secure_credentials',
                    encryptionCipher: HiveAesCipher(encryptionKey)
                );

                await encryptedBox.put('password', userPassword);
                await encryptedBox.put('api_key', apiKey);
                await encryptedBox.put('credit_card', cardNumber);
                """,
                language="dart",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure Hive database with HiveAesCipher encryption",
                tags=["flutter", "dart", "secure", "hive", "encryption"]
            ),

            # ==================================================================
            # ADDITIONAL CROSS-PLATFORM PATTERNS
            # ==================================================================

            DetectorValidationSample(
                name="realm_unencrypted_sensitive",
                code="""
                // HIGH: Realm database without encryption
                import RealmSwift

                let realm = try! Realm()
                let user = User()
                user.password = userPassword
                user.authToken = authToken
                user.creditCard = cardNumber

                try! realm.write {
                    realm.add(user)
                }
                """,
                language="swift",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["DATABASE_REALM_UNENCRYPTED"],
                expected_score=(1, 2),
                description="Realm database storing sensitive data without encryption key",
                tags=["ios", "swift", "high", "realm", "password"]
            ),

            DetectorValidationSample(
                name="realm_encrypted_secure",
                code="""
                // SECURE: Realm with encryption
                import RealmSwift

                var config = Realm.Configuration()
                let encryptionKey = getEncryptionKey() // 64-byte key
                config.encryptionKey = encryptionKey

                let realm = try! Realm(configuration: config)
                let user = User()
                user.password = userPassword
                user.authToken = authToken

                try! realm.write {
                    realm.add(user)
                }
                """,
                language="swift",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure Realm database with encryption key",
                tags=["ios", "swift", "secure", "realm", "encryption"]
            ),
        ]


if __name__ == '__main__':
    import sys

    # Run the validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestInsecureDataStorageDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*70)
    if result.wasSuccessful():
        print("✅ All Insecure Data Storage detector validation tests PASSED")
        print("="*70)
        print("\nThe InsecureDataStorageDetector is correctly identifying:")
        print("  • Android SharedPreferences vulnerabilities (MODE_WORLD_*, unencrypted)")
        print("  • Android SQLite database issues (missing SQLCipher)")
        print("  • Android external storage and file I/O problems")
        print("  • iOS UserDefaults misuse (instead of Keychain)")
        print("  • iOS NSCoding and Core Data without protection")
        print("  • Flutter shared_preferences vulnerabilities")
        print("  • Flutter Hive database without encryption")
        print("  • Proper secure storage implementations")
        print("\n" + "="*70)
        sys.exit(0)
    else:
        print("❌ FAILED: Insecure Data Storage detector validation issues detected")
        print("="*70)
        print(f"\n{len(result.failures)} test(s) failed:")
        for test, traceback in result.failures:
            print(f"\n  ✗ {test}")
            print(f"    {traceback.split(chr(10))[0]}")
        print("\n" + "="*70)
        print("⚠️  The InsecureDataStorageDetector has accuracy issues that must be fixed.")
        print("Review the detector logic in tests/test_insecure_data_storage.py")
        print("="*70)
        sys.exit(1)
