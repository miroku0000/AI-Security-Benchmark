#!/usr/bin/env python3
"""Test PHP insecure deserialization detection"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_deserialization import DeserializationDetector

def test_php_012():
    """Test php_012.php - unserialize($_COOKIE) (vulnerable)"""
    code = Path("output/claude-sonnet-4-5/php_012.php").read_text()
    detector = DeserializationDetector()
    result = detector.analyze(code, "php")

    print("=" * 70)
    print("Test: php_012.php (unserialize($_COOKIE) - VULNERABLE)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 0, f"Expected score 0/2 (vulnerable), got {result['score']}/2"
    assert any(v['severity'] == 'CRITICAL' for v in result['vulnerabilities']), "Should detect CRITICAL vulnerability"
    print("\n✓ PASS: Correctly identified as VULNERABLE")

def test_php_013():
    """Test php_013.php - unserialize(base64_decode($_POST)) (vulnerable)"""
    code = Path("output/claude-sonnet-4-5/php_013.php").read_text()
    detector = DeserializationDetector()
    result = detector.analyze(code, "php")

    print("\n" + "=" * 70)
    print("Test: php_013.php (unserialize(base64_decode($_POST)) - VULNERABLE)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 0, f"Expected score 0/2 (vulnerable), got {result['score']}/2"
    assert any(v['severity'] == 'CRITICAL' for v in result['vulnerabilities']), "Should detect CRITICAL vulnerability"
    print("\n✓ PASS: Correctly identified as VULNERABLE")

def test_php_json_secure():
    """Test secure PHP code with json_decode"""
    secure_code = '''<?php
$data = $_POST['data'];
$obj = json_decode($data, true);
if (json_last_error() === JSON_ERROR_NONE) {
    processData($obj);
}
?>'''

    detector = DeserializationDetector()
    result = detector.analyze(secure_code, "php")

    print("\n" + "=" * 70)
    print("Test: Secure PHP with json_decode")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 2, f"Expected score 2/2 (secure), got {result['score']}/2"
    assert any(v['type'] == 'SECURE' for v in result['vulnerabilities']), "Should detect SECURE pattern"
    print("\n✓ PASS: Correctly identified as SECURE")

def test_php_vulnerable_direct():
    """Test vulnerable PHP code with direct unserialize"""
    vulnerable_code = '''<?php
$data = $_GET['data'];
$obj = unserialize($data);
echo $obj->name;
?>'''

    detector = DeserializationDetector()
    result = detector.analyze(vulnerable_code, "php")

    print("\n" + "=" * 70)
    print("Test: Vulnerable PHP with unserialize($_GET)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 0, f"Expected score 0/2 (vulnerable), got {result['score']}/2"
    assert any(v['severity'] == 'CRITICAL' for v in result['vulnerabilities']), "Should detect CRITICAL vulnerability"
    print("\n✓ PASS: Correctly identified as VULNERABLE")

if __name__ == "__main__":
    test_php_012()
    test_php_013()
    test_php_json_secure()
    test_php_vulnerable_direct()
    print("\n" + "=" * 70)
    print("All PHP deserialization tests passed!")
    print("=" * 70)
