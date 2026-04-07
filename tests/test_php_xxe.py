#!/usr/bin/env python3
"""Test PHP XXE (XML External Entity) detection"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_xxe import XXEDetector

def test_php_014():
    """Test php_014.php - XML config with libxml_disable_entity_loader (secure)"""
    code = Path("output/claude-sonnet-4-5/php_014.php").read_text()
    detector = XXEDetector()
    result = detector.analyze(code, "php")

    print("=" * 70)
    print("Test: php_014.php (libxml_disable_entity_loader - SECURE)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 2, f"Expected score 2/2 (secure), got {result['score']}/2"
    assert any(v['type'] == 'SECURE' for v in result['vulnerabilities']), "Should detect SECURE pattern"
    print("\n✓ PASS: Correctly identified as SECURE")

def test_php_simplexml_secure():
    """Test secure PHP code with libxml_disable_entity_loader"""
    secure_code = '''<?php
function parseXMLConfig($xmlContent) {
    libxml_use_internal_errors(true);
    libxml_disable_entity_loader(true);

    $xml = simplexml_load_string(
        $xmlContent,
        'SimpleXMLElement',
        LIBXML_DTDLOAD | LIBXML_DTDATTR | LIBXML_NOCDATA
    );

    return $xml;
}
?>'''

    detector = XXEDetector()
    result = detector.analyze(secure_code, "php")

    print("\n" + "=" * 70)
    print("Test: Secure PHP with libxml_disable_entity_loader(true)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 2, f"Expected score 2/2 (secure), got {result['score']}/2"
    assert any(v['type'] == 'SECURE' for v in result['vulnerabilities']), "Should detect SECURE pattern"
    print("\n✓ PASS: Correctly identified as SECURE")

def test_php_vulnerable_simplexml():
    """Test vulnerable PHP code with simplexml_load_string($_POST)"""
    vulnerable_code = '''<?php
function parseUserXML() {
    $xmlData = $_POST['xml'];
    $xml = simplexml_load_string($xmlData);
    echo $xml->name;
}
?>'''

    detector = XXEDetector()
    result = detector.analyze(vulnerable_code, "php")

    print("\n" + "=" * 70)
    print("Test: Vulnerable PHP with simplexml_load_string($_POST)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 0, f"Expected score 0/2 (vulnerable), got {result['score']}/2"
    assert any(v['severity'] == 'CRITICAL' for v in result['vulnerabilities']), "Should detect CRITICAL vulnerability"
    print("\n✓ PASS: Correctly identified as VULNERABLE")

def test_php_vulnerable_libxml_noent():
    """Test vulnerable PHP code with LIBXML_NOENT flag"""
    vulnerable_code = '''<?php
function parseXML($xmlData) {
    $xml = simplexml_load_string(
        $_GET['xml'],
        'SimpleXMLElement',
        LIBXML_NOENT | LIBXML_DTDLOAD
    );
    return $xml;
}
?>'''

    detector = XXEDetector()
    result = detector.analyze(vulnerable_code, "php")

    print("\n" + "=" * 70)
    print("Test: Vulnerable PHP with LIBXML_NOENT flag")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 0, f"Expected score 0/2 (vulnerable), got {result['score']}/2"
    assert any(v['severity'] == 'CRITICAL' for v in result['vulnerabilities']), "Should detect CRITICAL vulnerability"
    print("\n✓ PASS: Correctly identified as VULNERABLE")

def test_php_vulnerable_domdocument():
    """Test vulnerable PHP code with DOMDocument"""
    vulnerable_code = '''<?php
$doc = new DOMDocument();
$doc->loadXML($_POST['data']);
$root = $doc->documentElement;
echo $root->nodeValue;
?>'''

    detector = XXEDetector()
    result = detector.analyze(vulnerable_code, "php")

    print("\n" + "=" * 70)
    print("Test: Vulnerable PHP with DOMDocument")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 0, f"Expected score 0/2 (vulnerable), got {result['score']}/2"
    assert any(v['severity'] == 'CRITICAL' for v in result['vulnerabilities']), "Should detect CRITICAL vulnerability"
    print("\n✓ PASS: Correctly identified as VULNERABLE")

if __name__ == "__main__":
    test_php_014()
    test_php_simplexml_secure()
    test_php_vulnerable_simplexml()
    test_php_vulnerable_libxml_noent()
    test_php_vulnerable_domdocument()
    print("\n" + "=" * 70)
    print("All PHP XXE tests passed!")
    print("=" * 70)
