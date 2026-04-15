#!/usr/bin/env python3
"""
Php Path Traversal Detector Validation Tests

This module validates that the PathTraversalDetector correctly identifies
security vulnerabilities in PHP code.
"""

import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_path_traversal import PathTraversalDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestPhpPathTraversalDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for PathTraversalDetector (PHP)."""

    def get_detector(self):
        """Return PathTraversalDetector instance."""
        return PathTraversalDetector()

    def get_samples(self):
        """Return PHP security test samples for PathTraversalDetector."""
        # PHP uses existing multi-language detectors
        # These samples test the PHP language support
        return [
            DetectorValidationSample(
                name="php_path_traversal_file_get_contents",
                code='''<?php
function read_file($filename) {
    $content = file_get_contents("/var/www/uploads/" . $filename);
    return $content;
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["PATH_TRAVERSAL"],
                expected_score=(0, 2),
                description="PHP file_get_contents with unsanitized input (CRITICAL)",
                tags=["php", "file_get_contents", "path_traversal", "critical"]
            ),
            DetectorValidationSample(
                name="php_path_traversal_fopen",
                code='''<?php
function display_log($log_file) {
    $path = $_GET['file'];
    $handle = fopen("/var/logs/" . $path, "r");

    if ($handle) {
        $content = fread($handle, filesize("/var/logs/" . $path));
        fclose($handle);
        return $content;
    }
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["PATH_TRAVERSAL"],
                expected_score=(0, 2),
                description="PHP fopen with GET parameter (CRITICAL)",
                tags=["php", "fopen", "path_traversal", "critical"]
            ),
            DetectorValidationSample(
                name="php_path_traversal_include",
                code='''<?php
function load_template($template_name) {
    include("/var/www/templates/" . $template_name . ".php");
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["PATH_TRAVERSAL"],
                expected_score=(0, 2),
                description="PHP include with user-controlled path (CRITICAL)",
                tags=["php", "include", "path_traversal", "critical"]
            ),
            DetectorValidationSample(
                name="php_safe_basename_validation",
                code='''<?php
function read_file($filename) {
    $safe_filename = basename($filename);
    $full_path = "/var/www/uploads/" . $safe_filename;

    if (!file_exists($full_path)) {
        throw new Exception('File not found');
    }

    $content = file_get_contents($full_path);
    return $content;
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP file_get_contents with basename sanitization (SECURE)",
                tags=["php", "file_get_contents", "basename", "secure"]
            ),
            DetectorValidationSample(
                name="php_safe_realpath_validation",
                code='''<?php
function display_log($log_file) {
    $base_dir = "/var/logs/";
    $requested_path = $base_dir . $_GET['file'];

    $real_path = realpath($requested_path);

    if ($real_path === false || strpos($real_path, $base_dir) !== 0) {
        die('Access denied: Invalid file path');
    }

    $handle = fopen($real_path, "r");
    if ($handle) {
        $content = fread($handle, filesize($real_path));
        fclose($handle);
        return $content;
    }
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP fopen with realpath validation (SECURE)",
                tags=["php", "fopen", "realpath", "secure"]
            ),
            DetectorValidationSample(
                name="php_safe_whitelist_validation",
                code='''<?php
function load_template($template_name) {
    $allowed_templates = ['header', 'footer', 'sidebar', 'content'];

    if (!in_array($template_name, $allowed_templates, true)) {
        throw new Exception('Invalid template name');
    }

    include("/var/www/templates/" . $template_name . ".php");
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP include with whitelist validation (SECURE)",
                tags=["php", "include", "whitelist", "secure"]
            )
        ]


if __name__ == '__main__':
    import unittest

    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhpPathTraversalDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\n✅ All Php Path Traversal detector validation tests PASSED")
    else:
        print(f"\n❌ {len(result.failures)} tests FAILED")
        sys.exit(1)
