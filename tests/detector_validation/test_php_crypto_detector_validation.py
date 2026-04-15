#!/usr/bin/env python3
"""
Php Crypto Detector Validation Tests

This module validates that the CryptoDetector correctly identifies
security vulnerabilities in PHP code.
"""

import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_crypto import CryptoDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestPhpCryptoDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for CryptoDetector (PHP)."""

    def get_detector(self):
        """Return CryptoDetector instance."""
        return CryptoDetector()

    def get_samples(self):
        """Return PHP security test samples for CryptoDetector."""
        # PHP uses existing multi-language detectors
        # These samples test the PHP language support
        return [
            DetectorValidationSample(
                name="php_weak_hash_md5",
                code='''<?php
function hash_password($password) {
    $hashed = md5($password);
    return $hashed;
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["WEAK_HASHING"],
                expected_score=(0, 2),
                description="PHP MD5 for password hashing (CRITICAL)",
                tags=["php", "md5", "weak_crypto", "critical"]
            ),
            DetectorValidationSample(
                name="php_weak_hash_sha1",
                code='''<?php
function store_user($username, $password) {
    $password_hash = sha1($password);
    $query = "INSERT INTO users (username, password) VALUES ('$username', '$password_hash')";
    mysqli_query($conn, $query);
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["WEAK_HASHING"],
                expected_score=(0, 2),
                description="PHP SHA1 for password hashing (CRITICAL)",
                tags=["php", "sha1", "weak_crypto", "critical"]
            ),
            DetectorValidationSample(
                name="php_deprecated_mcrypt",
                code='''<?php
function encrypt_data($data, $key) {
    $iv = mcrypt_create_iv(mcrypt_get_iv_size(MCRYPT_RIJNDAEL_128, MCRYPT_MODE_CBC), MCRYPT_RAND);
    $encrypted = mcrypt_encrypt(MCRYPT_RIJNDAEL_128, $key, $data, MCRYPT_MODE_CBC, $iv);
    return base64_encode($iv . $encrypted);
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["DEPRECATED_CRYPTO"],
                expected_score=(0, 2),
                description="PHP deprecated mcrypt extension (CRITICAL)",
                tags=["php", "mcrypt", "deprecated", "critical"]
            ),
            DetectorValidationSample(
                name="php_secure_password_hash",
                code='''<?php
function hash_password($password) {
    $options = ['cost' => 12];
    $hashed = password_hash($password, PASSWORD_BCRYPT, $options);
    return $hashed;
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP password_hash with bcrypt (SECURE)",
                tags=["php", "password_hash", "bcrypt", "secure"]
            ),
            DetectorValidationSample(
                name="php_secure_openssl_encrypt",
                code='''<?php
function encrypt_data($data, $key) {
    $cipher = "aes-256-gcm";
    $iv = openssl_random_pseudo_bytes(openssl_cipher_iv_length($cipher));
    $tag = null;

    $encrypted = openssl_encrypt($data, $cipher, $key, OPENSSL_RAW_DATA, $iv, $tag);
    return base64_encode($iv . $tag . $encrypted);
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP OpenSSL with AES-256-GCM (SECURE)",
                tags=["php", "openssl", "aes", "secure"]
            ),
            DetectorValidationSample(
                name="php_secure_argon2",
                code='''<?php
function store_user($username, $password) {
    $password_hash = password_hash($password, PASSWORD_ARGON2ID);

    $stmt = $conn->prepare("INSERT INTO users (username, password) VALUES (?, ?)");
    $stmt->bind_param("ss", $username, $password_hash);
    $stmt->execute();
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP password_hash with Argon2id (SECURE)",
                tags=["php", "password_hash", "argon2", "secure"]
            )
        ]


if __name__ == '__main__':
    import unittest

    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhpCryptoDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\n✅ All Php Crypto detector validation tests PASSED")
    else:
        print(f"\n❌ {len(result.failures)} tests FAILED")
        sys.exit(1)
