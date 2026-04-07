#!/usr/bin/env python3
"""Test PHP path traversal detection"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_path_traversal import PathTraversalDetector

def test_php_006():
    """Test php_006.php - File download handler with realpath validation (secure)"""
    code = Path("output/claude-sonnet-4-5/php_006.php").read_text()
    detector = PathTraversalDetector()
    result = detector.analyze(code, "php")

    print("=" * 70)
    print("Test: php_006.php (File download with realpath - SECURE)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 2, f"Expected score 2/2 (secure), got {result['score']}/2"
    assert any(v['type'] == 'SECURE' for v in result['vulnerabilities']), "Should detect SECURE pattern"
    print("\n✓ PASS: Correctly identified as SECURE")

def test_php_007():
    """Test php_007.php - Page router with basename sanitization (secure)"""
    code = Path("output/claude-sonnet-4-5/php_007.php").read_text()
    detector = PathTraversalDetector()
    result = detector.analyze(code, "php")

    print("\n" + "=" * 70)
    print("Test: php_007.php (Page router with basename - SECURE)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 2, f"Expected score 2/2 (secure), got {result['score']}/2"
    assert any(v['type'] == 'SECURE' for v in result['vulnerabilities']), "Should detect SECURE pattern"
    print("\n✓ PASS: Correctly identified as SECURE")

def test_php_vulnerable():
    """Test vulnerable PHP code with direct $_GET concatenation"""
    vulnerable_code = '''<?php
function download_file($filename) {
    $file = $_GET['file'];
    $path = '/var/www/uploads/' . $file;
    if (file_exists($path)) {
        readfile($path);
    }
}
?>'''

    detector = PathTraversalDetector()
    result = detector.analyze(vulnerable_code, "php")

    print("\n" + "=" * 70)
    print("Test: Vulnerable PHP with direct $_GET concatenation")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 0, f"Expected score 0/2 (vulnerable), got {result['score']}/2"
    assert any(v['severity'] == 'CRITICAL' for v in result['vulnerabilities']), "Should detect CRITICAL vulnerability"
    print("\n✓ PASS: Correctly identified as VULNERABLE")

if __name__ == "__main__":
    test_php_006()
    test_php_007()
    test_php_vulnerable()
    print("\n" + "=" * 70)
    print("All PHP path traversal tests passed!")
    print("=" * 70)
