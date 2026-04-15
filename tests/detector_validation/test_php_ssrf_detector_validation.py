#!/usr/bin/env python3
"""
Php Ssrf Detector Validation Tests

This module validates that the SSRFDetector correctly identifies
security vulnerabilities in PHP code.
"""

import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_ssrf import SSRFDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestPhpSsrfDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for SSRFDetector (PHP)."""

    def get_detector(self):
        """Return SSRFDetector instance."""
        return SSRFDetector()

    def get_samples(self):
        """Return PHP security test samples for SSRFDetector."""
        # PHP uses existing multi-language detectors
        # These samples test the PHP language support
        return [
            DetectorValidationSample(
                name="php_ssrf_file_get_contents",
                code='''<?php
function fetch_url($url) {
    $content = file_get_contents($_GET['url']);
    return $content;
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SSRF"],
                expected_score=(0, 2),
                description="PHP file_get_contents with user URL (CRITICAL)",
                tags=["php", "file_get_contents", "ssrf", "critical"]
            ),
            DetectorValidationSample(
                name="php_ssrf_curl_exec",
                code='''<?php
function proxy_request($target_url) {
    $ch = curl_init($_POST['url']);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    $result = curl_exec($ch);
    curl_close($ch);
    return $result;
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SSRF"],
                expected_score=(0, 2),
                description="PHP curl_exec with POST URL (CRITICAL)",
                tags=["php", "curl", "ssrf", "critical"]
            ),
            DetectorValidationSample(
                name="php_ssrf_fopen_url",
                code='''<?php
function load_remote_data($endpoint) {
    $url = "http://api.example.com/" . $_GET['endpoint'];
    $handle = fopen($url, "r");

    if ($handle) {
        $content = stream_get_contents($handle);
        fclose($handle);
        return $content;
    }
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SSRF"],
                expected_score=(0, 2),
                description="PHP fopen with user-controlled URL path (CRITICAL)",
                tags=["php", "fopen", "ssrf", "critical"]
            ),
            DetectorValidationSample(
                name="php_safe_url_whitelist",
                code='''<?php
function fetch_url($url) {
    $allowed_domains = ['api.example.com', 'cdn.example.com'];

    $parsed = parse_url($_GET['url']);
    if (!$parsed || !isset($parsed['host']) || !in_array($parsed['host'], $allowed_domains)) {
        throw new Exception('Invalid or unauthorized URL');
    }

    $content = file_get_contents($_GET['url']);
    return $content;
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP file_get_contents with domain whitelist (SECURE)",
                tags=["php", "file_get_contents", "whitelist", "secure"]
            ),
            DetectorValidationSample(
                name="php_safe_filter_var_validation",
                code='''<?php
function proxy_request($target_url) {
    $url = $_POST['url'];

    if (!filter_var($url, FILTER_VALIDATE_URL)) {
        die('Invalid URL format');
    }

    $parsed = parse_url($url);
    $allowed_hosts = ['api.example.com', 'data.example.com'];

    if (!in_array($parsed['host'], $allowed_hosts, true)) {
        die('URL host not allowed');
    }

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    $result = curl_exec($ch);
    curl_close($ch);
    return $result;
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP curl with filter_var and whitelist (SECURE)",
                tags=["php", "curl", "filter_var", "secure"]
            ),
            DetectorValidationSample(
                name="php_safe_predefined_endpoints",
                code='''<?php
function load_remote_data($endpoint) {
    $endpoints = [
        'users' => 'http://api.example.com/users',
        'posts' => 'http://api.example.com/posts',
        'comments' => 'http://api.example.com/comments'
    ];

    $endpoint_key = $_GET['endpoint'];
    if (!isset($endpoints[$endpoint_key])) {
        throw new Exception('Invalid endpoint');
    }

    $url = $endpoints[$endpoint_key];
    $handle = fopen($url, "r");
    if ($handle) {
        $content = stream_get_contents($handle);
        fclose($handle);
        return $content;
    }
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP fopen with predefined endpoint mapping (SECURE)",
                tags=["php", "fopen", "predefined", "secure"]
            )
        ]


if __name__ == '__main__':
    import unittest

    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhpSsrfDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\n✅ All Php Ssrf detector validation tests PASSED")
    else:
        print(f"\n❌ {len(result.failures)} tests FAILED")
        sys.exit(1)
