#!/usr/bin/env python3
"""
Format String Detector Validation Tests

This module validates that the FormatStringDetector correctly identifies
format string vulnerabilities in C/C++ code.

Test Coverage:
- printf(variable) - variable as format string (CRITICAL)
- fprintf/sprintf/snprintf with variable format strings (CRITICAL)
- Secure patterns: printf("%s", variable) with string literals
- Edge cases: Non-C/C++ languages, no printf functions
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_format_string import FormatStringDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestFormatStringDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Format String Detector."""

    def get_detector(self):
        """Return FormatStringDetector instance."""
        return FormatStringDetector()

    def get_samples(self):
        """Return hand-crafted format string test samples."""
        return [
            # ========== VULNERABLE - printf with variable ==========

            DetectorValidationSample(
                name="format_string_printf_variable",
                code='''
void display_message(char *user_input) {
    printf(user_input);  // Variable as format string
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["FORMAT_STRING"],
                expected_score=(0, 2),
                description="printf with variable format string (CRITICAL)",
                tags=["cpp", "printf", "critical"]
            ),

            # ========== VULNERABLE - fprintf with variable ==========

            DetectorValidationSample(
                name="format_string_fprintf_variable",
                code='''
void log_message(FILE *logfile, char *message) {
    fprintf(logfile, message);  // Variable as format string
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["FORMAT_STRING"],
                expected_score=(0, 2),
                description="fprintf with variable format string (CRITICAL)",
                tags=["cpp", "fprintf", "critical"]
            ),

            # ========== VULNERABLE - sprintf with variable ==========

            DetectorValidationSample(
                name="format_string_sprintf_variable",
                code='''
void format_output(char *buffer, char *template) {
    sprintf(buffer, template);  // Variable as format string
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["FORMAT_STRING"],
                expected_score=(0, 2),
                description="sprintf with variable format string (CRITICAL)",
                tags=["cpp", "sprintf", "critical"]
            ),

            # ========== VULNERABLE - snprintf with variable ==========

            DetectorValidationSample(
                name="format_string_snprintf_variable",
                code='''
void safe_format(char *buffer, size_t size, char *format) {
    snprintf(buffer, size, format);  // Variable as format string
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["FORMAT_STRING"],
                expected_score=(0, 2),
                description="snprintf with variable format string (CRITICAL)",
                tags=["cpp", "snprintf", "critical"]
            ),

            # ========== SECURE - printf with string literal ==========

            DetectorValidationSample(
                name="format_string_printf_literal",
                code='''
void display_message(char *user_input) {
    printf("%s", user_input);  // String literal as format
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="printf with string literal format (SECURE)",
                tags=["cpp", "printf", "secure"]
            ),

            # ========== SECURE - fprintf with string literal ==========

            DetectorValidationSample(
                name="format_string_fprintf_literal",
                code='''
void log_message(FILE *logfile, char *message) {
    fprintf(logfile, "Log: %s\\n", message);  // String literal
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="fprintf with string literal format (SECURE)",
                tags=["cpp", "fprintf", "secure"]
            ),

            # ========== SECURE - sprintf with string literal ==========

            DetectorValidationSample(
                name="format_string_sprintf_literal",
                code='''
void format_output(char *buffer, char *data) {
    sprintf(buffer, "Result: %s", data);  // String literal
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="sprintf with string literal format (SECURE)",
                tags=["cpp", "sprintf", "secure"]
            ),

            # ========== SECURE - snprintf with string literal ==========

            DetectorValidationSample(
                name="format_string_snprintf_literal",
                code='''
void safe_format(char *buffer, size_t size, char *data) {
    snprintf(buffer, size, "Data: %s", data);  // String literal
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="snprintf with string literal format (SECURE)",
                tags=["cpp", "snprintf", "secure"]
            ),

            # ========== SECURE - Multiple printf calls ==========

            DetectorValidationSample(
                name="format_string_multiple_secure",
                code='''
void display_info(char *name, int age) {
    printf("Name: %s\\n", name);
    printf("Age: %d\\n", age);
    fprintf(stderr, "Info displayed\\n");
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Multiple printf calls with string literals (SECURE)",
                tags=["cpp", "multiple", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="format_string_no_printf",
                code='''
void process_data(char *data) {
    int len = strlen(data);
    strcpy(buffer, data);
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="No printf functions (no risk)",
                tags=["cpp", "no_printf", "secure"]
            ),

            DetectorValidationSample(
                name="format_string_non_cpp_language",
                code='''
def display_message(message):
    print(message)
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Non-C/C++ language (out of scope)",
                tags=["python", "edge_case", "secure"]
            ),

            DetectorValidationSample(
                name="format_string_constant_only",
                code='''
void show_banner() {
    printf("=== Application Started ===\\n");
    printf("Version 1.0\\n");
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Printf with constant strings only (SECURE)",
                tags=["cpp", "constant", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFormatStringDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Format String detector validation tests PASSED")
        print("The FormatStringDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Format String detector validation tests FAILED")
        print("The FormatStringDetector has accuracy issues that must be fixed.")
        sys.exit(1)
