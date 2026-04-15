#!/usr/bin/env python3
"""
Php Xxe Detector Validation Tests

This module validates that the XXEDetector correctly identifies
security vulnerabilities in PHP code.
"""

import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_xxe import XXEDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestPhpXxeDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for XXEDetector (PHP)."""

    def get_detector(self):
        """Return XXEDetector instance."""
        return XXEDetector()

    def get_samples(self):
        """Return PHP security test samples for XXEDetector."""
        # PHP uses existing multi-language detectors
        # These samples test the PHP language support
        return [
            DetectorValidationSample(
                name="php_xxe_simplexml_load_string",
                code='''<?php
function parse_xml($xml_data) {
    $xml = simplexml_load_string($_POST['xml']);
    return $xml;
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["XXE"],
                expected_score=(0, 2),
                description="PHP simplexml_load_string without entity protection (CRITICAL)",
                tags=["php", "simplexml", "xxe", "critical"]
            ),
            DetectorValidationSample(
                name="php_xxe_domdocument_loadxml",
                code='''<?php
function process_xml($xml_string) {
    $dom = new DOMDocument();
    $dom->loadXML($_POST['data']);
    return $dom->getElementsByTagName('item');
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["XXE"],
                expected_score=(0, 2),
                description="PHP DOMDocument loadXML without protection (CRITICAL)",
                tags=["php", "domdocument", "xxe", "critical"]
            ),
            DetectorValidationSample(
                name="php_xxe_simplexml_load_file",
                code='''<?php
function load_config($filename) {
    $xml_file = $_GET['config'];
    $config = simplexml_load_file($xml_file);
    return $config;
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["XXE"],
                expected_score=(0, 2),
                description="PHP simplexml_load_file with user input (CRITICAL)",
                tags=["php", "simplexml", "xxe", "critical"]
            ),
            DetectorValidationSample(
                name="php_safe_libxml_disable_entities",
                code='''<?php
function parse_xml($xml_data) {
    libxml_disable_entity_loader(true);
    $previous_value = libxml_use_internal_errors(true);

    $xml = simplexml_load_string($_POST['xml'], 'SimpleXMLElement', LIBXML_NOENT | LIBXML_DTDLOAD);

    libxml_use_internal_errors($previous_value);
    return $xml;
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP simplexml with libxml_disable_entity_loader (SECURE)",
                tags=["php", "simplexml", "libxml", "secure"]
            ),
            DetectorValidationSample(
                name="php_safe_domdocument_no_entities",
                code='''<?php
function process_xml($xml_string) {
    $dom = new DOMDocument();

    // Disable external entity loading
    libxml_disable_entity_loader(true);
    $dom->substituteEntities = false;

    $dom->loadXML($_POST['data'], LIBXML_NOENT | LIBXML_DTDLOAD | LIBXML_NONET);

    return $dom->getElementsByTagName('item');
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP DOMDocument with entity protection (SECURE)",
                tags=["php", "domdocument", "secure"]
            ),
            DetectorValidationSample(
                name="php_safe_json_instead_of_xml",
                code='''<?php
function load_config($config_data) {
    // Use JSON instead of XML to avoid XXE
    $config = json_decode($_POST['config'], true);

    if (json_last_error() !== JSON_ERROR_NONE) {
        throw new Exception('Invalid JSON data');
    }

    return $config;
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP using JSON instead of XML (SECURE)",
                tags=["php", "json", "secure"]
            )
        ]


if __name__ == '__main__':
    import unittest

    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhpXxeDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\n✅ All Php Xxe detector validation tests PASSED")
    else:
        print(f"\n❌ {len(result.failures)} tests FAILED")
        sys.exit(1)
