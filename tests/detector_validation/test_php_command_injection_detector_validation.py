#!/usr/bin/env python3
"""
Php Command Injection Detector Validation Tests

This module validates that the CommandInjectionDetector correctly identifies
security vulnerabilities in PHP code.
"""

import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_command_injection import CommandInjectionDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestPhpCommandInjectionDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for CommandInjectionDetector (PHP)."""

    def get_detector(self):
        """Return CommandInjectionDetector instance."""
        return CommandInjectionDetector()

    def get_samples(self):
        """Return PHP security test samples for CommandInjectionDetector."""
        # PHP uses existing multi-language detectors
        # These samples test the PHP language support
        return [
            DetectorValidationSample(
                name="php_command_injection_exec",
                code='''<?php
function ping_host($hostname) {
    exec("ping -c 4 " . $hostname, $output);
    return implode("\n", $output);
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["COMMAND_INJECTION"],
                expected_score=(0, 2),
                description="PHP exec with string concatenation (CRITICAL)",
                tags=["php", "exec", "command_injection", "critical"]
            ),
            DetectorValidationSample(
                name="php_command_injection_shell_exec",
                code='''<?php
function backup_database($db_name) {
    $backup_file = "/backups/" . $db_name . ".sql";
    $result = shell_exec("mysqldump -u root -p password $db_name > $backup_file");
    return $result;
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["COMMAND_INJECTION"],
                expected_score=(0, 2),
                description="PHP shell_exec with unvalidated input (CRITICAL)",
                tags=["php", "shell_exec", "command_injection", "critical"]
            ),
            DetectorValidationSample(
                name="php_command_injection_system",
                code='''<?php
function convert_image($filename) {
    $output = $_GET['output'] ?? 'output.png';
    system("convert $filename $output");
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["COMMAND_INJECTION"],
                expected_score=(0, 2),
                description="PHP system call with GET parameter (CRITICAL)",
                tags=["php", "system", "command_injection", "critical"]
            ),
            DetectorValidationSample(
                name="php_safe_escapeshellarg",
                code='''<?php
function ping_host($hostname) {
    $safe_hostname = escapeshellarg($hostname);
    exec("ping -c 4 " . $safe_hostname, $output);
    return implode("\n", $output);
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP exec with escapeshellarg sanitization (SECURE)",
                tags=["php", "exec", "escapeshellarg", "secure"]
            ),
            DetectorValidationSample(
                name="php_safe_whitelist_validation",
                code='''<?php
function convert_image($filename, $format) {
    $allowed_formats = ['png', 'jpg', 'gif', 'webp'];

    if (!in_array($format, $allowed_formats, true)) {
        throw new Exception('Invalid output format');
    }

    $safe_filename = escapeshellarg($filename);
    $output = "output." . $format;
    system("convert " . $safe_filename . " " . $output);
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP system with whitelist and escapeshellarg (SECURE)",
                tags=["php", "system", "whitelist", "secure"]
            ),
            DetectorValidationSample(
                name="php_safe_escapeshellcmd",
                code='''<?php
function backup_database($db_name) {
    $safe_db_name = escapeshellcmd($db_name);
    $backup_file = "/backups/" . $safe_db_name . ".sql";
    $result = shell_exec("mysqldump -u root -p password " . $safe_db_name . " > " . $backup_file);
    return $result;
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP shell_exec with escapeshellcmd (SECURE)",
                tags=["php", "shell_exec", "escapeshellcmd", "secure"]
            )
        ]


if __name__ == '__main__':
    import unittest

    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhpCommandInjectionDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\n✅ All Php Command Injection detector validation tests PASSED")
    else:
        print(f"\n❌ {len(result.failures)} tests FAILED")
        sys.exit(1)
