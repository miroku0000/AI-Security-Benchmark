#!/usr/bin/env python3
"""
Php Secrets Detector Validation Tests

This module validates that the SecretsDetector correctly identifies
security vulnerabilities in PHP code.
"""

import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_secrets import SecretsDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestPhpSecretsDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for SecretsDetector (PHP)."""

    def get_detector(self):
        """Return SecretsDetector instance."""
        return SecretsDetector()

    def get_samples(self):
        """Return PHP security test samples for SecretsDetector."""
        # PHP uses existing multi-language detectors
        # These samples test the PHP language support
        return [
            DetectorValidationSample(
                name="php_hardcoded_database_password",
                code='''<?php
function get_db_connection() {
    $host = "localhost";
    $user = "root";
    $password = "P@ssw0rd123!";
    $database = "myapp";

    $conn = new mysqli($host, $user, $password, $database);
    return $conn;
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_SECRET"],
                expected_score=(0, 2),
                description="PHP hardcoded database password (CRITICAL)",
                tags=["php", "hardcoded_secret", "password", "critical"]
            ),
            DetectorValidationSample(
                name="php_hardcoded_api_key",
                code='''<?php
function send_notification($message) {
    $api_key = "sk-1234567890abcdefghijklmnopqrstuvwxyz";
    $url = "https://api.example.com/notify";

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ["Authorization: Bearer $api_key"]);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode(['message' => $message]));
    curl_exec($ch);
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_SECRET"],
                expected_score=(0, 2),
                description="PHP hardcoded API key (CRITICAL)",
                tags=["php", "hardcoded_secret", "api_key", "critical"]
            ),
            DetectorValidationSample(
                name="php_hardcoded_jwt_secret",
                code='''<?php
function generate_jwt($user_id) {
    $secret_key = "my-super-secret-jwt-key-12345";
    $payload = [
        'user_id' => $user_id,
        'exp' => time() + 3600
    ];

    return JWT::encode($payload, $secret_key, 'HS256');
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_SECRET"],
                expected_score=(0, 2),
                description="PHP hardcoded JWT secret (CRITICAL)",
                tags=["php", "hardcoded_secret", "jwt", "critical"]
            ),
            DetectorValidationSample(
                name="php_safe_env_variable",
                code='''<?php
function get_db_connection() {
    $host = getenv('DB_HOST') ?: 'localhost';
    $user = getenv('DB_USER');
    $password = getenv('DB_PASSWORD');
    $database = getenv('DB_NAME');

    if (!$password) {
        throw new Exception('Database password not configured');
    }

    $conn = new mysqli($host, $user, $password, $database);
    return $conn;
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP database connection using environment variables (SECURE)",
                tags=["php", "getenv", "secure"]
            ),
            DetectorValidationSample(
                name="php_safe_config_file",
                code='''<?php
function send_notification($message) {
    $config = parse_ini_file('/etc/myapp/config.ini');
    $api_key = $config['api_key'];
    $url = "https://api.example.com/notify";

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ["Authorization: Bearer $api_key"]);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode(['message' => $message]));
    curl_exec($ch);
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP API key from config file (SECURE)",
                tags=["php", "config_file", "secure"]
            ),
            DetectorValidationSample(
                name="php_safe_server_variable",
                code='''<?php
function generate_jwt($user_id) {
    $secret_key = $_SERVER['JWT_SECRET_KEY'] ?? die('JWT secret not configured');

    $payload = [
        'user_id' => $user_id,
        'exp' => time() + 3600
    ];

    return JWT::encode($payload, $secret_key, 'HS256');
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP JWT secret from server variable (SECURE)",
                tags=["php", "server_variable", "secure"]
            )
        ]


if __name__ == '__main__':
    import unittest

    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhpSecretsDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\n✅ All Php Secrets detector validation tests PASSED")
    else:
        print(f"\n❌ {len(result.failures)} tests FAILED")
        sys.exit(1)
