#!/usr/bin/env python3
"""
Php Csrf Detector Validation Tests

This module validates that the CSRFDetector correctly identifies
security vulnerabilities in PHP code.
"""

import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_csrf import CSRFDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestPhpCsrfDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for CSRFDetector (PHP)."""

    def get_detector(self):
        """Return CSRFDetector instance."""
        return CSRFDetector()

    def get_samples(self):
        """Return PHP security test samples for CSRFDetector."""
        # PHP uses existing multi-language detectors
        # These samples test the PHP language support
        return [
            DetectorValidationSample(
                name="php_csrf_no_token_validation",
                code='''<?php
function update_profile() {
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $name = $_POST['name'];
        $email = $_POST['email'];

        $stmt = $conn->prepare("UPDATE users SET name=?, email=? WHERE id=?");
        $stmt->bind_param("ssi", $name, $email, $_SESSION['user_id']);
        $stmt->execute();
    }
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CSRF"],
                expected_score=(0, 2),
                description="PHP POST handler without CSRF token (CRITICAL)",
                tags=["php", "csrf", "no_token", "critical"]
            ),
            DetectorValidationSample(
                name="php_csrf_delete_action",
                code='''<?php
function delete_account() {
    $user_id = $_POST['user_id'];

    $conn = get_db_connection();
    $query = "DELETE FROM users WHERE id = $user_id";
    mysqli_query($conn, $query);

    echo "Account deleted successfully";
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CSRF"],
                expected_score=(0, 2),
                description="PHP delete action without CSRF protection (CRITICAL)",
                tags=["php", "csrf", "delete", "critical"]
            ),
            DetectorValidationSample(
                name="php_csrf_get_state_change",
                code='''<?php
function transfer_money() {
    $to_account = $_GET['to'];
    $amount = $_GET['amount'];

    $conn = get_db_connection();
    $stmt = $conn->prepare("INSERT INTO transfers (to_account, amount) VALUES (?, ?)");
    $stmt->bind_param("sd", $to_account, $amount);
    $stmt->execute();
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CSRF"],
                expected_score=(0, 2),
                description="PHP state-changing operation via GET (CRITICAL)",
                tags=["php", "csrf", "get_method", "critical"]
            ),
            DetectorValidationSample(
                name="php_csrf_token_validation",
                code='''<?php
function update_profile() {
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        session_start();

        if (!isset($_POST['csrf_token']) || $_POST['csrf_token'] !== $_SESSION['csrf_token']) {
            die('CSRF token validation failed');
        }

        $name = $_POST['name'];
        $email = $_POST['email'];

        $stmt = $conn->prepare("UPDATE users SET name=?, email=? WHERE id=?");
        $stmt->bind_param("ssi", $name, $email, $_SESSION['user_id']);
        $stmt->execute();
    }
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP POST handler with CSRF token validation (SECURE)",
                tags=["php", "csrf", "token_validation", "secure"]
            ),
            DetectorValidationSample(
                name="php_csrf_hash_equals",
                code='''<?php
function delete_account() {
    session_start();

    if (!isset($_POST['csrf_token']) || !hash_equals($_SESSION['csrf_token'], $_POST['csrf_token'])) {
        http_response_code(403);
        die('Invalid CSRF token');
    }

    $user_id = $_SESSION['user_id'];
    $conn = get_db_connection();
    $stmt = $conn->prepare("DELETE FROM users WHERE id = ?");
    $stmt->bind_param("i", $user_id);
    $stmt->execute();
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP delete with hash_equals CSRF validation (SECURE)",
                tags=["php", "csrf", "hash_equals", "secure"]
            )
        ]


if __name__ == '__main__':
    import unittest

    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhpCsrfDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\n✅ All Php Csrf detector validation tests PASSED")
    else:
        print(f"\n❌ {len(result.failures)} tests FAILED")
        sys.exit(1)
