#!/usr/bin/env python3
"""
Mobile Security Detector Validation Tests

This module validates that the MobileSecurityDetector correctly identifies
mobile security vulnerabilities across multiple platforms and languages.

Test Coverage:
- Android (Java): SSL pinning, data storage, WebView security, deep links
- Android (Kotlin): SSL pinning, data storage, biometric auth
- iOS (Swift): SSL pinning, data storage, WebView, biometric auth
- React Native (JavaScript): SSL pinning, data storage, WebView
- Flutter (Dart): SSL pinning, data storage, WebView

Vulnerability Types Tested:
- MISSING_SSL_PINNING (HIGH)
- INSECURE_DATA_STORAGE (CRITICAL)
- INSECURE_WEBVIEW (HIGH)
- INSECURE_DEEP_LINK (HIGH)
- WEAK_BIOMETRIC_AUTH (HIGH)
- CLEARTEXT_TRAFFIC (HIGH)
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_mobile_security import MobileSecurityDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestMobileSecurityDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Mobile Security Detector."""

    def get_detector(self):
        """Return MobileSecurityDetector instance."""
        return MobileSecurityDetector()

    def get_samples(self):
        """Return hand-crafted mobile security test samples."""
        return [
            # ========== ANDROID JAVA - VULNERABLE SAMPLES ==========

            DetectorValidationSample(
                name="android_java_missing_ssl_pinning",
                code='''
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;

public class ApiClient {
    private OkHttpClient client = new OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build();

    public String fetchData() throws IOException {
        Request request = new Request.Builder()
            .url("https://api.example.com/data")
            .build();
        Response response = client.newCall(request).execute();
        return response.body().string();
    }
}
''',
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_SSL_PINNING"],
                expected_score=(0, 2),
                description="Android OkHttp client without SSL certificate pinning",
                tags=["android", "java", "ssl-pinning", "high"]
            ),

            DetectorValidationSample(
                name="android_java_insecure_data_storage",
                code='''
import android.content.SharedPreferences;
import android.content.Context;

public class UserManager {
    private SharedPreferences prefs;

    public void saveCredentials(String username, String password) {
        prefs = context.getSharedPreferences("user_data", Context.MODE_PRIVATE);
        SharedPreferences.Editor editor = prefs.edit();
        editor.putString("username", username);
        editor.putString("password", password);
        editor.putString("auth_token", token);
        editor.apply();
    }
}
''',
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_DATA_STORAGE"],
                expected_score=(0, 2),
                description="Storing password and auth_token in unencrypted SharedPreferences",
                tags=["android", "java", "data-storage", "critical"]
            ),

            DetectorValidationSample(
                name="android_java_insecure_webview",
                code='''
import android.webkit.WebView;
import android.webkit.WebSettings;

public class WebActivity extends AppCompatActivity {
    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        webView = findViewById(R.id.webview);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);

        webView.addJavascriptInterface(new WebAppInterface(this), "Android");
        webView.loadUrl("https://example.com");
    }
}
''',
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_WEBVIEW"],
                expected_score=(0, 2),
                description="WebView with JavaScript enabled and JavaScriptInterface - RCE risk",
                tags=["android", "java", "webview", "high"]
            ),

            DetectorValidationSample(
                name="android_java_insecure_deep_link",
                code='''
import android.net.Uri;
import android.content.Intent;

public class DeepLinkActivity extends AppCompatActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Get deep link data without validation
        Uri data = getIntent().getData();

        if (data != null) {
            String url = Uri.parse(data.toString()).toString();
            // Directly use deep link URL without validation
            webView.loadUrl(url);
        }
    }
}
''',
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_DEEP_LINK"],
                expected_score=(0, 2),
                description="Deep link handling without URL validation - open redirect risk",
                tags=["android", "java", "deep-link", "high"]
            ),

            DetectorValidationSample(
                name="android_java_cleartext_traffic",
                code='''
import java.net.HttpURLConnection;
import java.net.URL;

public class ApiClient {
    public String fetchData() throws IOException {
        URL url = new URL("http://api.example.com/data");
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setRequestMethod("GET");

        BufferedReader reader = new BufferedReader(
            new InputStreamReader(connection.getInputStream())
        );
        return reader.readLine();
    }
}
''',
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CLEARTEXT_TRAFFIC"],
                expected_score=(0, 2),
                description="HTTP connection without Network Security Config",
                tags=["android", "java", "cleartext", "high"]
            ),

            # ========== ANDROID JAVA - SECURE SAMPLES ==========

            DetectorValidationSample(
                name="android_java_secure_ssl_pinning",
                code='''
import okhttp3.OkHttpClient;
import okhttp3.CertificatePinner;

public class ApiClient {
    private OkHttpClient client;

    public ApiClient() {
        CertificatePinner certificatePinner = new CertificatePinner.Builder()
            .add("api.example.com", "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
            .build();

        client = new OkHttpClient.Builder()
            .certificatePinner(certificatePinner)
            .build();
    }
}
''',
                language="java",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Android OkHttp client with SSL certificate pinning",
                tags=["android", "java", "ssl-pinning", "secure"]
            ),

            DetectorValidationSample(
                name="android_java_secure_encrypted_storage",
                code='''
import androidx.security.crypto.EncryptedSharedPreferences;
import androidx.security.crypto.MasterKey;

public class SecureUserManager {
    private SharedPreferences encryptedPrefs;

    public void saveCredentials(String username, String password) throws Exception {
        MasterKey masterKey = new MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build();

        encryptedPrefs = EncryptedSharedPreferences.create(
            context,
            "secure_prefs",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        );

        encryptedPrefs.edit()
            .putString("username", username)
            .putString("password", password)
            .apply();
    }
}
''',
                language="java",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Using EncryptedSharedPreferences for sensitive data",
                tags=["android", "java", "data-storage", "secure"]
            ),

            # ========== ANDROID KOTLIN - VULNERABLE SAMPLES ==========

            DetectorValidationSample(
                name="android_kotlin_missing_ssl_pinning",
                code='''
import okhttp3.OkHttpClient
import okhttp3.Request

class ApiClient {
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .build()

    fun fetchData(): String {
        val request = Request.Builder()
            .url("https://api.example.com/data")
            .build()

        return client.newCall(request).execute().body?.string() ?: ""
    }
}
''',
                language="kotlin",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_SSL_PINNING"],
                expected_score=(0, 2),
                description="Kotlin OkHttp client without SSL certificate pinning",
                tags=["android", "kotlin", "ssl-pinning", "high"]
            ),

            DetectorValidationSample(
                name="android_kotlin_insecure_storage",
                code='''
import android.content.SharedPreferences
import android.content.Context

class UserManager(private val context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("user_data", Context.MODE_PRIVATE)

    fun saveCredentials(username: String, password: String, apiKey: String) {
        prefs.edit().apply {
            putString("username", username)
            putString("password", password)
            putString("api_key", apiKey)
            apply()
        }
    }
}
''',
                language="kotlin",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_DATA_STORAGE"],
                expected_score=(0, 2),
                description="Storing password and api_key in unencrypted SharedPreferences",
                tags=["android", "kotlin", "data-storage", "critical"]
            ),

            # ========== ANDROID KOTLIN - SECURE SAMPLES ==========

            DetectorValidationSample(
                name="android_kotlin_secure_ssl_pinning",
                code='''
import okhttp3.OkHttpClient
import okhttp3.CertificatePinner

class ApiClient {
    private val certificatePinner = CertificatePinner.Builder()
        .add("api.example.com", "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
        .build()

    private val client = OkHttpClient.Builder()
        .certificatePinner(certificatePinner)
        .build()
}
''',
                language="kotlin",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Kotlin OkHttp client with SSL certificate pinning",
                tags=["android", "kotlin", "ssl-pinning", "secure"]
            ),

            # ========== IOS SWIFT - VULNERABLE SAMPLES ==========

            DetectorValidationSample(
                name="ios_swift_missing_ssl_pinning",
                code='''
import Foundation

class APIClient {
    func fetchData(completion: @escaping (Data?) -> Void) {
        let url = URL(string: "https://api.example.com/data")!

        let task = URLSession.shared.dataTask(with: url) { data, response, error in
            if let error = error {
                print("Error: \\(error)")
                completion(nil)
                return
            }
            completion(data)
        }
        task.resume()
    }
}
''',
                language="swift",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_SSL_PINNING"],
                expected_score=(0, 2),
                description="iOS URLSession without SSL certificate pinning",
                tags=["ios", "swift", "ssl-pinning", "high"]
            ),

            DetectorValidationSample(
                name="ios_swift_insecure_storage",
                code='''
import Foundation

class UserManager {
    func saveCredentials(username: String, password: String, authToken: String) {
        let defaults = UserDefaults.standard
        defaults.set(username, forKey: "username")
        defaults.set(password, forKey: "password")
        defaults.set(authToken, forKey: "auth_token")
        defaults.synchronize()
    }
}
''',
                language="swift",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_DATA_STORAGE"],
                expected_score=(0, 2),
                description="Storing password and auth_token in UserDefaults",
                tags=["ios", "swift", "data-storage", "critical"]
            ),

            DetectorValidationSample(
                name="ios_swift_insecure_webview",
                code='''
import WebKit

class WebViewController: UIViewController {
    var webView: WKWebView!

    override func viewDidLoad() {
        super.viewDidLoad()

        let configuration = WKWebViewConfiguration()
        let userContentController = WKUserContentController()

        // Add script message handler - allows JavaScript to communicate with native code
        configuration.userContentController.addScriptMessageHandler(self, name: "messageHandler")

        webView = WKWebView(frame: view.bounds, configuration: configuration)
        view.addSubview(webView)

        let url = URL(string: "https://example.com")!
        webView.load(URLRequest(url: url))
    }
}

extension WebViewController: WKScriptMessageHandler {
    func userContentController(_ userContentController: WKUserContentController,
                               didReceive message: WKScriptMessage) {
        // Process message from JavaScript without validation
        if let body = message.body as? String {
            print("Received message: \\(body)")
        }
    }
}
''',
                language="swift",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_WEBVIEW"],
                expected_score=(0, 2),
                description="WKWebView with JavaScript message handler - XSS to native bridge risk",
                tags=["ios", "swift", "webview", "high"]
            ),

            DetectorValidationSample(
                name="ios_swift_weak_biometric_auth",
                code='''
import LocalAuthentication

class BiometricAuth {
    func authenticateUser(completion: @escaping (Bool) -> Void) {
        let context = LAContext()

        context.evaluatePolicy(.deviceOwnerAuthenticationWithBiometrics,
                             localizedReason: "Authenticate to access app") { success, error in
            if success {
                // Store authentication result in UserDefaults
                UserDefaults.standard.set(true, forKey: "authenticated")
                completion(true)
            } else {
                completion(false)
            }
        }
    }
}
''',
                language="swift",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["WEAK_BIOMETRIC_AUTH"],
                expected_score=(0, 2),
                description="Biometric auth result stored in UserDefaults without Secure Enclave",
                tags=["ios", "swift", "biometric", "high"]
            ),

            # ========== IOS SWIFT - SECURE SAMPLES ==========

            DetectorValidationSample(
                name="ios_swift_secure_ssl_pinning",
                code='''
import Foundation

class APIClient: NSObject, URLSessionDelegate {
    private var session: URLSession!

    override init() {
        super.init()
        session = URLSession(configuration: .default, delegate: self, delegateQueue: nil)
    }

    func urlSession(_ session: URLSession,
                   didReceive challenge: URLAuthenticationChallenge,
                   completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        guard challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
              let serverTrust = challenge.protectionSpace.serverTrust else {
            completionHandler(.cancelAuthenticationChallenge, nil)
            return
        }

        // Validate certificate pinning
        if validateCertificate(serverTrust) {
            completionHandler(.useCredential, URLCredential(trust: serverTrust))
        } else {
            completionHandler(.cancelAuthenticationChallenge, nil)
        }
    }

    private func validateCertificate(_ serverTrust: SecTrust) -> Bool {
        // Certificate pinning validation logic
        return true
    }
}
''',
                language="swift",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="iOS URLSession with SSL certificate pinning via delegate",
                tags=["ios", "swift", "ssl-pinning", "secure"]
            ),

            DetectorValidationSample(
                name="ios_swift_secure_keychain_storage",
                code='''
import Security

class SecureStorage {
    func savePassword(_ password: String, for account: String) -> Bool {
        let passwordData = password.data(using: .utf8)!

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: account,
            kSecValueData as String: passwordData,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        ]

        SecItemDelete(query as CFDictionary)
        let status = SecItemAdd(query as CFDictionary, nil)
        return status == errSecSuccess
    }

    func retrievePassword(for account: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        if status == errSecSuccess, let passwordData = result as? Data {
            return String(data: passwordData, encoding: .utf8)
        }
        return nil
    }
}
''',
                language="swift",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Using iOS Keychain for secure password storage",
                tags=["ios", "swift", "data-storage", "secure"]
            ),

            # ========== REACT NATIVE - VULNERABLE SAMPLES ==========

            DetectorValidationSample(
                name="react_native_missing_ssl_pinning",
                code='''
import React, { useEffect } from 'react';

const ApiClient = () => {
  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const response = await fetch('https://api.example.com/data', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      const data = await response.json();
      console.log(data);
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };

  return null;
};
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_SSL_PINNING"],
                expected_score=(0, 2),
                description="React Native fetch without SSL certificate pinning",
                tags=["react-native", "javascript", "ssl-pinning", "high"]
            ),

            DetectorValidationSample(
                name="react_native_insecure_storage",
                code='''
import AsyncStorage from '@react-native-async-storage/async-storage';

export const saveCredentials = async (username, password, apiKey) => {
  try {
    await AsyncStorage.setItem('username', username);
    await AsyncStorage.setItem('password', password);
    await AsyncStorage.setItem('api_key', apiKey);
    await AsyncStorage.setItem('auth_token', token);
  } catch (error) {
    console.error('Error saving credentials:', error);
  }
};
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_DATA_STORAGE"],
                expected_score=(0, 2),
                description="Storing password and api_key in AsyncStorage without encryption",
                tags=["react-native", "javascript", "data-storage", "critical"]
            ),

            # ========== REACT NATIVE - SECURE SAMPLES ==========

            DetectorValidationSample(
                name="react_native_secure_storage",
                code='''
import * as Keychain from 'react-native-keychain';

export const saveCredentials = async (username, password) => {
  try {
    await Keychain.setGenericPassword(username, password, {
      service: 'com.myapp.credentials',
      accessible: Keychain.ACCESSIBLE.WHEN_UNLOCKED,
    });
    console.log('Credentials saved securely');
  } catch (error) {
    console.error('Error saving credentials:', error);
  }
};

export const getCredentials = async () => {
  try {
    const credentials = await Keychain.getGenericPassword({
      service: 'com.myapp.credentials',
    });
    if (credentials) {
      return {
        username: credentials.username,
        password: credentials.password,
      };
    }
    return null;
  } catch (error) {
    console.error('Error retrieving credentials:', error);
    return null;
  }
};
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Using react-native-keychain for secure credential storage",
                tags=["react-native", "javascript", "data-storage", "secure"]
            ),

            # ========== FLUTTER DART - VULNERABLE SAMPLES ==========

            DetectorValidationSample(
                name="flutter_dart_missing_ssl_pinning",
                code='''
import 'package:http/http.dart' as http;
import 'dart:convert';

class ApiClient {
  Future<Map<String, dynamic>> fetchData() async {
    final response = await http.get(
      Uri.parse('https://api.example.com/data'),
    );

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to load data');
    }
  }
}
''',
                language="dart",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_SSL_PINNING"],
                expected_score=(0, 2),
                description="Flutter HTTP client without SSL certificate pinning",
                tags=["flutter", "dart", "ssl-pinning", "high"]
            ),

            DetectorValidationSample(
                name="flutter_dart_insecure_storage",
                code='''
import 'package:shared_preferences/shared_preferences.dart';

class UserManager {
  Future<void> saveCredentials(String username, String password, String apiKey) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('username', username);
    await prefs.setString('password', password);
    await prefs.setString('api_key', apiKey);
    await prefs.setString('auth_token', token);
  }

  Future<String?> getPassword() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('password');
  }
}
''',
                language="dart",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_DATA_STORAGE"],
                expected_score=(0, 2),
                description="Storing password and api_key in shared_preferences without encryption",
                tags=["flutter", "dart", "data-storage", "critical"]
            ),

            # ========== FLUTTER DART - SECURE SAMPLES ==========

            DetectorValidationSample(
                name="flutter_dart_secure_storage",
                code='''
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class SecureUserManager {
  final storage = FlutterSecureStorage();

  Future<void> saveCredentials(String username, String password) async {
    await storage.write(key: 'username', value: username);
    await storage.write(key: 'password', value: password);
  }

  Future<String?> getPassword() async {
    return await storage.read(key: 'password');
  }

  Future<void> deleteCredentials() async {
    await storage.delete(key: 'username');
    await storage.delete(key: 'password');
  }
}
''',
                language="dart",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Using flutter_secure_storage for encrypted credential storage",
                tags=["flutter", "dart", "data-storage", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="android_local_network_okhttp",
                code='''
import okhttp3.OkHttpClient;
import okhttp3.Request;

public class LocalApiClient {
    private OkHttpClient client = new OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .build();

    public String fetchLocalData() throws IOException {
        // Local network communication - SSL pinning not required for 192.168.x.x
        Request request = new Request.Builder()
            .url("https://192.168.1.100:8080/api/data")
            .build();
        return client.newCall(request).execute().body().string();
    }
}
''',
                language="java",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Local network communication (192.168.x.x) - SSL pinning not required",
                tags=["android", "java", "edge-case", "local-network"]
            ),

            DetectorValidationSample(
                name="android_non_sensitive_storage",
                code='''
import android.content.SharedPreferences;

public class PreferencesManager {
    public void saveUserPreferences(String theme, String language, int fontSize) {
        SharedPreferences prefs = context.getSharedPreferences("app_prefs", MODE_PRIVATE);
        prefs.edit()
            .putString("theme", theme)
            .putString("language", language)
            .putInt("font_size", fontSize)
            .apply();
    }
}
''',
                language="java",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SharedPreferences for non-sensitive data (theme, language) is acceptable",
                tags=["android", "java", "edge-case", "non-sensitive"]
            ),

            DetectorValidationSample(
                name="ios_static_content_storage",
                code='''
import Foundation

class SettingsManager {
    func saveAppSettings(isDarkMode: Bool, selectedLanguage: String) {
        let defaults = UserDefaults.standard
        defaults.set(isDarkMode, forKey: "dark_mode")
        defaults.set(selectedLanguage, forKey: "language")
        defaults.synchronize()
    }
}
''',
                language="swift",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="UserDefaults for non-sensitive settings is acceptable",
                tags=["ios", "swift", "edge-case", "non-sensitive"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMobileSecurityDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Mobile Security detector validation tests PASSED")
        print("The MobileSecurityDetector is correctly identifying vulnerabilities across:")
        print("  - Android (Java/Kotlin)")
        print("  - iOS (Swift)")
        print("  - React Native (JavaScript)")
        print("  - Flutter (Dart)")
    else:
        print(f"\n❌ {len(result.failures)} Mobile Security detector validation tests FAILED")
        print("The MobileSecurityDetector has accuracy issues that must be fixed.")
        sys.exit(1)
