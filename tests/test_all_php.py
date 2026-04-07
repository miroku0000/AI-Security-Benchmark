#!/usr/bin/env python3
"""Comprehensive test to verify all 20 PHP files can be analyzed"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_sql_injection import SQLInjectionDetector
from tests.test_xss import XSSDetector
from tests.test_command_injection import CommandInjectionDetector
from tests.test_path_traversal import PathTraversalDetector
from tests.test_secrets import SecretsDetector
from tests.test_deserialization import DeserializationDetector
from tests.test_xxe import XXEDetector
from tests.test_ssrf import SSRFDetector
from tests.test_crypto import CryptoDetector
from tests.test_file_upload import FileUploadDetector
from tests.test_access_control import AccessControlDetector
from tests.test_csrf import CSRFDetector

def test_all_php_files():
    """Test that all 20 PHP files can be analyzed by their respective detectors"""

    base_path = Path("output/claude-sonnet-4-5")

    # Map files to their detectors
    test_cases = [
        # SQL Injection (3 files)
        ("php_001.php", SQLInjectionDetector, "php", "SQL Injection - Raw query"),
        ("php_002.php", SQLInjectionDetector, "php", "SQL Injection - String interpolation"),
        ("php_003.php", SQLInjectionDetector, "php", "SQL Injection - PDO vulnerable"),

        # XSS (2 files)
        ("php_004.php", XSSDetector, "php", "XSS - Echo user input"),
        ("php_005.php", XSSDetector, "php", "XSS - Template injection"),

        # Path Traversal (2 files)
        ("php_006.php", PathTraversalDetector, "php", "Path Traversal - File include"),
        ("php_007.php", PathTraversalDetector, "php", "Path Traversal - File read"),

        # Command Injection (2 files)
        ("php_008.php", CommandInjectionDetector, "php", "Command Injection - exec()"),
        ("php_009.php", CommandInjectionDetector, "php", "Command Injection - shell_exec()"),

        # Hardcoded Secrets (2 files)
        ("php_010.php", SecretsDetector, "php", "Hardcoded Secrets - Database password"),
        ("php_011.php", SecretsDetector, "php", "Hardcoded Secrets - API key"),

        # Insecure Deserialization (2 files)
        ("php_012.php", DeserializationDetector, "php", "Deserialization - unserialize()"),
        ("php_013.php", DeserializationDetector, "php", "Deserialization - Cookie data"),

        # XXE (1 file)
        ("php_014.php", XXEDetector, "php", "XXE - SimpleXML"),

        # SSRF (1 file)
        ("php_015.php", SSRFDetector, "php", "SSRF - file_get_contents()"),

        # Weak Crypto (2 files)
        ("php_016.php", CryptoDetector, "php", "Weak Crypto - MD5"),
        ("php_017.php", CryptoDetector, "php", "Weak Crypto - Weak password hash"),

        # File Upload (1 file)
        ("php_018.php", FileUploadDetector, "php", "File Upload - WordPress plugin"),

        # Access Control (1 file)
        ("php_019.php", AccessControlDetector, "php", "Access Control - Laravel mass assignment"),

        # CSRF (1 file)
        ("php_020.php", CSRFDetector, "php", "CSRF - Admin panel"),
    ]

    print("=" * 80)
    print("COMPREHENSIVE PHP DETECTOR TEST - All 20 Files")
    print("=" * 80)

    passed = 0
    failed = 0

    for filename, detector_class, language, description in test_cases:
        file_path = base_path / filename

        try:
            # Read file
            code = file_path.read_text()

            # Create detector instance
            detector = detector_class()

            # Analyze code
            result = detector.analyze(code, language)

            # Verify result has required fields
            assert "score" in result, f"{filename}: Missing 'score' in result"
            assert "vulnerabilities" in result, f"{filename}: Missing 'vulnerabilities' in result"
            assert "max_score" in result, f"{filename}: Missing 'max_score' in result"
            assert isinstance(result["score"], int), f"{filename}: Score must be an integer"
            assert isinstance(result["vulnerabilities"], list), f"{filename}: Vulnerabilities must be a list"

            # Get vulnerability type
            vuln_types = [v.get("type", "UNKNOWN") for v in result["vulnerabilities"]]
            vuln_severities = [v.get("severity", "UNKNOWN") for v in result["vulnerabilities"]]

            status = "✓ PASS" if result["score"] >= 0 else "✗ FAIL"
            print(f"{status} | {filename:15} | {description:40} | Score: {result['score']}/{result['max_score']} | {', '.join(set(vuln_severities[:3]))}")

            passed += 1

        except Exception as e:
            print(f"✗ FAIL | {filename:15} | {description:40} | ERROR: {str(e)[:50]}")
            failed += 1

    print("=" * 80)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {len(test_cases)} total tests")
    print("=" * 80)

    if failed > 0:
        print("\n❌ SOME TESTS FAILED")
        sys.exit(1)
    else:
        print("\n✅ ALL 20 PHP FILES SUCCESSFULLY ANALYZED!")
        return True

if __name__ == "__main__":
    test_all_php_files()
