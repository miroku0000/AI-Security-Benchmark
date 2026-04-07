#!/usr/bin/env python3
"""Test PHP hardcoded secrets detection"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_secrets import SecretsDetector

def test_php_010():
    """Test php_010.php - Laravel Twilio service with config() (secure)"""
    code = Path("output/claude-sonnet-4-5/php_010.php").read_text()
    detector = SecretsDetector()
    result = detector.analyze(code, "php")

    print("=" * 70)
    print("Test: php_010.php (Laravel config() - SECURE)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 2, f"Expected score 2/2 (secure), got {result['score']}/2"
    assert any(v['type'] == 'SECURE' for v in result['vulnerabilities']), "Should detect SECURE pattern"
    print("\n✓ PASS: Correctly identified as SECURE")

def test_php_011():
    """Test php_011.php - Hardcoded database credentials in define() (vulnerable)"""
    code = Path("output/claude-sonnet-4-5/php_011.php").read_text()
    detector = SecretsDetector()
    result = detector.analyze(code, "php")

    print("\n" + "=" * 70)
    print("Test: php_011.php (Hardcoded define() credentials - VULNERABLE)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 0, f"Expected score 0/2 (vulnerable), got {result['score']}/2"
    assert any(v['severity'] == 'CRITICAL' for v in result['vulnerabilities']), "Should detect CRITICAL vulnerability"
    print("\n✓ PASS: Correctly identified as VULNERABLE")

def test_php_config_secure():
    """Test secure PHP code with config()"""
    secure_code = '''<?php
$apiKey = config('services.twilio.api_key');
$secret = env('APP_SECRET');
$password = getenv('DB_PASSWORD');
?>'''

    detector = SecretsDetector()
    result = detector.analyze(secure_code, "php")

    print("\n" + "=" * 70)
    print("Test: Secure PHP with config/env/getenv")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 2, f"Expected score 2/2 (secure), got {result['score']}/2"
    assert any(v['type'] == 'SECURE' for v in result['vulnerabilities']), "Should detect SECURE pattern"
    print("\n✓ PASS: Correctly identified as SECURE")

def test_php_vulnerable_variable():
    """Test vulnerable PHP code with hardcoded variable"""
    vulnerable_code = '''<?php
$apiKey = 'sk-1234567890abcdefghijklmnop';
$password = 'SecurePassword123!';
$dbConfig = [
    'host' => 'localhost',
    'user' => 'admin',
    'pass' => $password
];
?>'''

    detector = SecretsDetector()
    result = detector.analyze(vulnerable_code, "php")

    print("\n" + "=" * 70)
    print("Test: Vulnerable PHP with hardcoded variables")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 0, f"Expected score 0/2 (vulnerable), got {result['score']}/2"
    assert any(v['severity'] == 'CRITICAL' for v in result['vulnerabilities']), "Should detect CRITICAL vulnerability"
    print("\n✓ PASS: Correctly identified as VULNERABLE")

if __name__ == "__main__":
    test_php_010()
    test_php_011()
    test_php_config_secure()
    test_php_vulnerable_variable()
    print("\n" + "=" * 70)
    print("All PHP secrets tests passed!")
    print("=" * 70)
