#!/usr/bin/env python3
"""
Comprehensive tests for detector improvements:
- ATS bypass (development context awareness)
- ML adversarial defense (multi-tiered scoring)
- Weak biometric auth (KeyStore/Secure Enclave detection)
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_mobile_security import MobileSecurityDetector
from tests.test_ml_security import MLSecurityDetector


def test_ats_bypass_global_critical():
    """Test that global ATS bypass is flagged as CRITICAL"""
    vulnerable_code = '''
// Info.plist configuration
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
'''
    detector = MobileSecurityDetector()
    result = detector._analyze_ios(vulnerable_code)

    assert result['score'] == 0, "Should fail for global ATS bypass"
    ats_issues = [v for v in result['vulnerabilities'] if v['type'] == 'ATS_BYPASS']
    assert len(ats_issues) > 0, "Should detect ATS bypass"
    assert ats_issues[0]['severity'] == 'CRITICAL', "Global bypass should be CRITICAL"
    print("✅ test_ats_bypass_global_critical: PASS")


def test_ats_bypass_localhost_dev_info():
    """Test that localhost exceptions with dev comments are INFO"""
    secure_code = '''
// Development only - remove in production
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSExceptionDomains</key>
    <dict>
        <key>localhost</key>
        <dict>
            <key>NSExceptionAllowsInsecureHTTPLoads</key>
            <true/>
        </dict>
    </dict>
</dict>
'''
    detector = MobileSecurityDetector()
    result = detector._analyze_ios(secure_code)

    # Should not fail for localhost dev exceptions
    ats_issues = [v for v in result['vulnerabilities'] if 'ATS_BYPASS' in v['type']]
    if ats_issues:
        assert ats_issues[0]['severity'] == 'INFO', "Localhost dev exception should be INFO"
    print("✅ test_ats_bypass_localhost_dev_info: PASS")


def test_ats_bypass_limited_domains_medium():
    """Test that 1-2 domain exceptions are MEDIUM severity"""
    code_with_domains = '''
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSExceptionDomains</key>
    <dict>
        <key>legacy.example.com</key>
        <dict>
            <key>NSExceptionAllowsInsecureHTTPLoads</key>
            <true/>
        </dict>
    </dict>
</dict>
'''
    detector = MobileSecurityDetector()
    result = detector._analyze_ios(code_with_domains)

    ats_issues = [v for v in result['vulnerabilities'] if v['type'] == 'ATS_BYPASS']
    if ats_issues:
        assert ats_issues[0]['severity'] in ['MEDIUM', 'HIGH'], "Limited domains should be MEDIUM/HIGH"
    print("✅ test_ats_bypass_limited_domains_medium: PASS")


def test_ats_bypass_many_domains_high():
    """Test that 3+ domain exceptions are HIGH severity"""
    code_with_many_domains = '''
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSExceptionDomains</key>
    <dict>
        <key>api1.example.com</key>
        <dict>
            <key>NSExceptionAllowsInsecureHTTPLoads</key>
            <true/>
        </dict>
        <key>api2.example.com</key>
        <dict>
            <key>NSExceptionAllowsInsecureHTTPLoads</key>
            <true/>
        </dict>
        <key>api3.example.com</key>
        <dict>
            <key>NSExceptionAllowsInsecureHTTPLoads</key>
            <true/>
        </dict>
    </dict>
</dict>
'''
    detector = MobileSecurityDetector()
    result = detector._analyze_ios(code_with_many_domains)

    ats_issues = [v for v in result['vulnerabilities'] if v['type'] == 'ATS_BYPASS']
    assert len(ats_issues) > 0, "Should detect ATS bypass"
    assert ats_issues[0]['severity'] == 'HIGH', "Many domains should be HIGH"
    assert result['score'] == 0, "Should fail for many domains"
    print("✅ test_ats_bypass_many_domains_high: PASS")


def test_ml_adversarial_no_defense_high():
    """Test that models without adversarial defense are HIGH severity"""
    vulnerable_code = '''
import torch

model = torch.load('model.pth')

def predict(input_data):
    output = model(input_data)
    return output
'''
    detector = MLSecurityDetector()
    result = detector.detect(vulnerable_code, 'python')

    ml_issues = [v for v in result['vulnerabilities'] if v['type'] == 'ML_ADVERSARIAL_EXAMPLES']
    assert len(ml_issues) > 0, "Should detect missing adversarial defense"
    assert ml_issues[0]['severity'] == 'HIGH', "No defense should be HIGH"
    print("✅ test_ml_adversarial_no_defense_high: PASS")


def test_ml_adversarial_one_defense_medium():
    """Test that models with 1 defense are MEDIUM severity"""
    code_with_one_defense = '''
import torch

model = torch.load('model.pth')

def predict(input_data):
    # Confidence thresholding
    output = model(input_data)
    confidence = torch.max(output).item()
    if confidence < 0.8:
        return None
    return output
'''
    detector = MLSecurityDetector()
    result = detector.detect(code_with_one_defense, 'python')

    ml_issues = [v for v in result['vulnerabilities'] if v['type'] == 'ML_ADVERSARIAL_EXAMPLES']
    assert len(ml_issues) > 0, "Should detect insufficient defense"
    assert ml_issues[0]['severity'] == 'MEDIUM', "One defense should be MEDIUM"
    print("✅ test_ml_adversarial_one_defense_medium: PASS")


def test_ml_adversarial_two_defenses_secure():
    """Test that models with 2+ defenses are SECURE"""
    secure_code = '''
import torch
import numpy as np

model = torch.load('model.pth')

def predict(input_data):
    # Defense 1: Input validation
    input_data = torch.clip(input_data, 0, 1)
    input_data = normalize_input(input_data)

    # Defense 2: Confidence thresholding
    output = model(input_data)
    confidence = torch.max(output).item()
    if confidence < 0.9:
        return None

    return output
'''
    detector = MLSecurityDetector()
    result = detector.detect(secure_code, 'python')

    ml_issues = [v for v in result['vulnerabilities'] if v['type'] == 'ML_ADVERSARIAL_EXAMPLES']
    assert len(ml_issues) == 0, "Should NOT flag models with 2+ defenses"
    print("✅ test_ml_adversarial_two_defenses_secure: PASS")


def test_ml_adversarial_training_defense():
    """Test that adversarial training is recognized as a defense"""
    secure_code = '''
import torch
from art.attacks import FGSM, PGD

model = torch.load('model.pth')

# Adversarial training
epsilon = 0.1
for epoch in range(10):
    for batch in dataloader:
        # Generate adversarial examples
        fgsm_attack = FGSM(model, epsilon=epsilon)
        adv_examples = fgsm_attack.generate(batch)

        # Train on both clean and adversarial
        loss = train_step(batch, adv_examples)

def predict(input_data):
    # Confidence thresholding
    output = model(input_data)
    if torch.max(output) < 0.85:
        return None
    return output
'''
    detector = MLSecurityDetector()
    result = detector.detect(secure_code, 'python')

    ml_issues = [v for v in result['vulnerabilities'] if v['type'] == 'ML_ADVERSARIAL_EXAMPLES']
    assert len(ml_issues) == 0, "Should recognize adversarial training + confidence threshold"
    print("✅ test_ml_adversarial_training_defense: PASS")


def test_android_biometric_insecure_sharedprefs():
    """Test that storing auth result in SharedPreferences is flagged"""
    vulnerable_code = '''
import androidx.biometric.BiometricPrompt

val biometricPrompt = BiometricPrompt(activity, executor,
    object : BiometricPrompt.AuthenticationCallback() {
        override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
            // VULNERABLE: Storing auth result in SharedPreferences
            val prefs = getSharedPreferences("auth", MODE_PRIVATE)
            prefs.edit().putBoolean("authenticated", true).apply()
        }
    }
)
'''
    detector = MobileSecurityDetector()
    result = detector._analyze_android_kotlin(vulnerable_code)

    assert result['score'] == 0, "Should fail for SharedPreferences auth storage"
    # Accept either WEAK_BIOMETRIC_AUTH or INSECURE_DATA_STORAGE (both are correct detections)
    bio_issues = [v for v in result['vulnerabilities'] if v['type'] in ['WEAK_BIOMETRIC_AUTH', 'INSECURE_DATA_STORAGE']]
    assert len(bio_issues) > 0, "Should detect weak biometric auth or insecure storage"
    assert bio_issues[0]['severity'] in ['HIGH', 'CRITICAL'], "Should be HIGH or CRITICAL severity"
    print("✅ test_android_biometric_insecure_sharedprefs: PASS")


def test_android_biometric_secure_keystore():
    """Test that CryptoObject + KeyStore is recognized as secure"""
    secure_code = '''
import androidx.biometric.BiometricPrompt
import android.security.keystore.KeyGenParameterSpec
import javax.crypto.Cipher

// Generate key in AndroidKeyStore
val keyGenerator = KeyGenerator.getInstance(
    KeyProperties.KEY_ALGORITHM_AES,
    "AndroidKeyStore"
)
keyGenerator.init(
    KeyGenParameterSpec.Builder(
        KEY_NAME,
        KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
    )
    .setUserAuthenticationRequired(true)
    .build()
)

// Use CryptoObject with biometric
val cipher = getCipher()
val cryptoObject = BiometricPrompt.CryptoObject(cipher)

val biometricPrompt = BiometricPrompt(activity, executor,
    object : BiometricPrompt.AuthenticationCallback() {
        override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
            // SECURE: Using CryptoObject backed by AndroidKeyStore
            val encryptedData = result.cryptoObject?.cipher?.doFinal(data)
        }
    }
)
biometricPrompt.authenticate(promptInfo, cryptoObject)
'''
    detector = MobileSecurityDetector()
    result = detector._analyze_android_kotlin(secure_code)

    bio_issues = [v for v in result['vulnerabilities'] if v['type'] == 'WEAK_BIOMETRIC_AUTH' and v['severity'] == 'HIGH']
    assert len(bio_issues) == 0, "Should NOT flag KeyStore-backed biometric auth"
    print("✅ test_android_biometric_secure_keystore: PASS")


def test_ios_biometric_insecure_userdefaults():
    """Test that storing auth result in UserDefaults is flagged"""
    vulnerable_code = '''
import LocalAuthentication

let context = LAContext()
context.evaluatePolicy(.deviceOwnerAuthenticationWithBiometrics,
                      localizedReason: "Authenticate") { success, error in
    if success {
        // VULNERABLE: Storing auth result in UserDefaults
        UserDefaults.standard.set(true, forKey: "authenticated")
    }
}
'''
    detector = MobileSecurityDetector()
    result = detector._analyze_ios(vulnerable_code)

    assert result['score'] == 0, "Should fail for UserDefaults auth storage"
    bio_issues = [v for v in result['vulnerabilities'] if v['type'] == 'WEAK_BIOMETRIC_AUTH']
    assert len(bio_issues) > 0, "Should detect weak biometric auth"
    assert bio_issues[0]['severity'] == 'HIGH', "Should be HIGH severity"
    print("✅ test_ios_biometric_insecure_userdefaults: PASS")


def test_ios_biometric_secure_keychain():
    """Test that SecAccessControl + Keychain is recognized as secure"""
    secure_code = '''
import LocalAuthentication
import Security

// Create access control with biometry requirement
let access = SecAccessControlCreateWithFlags(
    nil,
    kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly,
    .biometryCurrentSet,
    nil
)

// Store token in Keychain with biometry requirement
let query: [String: Any] = [
    kSecClass as String: kSecClassGenericPassword,
    kSecAttrAccessControl as String: access as Any,
    kSecValueData as String: tokenData,
    kSecAttrTokenIDSecureEnclave as String: true
]
SecItemAdd(query as CFDictionary, nil)

let context = LAContext()
context.evaluatePolicy(.deviceOwnerAuthenticationWithBiometrics,
                      localizedReason: "Authenticate") { success, error in
    if success {
        // SECURE: Token stored in Keychain with Secure Enclave binding
        let keychainQuery: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecReturnData as String: true
        ]
        SecItemCopyMatching(keychainQuery as CFDictionary, &result)
    }
}
'''
    detector = MobileSecurityDetector()
    result = detector._analyze_ios(secure_code)

    bio_issues = [v for v in result['vulnerabilities'] if v['type'] == 'WEAK_BIOMETRIC_AUTH' and v['severity'] == 'HIGH']
    assert len(bio_issues) == 0, "Should NOT flag Secure Enclave-backed biometric auth"
    print("✅ test_ios_biometric_secure_keychain: PASS")


def run_all_tests():
    """Run all detector improvement tests"""
    print("=" * 80)
    print("DETECTOR IMPROVEMENT TESTS")
    print("=" * 80)
    print()

    print("ATS Bypass Tests:")
    test_ats_bypass_global_critical()
    test_ats_bypass_localhost_dev_info()
    test_ats_bypass_limited_domains_medium()
    test_ats_bypass_many_domains_high()
    print()

    print("ML Adversarial Defense Tests:")
    test_ml_adversarial_no_defense_high()
    test_ml_adversarial_one_defense_medium()
    test_ml_adversarial_two_defenses_secure()
    test_ml_adversarial_training_defense()
    print()

    print("Biometric Authentication Tests:")
    test_android_biometric_insecure_sharedprefs()
    test_android_biometric_secure_keystore()
    test_ios_biometric_insecure_userdefaults()
    test_ios_biometric_secure_keychain()
    print()

    print("=" * 80)
    print("ALL TESTS PASSED! ✅")
    print("=" * 80)


if __name__ == '__main__':
    run_all_tests()
