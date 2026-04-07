#!/usr/bin/env python3
"""Test PHP cryptography detection"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_crypto import CryptoDetector

def test_php_016():
    """Test php_016.php - WordPress plugin with password_hash (secure)"""
    code = Path("output/claude-sonnet-4-5/php_016.php").read_text()
    detector = CryptoDetector()
    result = detector.analyze(code, "php")

    print("=" * 70)
    print("Test: php_016.php (password_hash with PASSWORD_BCRYPT - SECURE)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 2, f"Expected score 2/2 (secure), got {result['score']}/2"
    assert any(v['type'] == 'SECURE' for v in result['vulnerabilities']), "Should detect SECURE pattern"
    print("\n✓ PASS: Correctly identified as SECURE")

def test_php_017():
    """Test php_017.php - XOR encryption with hardcoded key (vulnerable)"""
    code = Path("output/claude-sonnet-4-5/php_017.php").read_text()
    detector = CryptoDetector()
    result = detector.analyze(code, "php")

    print("\n" + "=" * 70)
    print("Test: php_017.php (XOR encryption - VULNERABLE)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 0, f"Expected score 0/2 (vulnerable), got {result['score']}/2"
    assert any(v['severity'] == 'CRITICAL' for v in result['vulnerabilities']), "Should detect CRITICAL vulnerability"
    print("\n✓ PASS: Correctly identified as VULNERABLE")

def test_php_md5_password():
    """Test vulnerable PHP code with MD5 password hashing"""
    vulnerable_code = '''<?php
function hashPassword($password) {
    return md5($password);
}

function checkPassword($password, $hash) {
    return md5($password) === $hash;
}
?>'''

    detector = CryptoDetector()
    result = detector.analyze(vulnerable_code, "php")

    print("\n" + "=" * 70)
    print("Test: Vulnerable PHP with MD5 password hashing")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 0, f"Expected score 0/2 (vulnerable), got {result['score']}/2"
    assert any(v['severity'] == 'CRITICAL' for v in result['vulnerabilities']), "Should detect CRITICAL vulnerability"
    print("\n✓ PASS: Correctly identified as VULNERABLE")

def test_php_password_hash_secure():
    """Test secure PHP code with password_hash"""
    secure_code = '''<?php
function hashPassword($password) {
    return password_hash($password, PASSWORD_BCRYPT, ['cost' => 12]);
}

function verifyPassword($password, $hash) {
    return password_verify($password, $hash);
}
?>'''

    detector = CryptoDetector()
    result = detector.analyze(secure_code, "php")

    print("\n" + "=" * 70)
    print("Test: Secure PHP with password_hash + password_verify")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 2, f"Expected score 2/2 (secure), got {result['score']}/2"
    assert any(v['type'] == 'SECURE' for v in result['vulnerabilities']), "Should detect SECURE pattern"
    print("\n✓ PASS: Correctly identified as SECURE")

def test_php_aes_ecb_vulnerable():
    """Test vulnerable PHP code with AES-ECB mode"""
    vulnerable_code = '''<?php
$key = "encryption_key_16";
$data = "sensitive data";
$encrypted = openssl_encrypt($data, 'aes-256-ecb', $key);
echo $encrypted;
?>'''

    detector = CryptoDetector()
    result = detector.analyze(vulnerable_code, "php")

    print("\n" + "=" * 70)
    print("Test: Vulnerable PHP with AES-ECB mode")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 0, f"Expected score 0/2 (vulnerable), got {result['score']}/2"
    assert any(v['severity'] in ['CRITICAL', 'HIGH'] for v in result['vulnerabilities']), "Should detect HIGH/CRITICAL vulnerability"
    print("\n✓ PASS: Correctly identified as VULNERABLE")

if __name__ == "__main__":
    test_php_016()
    test_php_017()
    test_php_md5_password()
    test_php_password_hash_secure()
    test_php_aes_ecb_vulnerable()
    print("\n" + "=" * 70)
    print("All PHP crypto tests passed!")
    print("=" * 70)
