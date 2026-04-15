#!/usr/bin/env python3
"""
Php Access Control Detector Validation Tests

This module validates that the AccessControlDetector correctly identifies
security vulnerabilities in PHP code.
"""

import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_access_control import AccessControlDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestPhpAccessControlDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for AccessControlDetector (PHP)."""

    def get_detector(self):
        """Return AccessControlDetector instance."""
        return AccessControlDetector()

    def get_samples(self):
        """Return PHP security test samples for AccessControlDetector."""
        # PHP uses existing multi-language detectors
        # These samples test the PHP language support
        return [
            DetectorValidationSample(
                name="php_missing_access_control_admin",
                code='''<?php
function delete_user($user_id) {
    // No access control check
    $conn = get_db_connection();
    $stmt = $conn->prepare("DELETE FROM users WHERE id = ?");
    $stmt->bind_param("i", $user_id);
    $stmt->execute();
    return true;
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ACCESS_CONTROL"],
                expected_score=(0, 2),
                description="PHP admin function without access control (CRITICAL)",
                tags=["php", "access_control", "missing_authz", "critical"]
            ),
            DetectorValidationSample(
                name="php_missing_role_check",
                code='''<?php
function update_salary($employee_id, $new_salary) {
    // Missing role validation
    $conn = get_db_connection();
    $query = "UPDATE employees SET salary = $new_salary WHERE id = $employee_id";
    mysqli_query($conn, $query);
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ACCESS_CONTROL"],
                expected_score=(0, 2),
                description="PHP salary update without role check (CRITICAL)",
                tags=["php", "access_control", "missing_role", "critical"]
            ),
            DetectorValidationSample(
                name="php_proper_session_check",
                code='''<?php
function delete_user($user_id) {
    session_start();
    if (!isset($_SESSION['user_role']) || $_SESSION['user_role'] !== 'admin') {
        die('Access denied: Admin privileges required');
    }

    $conn = get_db_connection();
    $stmt = $conn->prepare("DELETE FROM users WHERE id = ?");
    $stmt->bind_param("i", $user_id);
    $stmt->execute();
    return true;
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP function with proper session-based access control (SECURE)",
                tags=["php", "access_control", "session", "secure"]
            ),
            DetectorValidationSample(
                name="php_role_based_access_control",
                code='''<?php
function update_salary($employee_id, $new_salary) {
    session_start();
    $allowed_roles = ['admin', 'hr_manager'];

    if (!isset($_SESSION['user_role']) || !in_array($_SESSION['user_role'], $allowed_roles)) {
        throw new Exception('Unauthorized: Insufficient privileges');
    }

    $conn = get_db_connection();
    $stmt = $conn->prepare("UPDATE employees SET salary = ? WHERE id = ?");
    $stmt->bind_param("di", $new_salary, $employee_id);
    $stmt->execute();
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP function with role-based access control (SECURE)",
                tags=["php", "access_control", "rbac", "secure"]
            ),
            DetectorValidationSample(
                name="php_ownership_check",
                code='''<?php
function edit_profile($user_id, $data) {
    session_start();

    // Verify user can only edit their own profile
    if (!isset($_SESSION['user_id']) || $_SESSION['user_id'] != $user_id) {
        die('Access denied: Can only edit your own profile');
    }

    $conn = get_db_connection();
    $stmt = $conn->prepare("UPDATE users SET name = ?, email = ? WHERE id = ?");
    $stmt->bind_param("ssi", $data['name'], $data['email'], $user_id);
    $stmt->execute();
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP function with ownership verification (SECURE)",
                tags=["php", "access_control", "ownership", "secure"]
            )
        ]


if __name__ == '__main__':
    import unittest

    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhpAccessControlDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\n✅ All Php Access Control detector validation tests PASSED")
    else:
        print(f"\n❌ {len(result.failures)} tests FAILED")
        sys.exit(1)
