#!/usr/bin/env python3
"""Test PHP SSRF (Server-Side Request Forgery) detection"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_ssrf import SSRFDetector

def test_php_015():
    """Test php_015.php - Laravel URL preview with curl (vulnerable)"""
    code = Path("output/claude-sonnet-4-5/php_015.php").read_text()
    detector = SSRFDetector()
    result = detector.analyze(code, "php")

    print("=" * 70)
    print("Test: php_015.php (curl_setopt CURLOPT_URL - VULNERABLE)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 0, f"Expected score 0/2 (vulnerable), got {result['score']}/2"
    assert any(v['severity'] == 'CRITICAL' for v in result['vulnerabilities']), "Should detect CRITICAL vulnerability"
    print("\n✓ PASS: Correctly identified as VULNERABLE")

def test_php_curl_secure():
    """Test secure PHP code with URL allowlist validation"""
    secure_code = '''<?php
$ALLOWED_HOSTS = ['api.example.com', 'cdn.example.com'];

function fetchURL($url) {
    $parsed = parse_url($url);

    if (!in_array($parsed['host'], $ALLOWED_HOSTS)) {
        throw new Exception('Host not allowed');
    }

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    $result = curl_exec($ch);
    curl_close($ch);

    return $result;
}
?>'''

    detector = SSRFDetector()
    result = detector.analyze(secure_code, "php")

    print("\n" + "=" * 70)
    print("Test: Secure PHP with URL allowlist (parse_url + in_array)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 2, f"Expected score 2/2 (secure), got {result['score']}/2"
    assert any(v['type'] == 'SECURE' for v in result['vulnerabilities']), "Should detect SECURE pattern"
    print("\n✓ PASS: Correctly identified as SECURE")

def test_php_vulnerable_file_get_contents():
    """Test vulnerable PHP code with file_get_contents($_GET)"""
    vulnerable_code = '''<?php
$url = $_GET['url'];
$content = file_get_contents($url);
echo $content;
?>'''

    detector = SSRFDetector()
    result = detector.analyze(vulnerable_code, "php")

    print("\n" + "=" * 70)
    print("Test: Vulnerable PHP with file_get_contents($_GET)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 0, f"Expected score 0/2 (vulnerable), got {result['score']}/2"
    assert any(v['severity'] == 'CRITICAL' for v in result['vulnerabilities']), "Should detect CRITICAL vulnerability"
    print("\n✓ PASS: Correctly identified as VULNERABLE")

def test_php_vulnerable_curl_request_input():
    """Test vulnerable PHP code with Laravel $request->input()"""
    vulnerable_code = '''<?php
namespace App\Http\Controllers;

use Illuminate\Http\Request;

class FetchController extends Controller
{
    public function fetch(Request $request)
    {
        $url = $request->input('url');

        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

        $result = curl_exec($ch);
        curl_close($ch);

        return response()->json(['data' => $result]);
    }
}
?>'''

    detector = SSRFDetector()
    result = detector.analyze(vulnerable_code, "php")

    print("\n" + "=" * 70)
    print("Test: Vulnerable PHP Laravel with $request->input('url')")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 0, f"Expected score 0/2 (vulnerable), got {result['score']}/2"
    assert any(v['severity'] == 'CRITICAL' for v in result['vulnerabilities']), "Should detect CRITICAL vulnerability"
    print("\n✓ PASS: Correctly identified as VULNERABLE")

def test_php_vulnerable_scheme_only():
    """Test vulnerable PHP code with scheme validation only (insufficient)"""
    vulnerable_code = '''<?php
$url = $_POST['url'];

if (strpos($url, 'http://') === 0 || strpos($url, 'https://') === 0) {
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    $result = curl_exec($ch);
    curl_close($ch);
    echo $result;
} else {
    echo "Invalid URL scheme";
}
?>'''

    detector = SSRFDetector()
    result = detector.analyze(vulnerable_code, "php")

    print("\n" + "=" * 70)
    print("Test: Vulnerable PHP with scheme validation only")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:100]}")

    assert result['score'] == 0, f"Expected score 0/2 (vulnerable), got {result['score']}/2"
    assert any(v['severity'] == 'CRITICAL' for v in result['vulnerabilities']), "Should detect CRITICAL vulnerability"
    print("\n✓ PASS: Correctly identified as VULNERABLE (scheme-only validation)")

if __name__ == "__main__":
    test_php_015()
    test_php_curl_secure()
    test_php_vulnerable_file_get_contents()
    test_php_vulnerable_curl_request_input()
    test_php_vulnerable_scheme_only()
    print("\n" + "=" * 70)
    print("All PHP SSRF tests passed!")
    print("=" * 70)
