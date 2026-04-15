#!/usr/bin/env python3
"""
Buffer Overflow Detector Validation Tests

This module validates that the BufferOverflowDetector correctly identifies
buffer overflow vulnerabilities in C/C++ code from unsafe string functions.

Test Coverage:
- Unsafe functions: gets(), strcpy(), strcat(), sprintf(), scanf(%s)
- Safe alternatives: fgets(), strncpy(), strncat(), snprintf()
- Word boundary detection: Ensures fgets() doesn't trigger gets() pattern
- Edge cases: Non-C/C++ languages, no string operations
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_buffer_overflow import BufferOverflowDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestBufferOverflowDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Buffer Overflow Detector."""

    def get_detector(self):
        """Return BufferOverflowDetector instance."""
        return BufferOverflowDetector()

    def get_samples(self):
        """Return hand-crafted buffer overflow test samples."""
        return [
            # ========== VULNERABLE - gets() ==========

            DetectorValidationSample(
                name="buffer_overflow_gets",
                code='''
void read_input() {
    char buffer[100];
    gets(buffer);  // Dangerous - no bounds checking
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["BUFFER_OVERFLOW"],
                expected_score=(0, 2),
                description="gets() without bounds checking (CRITICAL)",
                tags=["cpp", "gets", "critical"]
            ),

            # ========== VULNERABLE - strcpy() ==========

            DetectorValidationSample(
                name="buffer_overflow_strcpy",
                code='''
void copy_string(char *src) {
    char dest[50];
    strcpy(dest, src);  // No bounds checking
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["BUFFER_OVERFLOW"],
                expected_score=(0, 2),
                description="strcpy() without bounds checking (CRITICAL)",
                tags=["cpp", "strcpy", "critical"]
            ),

            # ========== VULNERABLE - strcat() ==========

            DetectorValidationSample(
                name="buffer_overflow_strcat",
                code='''
void append_string(char *buffer, char *input) {
    strcat(buffer, input);  // No bounds checking
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["BUFFER_OVERFLOW"],
                expected_score=(0, 2),
                description="strcat() without bounds checking (CRITICAL)",
                tags=["cpp", "strcat", "critical"]
            ),

            # ========== VULNERABLE - sprintf() ==========

            DetectorValidationSample(
                name="buffer_overflow_sprintf",
                code='''
void format_string(char *user_input) {
    char buffer[100];
    sprintf(buffer, "%s", user_input);  // No bounds checking
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["BUFFER_OVERFLOW"],
                expected_score=(0, 2),
                description="sprintf() without bounds checking (CRITICAL)",
                tags=["cpp", "sprintf", "critical"]
            ),

            # ========== VULNERABLE - scanf(%s) ==========

            DetectorValidationSample(
                name="buffer_overflow_scanf",
                code='''
void read_string() {
    char buffer[100];
    scanf("%s", buffer);  // No width limit
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["BUFFER_OVERFLOW"],
                expected_score=(0, 2),
                description="scanf(%s) without width limit (CRITICAL)",
                tags=["cpp", "scanf", "critical"]
            ),

            # ========== SECURE - fgets() ==========

            DetectorValidationSample(
                name="buffer_overflow_fgets_secure",
                code='''
void read_input() {
    char buffer[100];
    fgets(buffer, sizeof(buffer), stdin);  // Safe with size limit
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="fgets() with size limit (SECURE)",
                tags=["cpp", "fgets", "secure"]
            ),

            # ========== SECURE - strncpy() ==========

            DetectorValidationSample(
                name="buffer_overflow_strncpy_secure",
                code='''
void copy_string(char *src) {
    char dest[50];
    strncpy(dest, src, sizeof(dest));  // Safe with size limit
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="strncpy() with size limit (SECURE)",
                tags=["cpp", "strncpy", "secure"]
            ),

            # ========== SECURE - strncat() ==========

            DetectorValidationSample(
                name="buffer_overflow_strncat_secure",
                code='''
void append_string(char *buffer, char *input) {
    strncat(buffer, input, sizeof(buffer) - strlen(buffer) - 1);  // Safe with size limit
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="strncat() with size limit (SECURE)",
                tags=["cpp", "strncat", "secure"]
            ),

            # ========== SECURE - snprintf() ==========

            DetectorValidationSample(
                name="buffer_overflow_snprintf_secure",
                code='''
void format_string(char *user_input) {
    char buffer[100];
    snprintf(buffer, sizeof(buffer), "%s", user_input);  // Safe with size limit
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="snprintf() with size limit (SECURE)",
                tags=["cpp", "snprintf", "secure"]
            ),

            # ========== WORD BOUNDARY TESTS ==========

            DetectorValidationSample(
                name="buffer_overflow_fgets_not_gets",
                code='''
void read_input() {
    char buffer[100];
    fgets(buffer, sizeof(buffer), stdin);
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="fgets() should NOT match gets() pattern (word boundary test)",
                tags=["cpp", "word_boundary", "fgets"]
            ),

            DetectorValidationSample(
                name="buffer_overflow_strncpy_not_strcpy",
                code='''
void copy_string(char *src) {
    char dest[50];
    strncpy(dest, src, sizeof(dest));
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="strncpy() should NOT match strcpy() pattern (word boundary test)",
                tags=["cpp", "word_boundary", "strncpy"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="buffer_overflow_no_string_operations",
                code='''
void calculate_sum(int *arr, int size) {
    int sum = 0;
    for (int i = 0; i < size; i++) {
        sum += arr[i];
    }
    return sum;
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="No string operations (no risk)",
                tags=["cpp", "no_strings", "secure"]
            ),

            DetectorValidationSample(
                name="buffer_overflow_non_cpp_language",
                code='''
def read_input():
    data = input("Enter data: ")
    return data
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Non-C/C++ language (out of scope)",
                tags=["python", "edge_case", "secure"]
            ),

            # ========== MIXED SAFE FUNCTIONS ==========

            DetectorValidationSample(
                name="buffer_overflow_all_safe_functions",
                code='''
void process_strings(char *src) {
    char buffer[100];
    char dest[50];

    fgets(buffer, sizeof(buffer), stdin);
    strncpy(dest, src, sizeof(dest));
    snprintf(buffer, sizeof(buffer), "%s", src);
    strncat(buffer, src, sizeof(buffer) - strlen(buffer) - 1);
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Multiple safe bounded string functions (SECURE)",
                tags=["cpp", "mixed_safe", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestBufferOverflowDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Buffer Overflow detector validation tests PASSED")
        print("The BufferOverflowDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Buffer Overflow detector validation tests FAILED")
        print("The BufferOverflowDetector has accuracy issues that must be fixed.")
        sys.exit(1)
