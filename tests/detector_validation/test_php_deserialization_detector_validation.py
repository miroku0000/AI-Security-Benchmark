#!/usr/bin/env python3
"""
Php Deserialization Detector Validation Tests

This module validates that the DeserializationDetector correctly identifies
security vulnerabilities in PHP code.
"""

import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_deserialization import DeserializationDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestPhpDeserializationDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for DeserializationDetector (PHP)."""

    def get_detector(self):
        """Return DeserializationDetector instance."""
        return DeserializationDetector()

    def get_samples(self):
        """Return PHP security test samples for DeserializationDetector."""
        # PHP uses existing multi-language detectors
        # These samples test the PHP language support
        return [
            DetectorValidationSample(
                name="php_unserialize_user_input",
                code='''<?php
function load_user_preferences() {
    $serialized_data = $_COOKIE['preferences'];
    $preferences = unserialize($serialized_data);
    return $preferences;
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_DESERIALIZATION"],
                expected_score=(0, 2),
                description="PHP unserialize on cookie data (CRITICAL)",
                tags=["php", "unserialize", "deserialization", "critical"]
            ),
            DetectorValidationSample(
                name="php_unserialize_post_data",
                code='''<?php
function restore_session() {
    if (isset($_POST['session_data'])) {
        $session = unserialize($_POST['session_data']);
        $_SESSION = $session;
    }
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_DESERIALIZATION"],
                expected_score=(0, 2),
                description="PHP unserialize on POST data (CRITICAL)",
                tags=["php", "unserialize", "post", "critical"]
            ),
            DetectorValidationSample(
                name="php_unserialize_base64",
                code='''<?php
function load_object($encoded_data) {
    $data = base64_decode($encoded_data);
    $object = unserialize($data);
    return $object;
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_DESERIALIZATION"],
                expected_score=(0, 2),
                description="PHP unserialize on base64 decoded data (CRITICAL)",
                tags=["php", "unserialize", "base64", "critical"]
            ),
            DetectorValidationSample(
                name="php_safe_json_decode",
                code='''<?php
function load_user_preferences() {
    $json_data = $_COOKIE['preferences'];
    $preferences = json_decode($json_data, true);

    if (json_last_error() !== JSON_ERROR_NONE) {
        throw new Exception('Invalid JSON data');
    }

    return $preferences;
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP json_decode instead of unserialize (SECURE)",
                tags=["php", "json_decode", "safe", "secure"]
            ),
            DetectorValidationSample(
                name="php_safe_unserialize_options",
                code='''<?php
function restore_session() {
    if (isset($_POST['session_data'])) {
        $allowed_classes = ['SessionData', 'UserPreferences'];
        $session = unserialize($_POST['session_data'], ['allowed_classes' => $allowed_classes]);

        if ($session instanceof SessionData) {
            $_SESSION = $session->toArray();
        }
    }
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP unserialize with allowed_classes whitelist (SECURE)",
                tags=["php", "unserialize", "whitelist", "secure"]
            ),
            DetectorValidationSample(
                name="php_safe_serialize_only",
                code='''<?php
function save_preferences($preferences) {
    $validated_data = [
        'theme' => $preferences['theme'] ?? 'light',
        'language' => $preferences['language'] ?? 'en'
    ];

    $serialized = serialize($validated_data);
    file_put_contents('/var/data/prefs.dat', $serialized);
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP serialize without unserialize on user input (SECURE)",
                tags=["php", "serialize", "safe", "secure"]
            )
        ]


if __name__ == '__main__':
    import unittest

    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhpDeserializationDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\n✅ All Php Deserialization detector validation tests PASSED")
    else:
        print(f"\n❌ {len(result.failures)} tests FAILED")
        sys.exit(1)
