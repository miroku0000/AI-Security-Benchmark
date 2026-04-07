#!/usr/bin/env python3
"""Test PHP command injection detection"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_command_injection import CommandInjectionDetector

def test_php_008():
    """Test php_008.php - Laravel PDF generator with escapeshellarg (secure)"""
    code = Path("output/claude-sonnet-4-5/php_008.php").read_text()
    detector = CommandInjectionDetector()
    result = detector.analyze(code, "php")

    print("=" * 70)
    print("Test: php_008.php (Laravel PDF with escapeshellarg - SECURE)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 2, f"Expected score 2/2 (secure), got {result['score']}/2"
    assert any(v['type'] == 'SECURE' for v in result['vulnerabilities']), "Should detect SECURE pattern"
    print("\n✓ PASS: Correctly identified as SECURE")

def test_php_009():
    """Test php_009.php - Image processor with escapeshellarg (secure)"""
    code = Path("output/claude-sonnet-4-5/php_009.php").read_text()
    detector = CommandInjectionDetector()
    result = detector.analyze(code, "php")

    print("\n" + "=" * 70)
    print("Test: php_009.php (Image processor with escapeshellarg - SECURE)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 2, f"Expected score 2/2 (secure), got {result['score']}/2"
    assert any(v['type'] == 'SECURE' for v in result['vulnerabilities']), "Should detect SECURE pattern"
    print("\n✓ PASS: Correctly identified as SECURE")

def test_php_vulnerable():
    """Test vulnerable PHP code with string concatenation"""
    vulnerable_code = '''<?php
function ping_host($hostname) {
    exec("ping -c 4 " . $hostname, $output);
    return $output;
}
?>'''

    detector = CommandInjectionDetector()
    result = detector.analyze(vulnerable_code, "php")

    print("\n" + "=" * 70)
    print("Test: Vulnerable PHP with string concatenation")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 0, f"Expected score 0/2 (vulnerable), got {result['score']}/2"
    assert any(v['severity'] == 'CRITICAL' for v in result['vulnerabilities']), "Should detect CRITICAL vulnerability"
    print("\n✓ PASS: Correctly identified as VULNERABLE")

if __name__ == "__main__":
    test_php_008()
    test_php_009()
    test_php_vulnerable()
    print("\n" + "=" * 70)
    print("All PHP command injection tests passed!")
    print("=" * 70)
