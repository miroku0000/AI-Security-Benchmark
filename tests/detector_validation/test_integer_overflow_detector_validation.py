#!/usr/bin/env python3
"""
Integer Overflow Detector Validation Tests

This module validates that the IntegerOverflowDetector correctly identifies
integer overflow vulnerabilities in Rust and C/C++ code.

Test Coverage:
- Rust: Unchecked multiply/add operations (HIGH)
- Rust: Checked arithmetic with checked_mul/checked_add (SECURE)
- C/C++: Arithmetic without bounds checking (HIGH)
- C/C++: Bounds checking with INT_MAX/SIZE_MAX comparisons (SECURE)
- Edge cases: No arithmetic operations, other languages
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_integer_overflow import IntegerOverflowDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestIntegerOverflowDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Integer Overflow Detector."""

    def get_detector(self):
        """Return IntegerOverflowDetector instance."""
        return IntegerOverflowDetector()

    def get_samples(self):
        """Return hand-crafted integer overflow test samples."""
        return [
            # ========== VULNERABLE - Rust unchecked multiply ==========

            DetectorValidationSample(
                name="integer_overflow_rust_multiply",
                code='''
fn calculate_area(width: u32, height: u32) -> u32 {
    let area = width * height;  // No overflow check
    area
}
''',
                language="rust",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INTEGER_OVERFLOW"],
                expected_score=(0, 2),
                description="Rust multiply without overflow check (HIGH)",
                tags=["rust", "multiply", "high"]
            ),

            DetectorValidationSample(
                name="integer_overflow_rust_add",
                code='''
fn increment_counter(value: u32, increment: u32) -> u32 {
    let result = value + increment;  // No overflow check
    result
}
''',
                language="rust",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INTEGER_OVERFLOW"],
                expected_score=(0, 2),
                description="Rust addition without overflow check (HIGH)",
                tags=["rust", "add", "high"]
            ),

            # ========== SECURE - Rust checked arithmetic ==========

            DetectorValidationSample(
                name="integer_overflow_rust_checked_mul",
                code='''
fn calculate_area(width: u32, height: u32) -> Option<u32> {
    width.checked_mul(height)  // Safe with checked_mul
}
''',
                language="rust",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Rust checked_mul prevents overflow (SECURE)",
                tags=["rust", "checked_mul", "secure"]
            ),

            DetectorValidationSample(
                name="integer_overflow_rust_checked_add",
                code='''
fn increment_counter(value: u32, increment: u32) -> Option<u32> {
    value.checked_add(increment)  // Safe with checked_add
}
''',
                language="rust",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Rust checked_add prevents overflow (SECURE)",
                tags=["rust", "checked_add", "secure"]
            ),

            DetectorValidationSample(
                name="integer_overflow_rust_saturating_mul",
                code='''
fn calculate_area(width: u32, height: u32) -> u32 {
    width.saturating_mul(height)  // Safe with saturating_mul
}
''',
                language="rust",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Rust saturating_mul prevents overflow (SECURE)",
                tags=["rust", "saturating_mul", "secure"]
            ),

            # ========== VULNERABLE - C/C++ unchecked multiply ==========

            DetectorValidationSample(
                name="integer_overflow_cpp_multiply",
                code='''
int calculate_size(int width, int height) {
    int size = width * height;  // No overflow check
    return size;
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INTEGER_OVERFLOW"],
                expected_score=(0, 2),
                description="C++ multiply without bounds check (HIGH)",
                tags=["cpp", "multiply", "high"]
            ),

            DetectorValidationSample(
                name="integer_overflow_cpp_malloc",
                code='''
void allocate_buffer(int width, int height) {
    char *buffer = malloc(width * height);  // Multiply in malloc without check
    process_buffer(buffer);
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INTEGER_OVERFLOW"],
                expected_score=(0, 2),
                description="malloc with multiply without bounds check (HIGH)",
                tags=["cpp", "malloc", "high"]
            ),

            # ========== SECURE - C/C++ with bounds checking ==========

            DetectorValidationSample(
                name="integer_overflow_cpp_int_max_check",
                code='''
int calculate_size(int width, int height) {
    if (width > INT_MAX / height) {
        return -1;  // Overflow would occur
    }
    int size = width * height;
    return size;
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="INT_MAX bounds check prevents overflow (SECURE)",
                tags=["cpp", "int_max", "secure"]
            ),

            DetectorValidationSample(
                name="integer_overflow_cpp_size_max_check",
                code='''
void allocate_buffer(size_t width, size_t height) {
    if (width > SIZE_MAX / height) {
        return;  // Overflow would occur
    }
    char *buffer = malloc(width * height);
    process_buffer(buffer);
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="SIZE_MAX bounds check prevents overflow (SECURE)",
                tags=["cpp", "size_max", "secure"]
            ),

            DetectorValidationSample(
                name="integer_overflow_cpp_uint_max_check",
                code='''
unsigned int calculate_size(unsigned int width, unsigned int height) {
    if (width > UINT_MAX / height) {
        return 0;  // Overflow would occur
    }
    unsigned int size = width * height;
    return size;
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="UINT_MAX bounds check prevents overflow (SECURE)",
                tags=["cpp", "uint_max", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="integer_overflow_no_arithmetic",
                code='''
int get_constant() {
    return 42;
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="No arithmetic operations (no risk)",
                tags=["cpp", "no_arithmetic", "secure"]
            ),

            DetectorValidationSample(
                name="integer_overflow_python_language",
                code='''
def calculate_area(width, height):
    return width * height
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Python has arbitrary precision (out of scope)",
                tags=["python", "edge_case", "secure"]
            ),

            DetectorValidationSample(
                name="integer_overflow_rust_no_arithmetic",
                code='''
fn get_constant() -> u32 {
    42
}
''',
                language="rust",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Rust no arithmetic operations (no risk)",
                tags=["rust", "no_arithmetic", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestIntegerOverflowDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Integer Overflow detector validation tests PASSED")
        print("The IntegerOverflowDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Integer Overflow detector validation tests FAILED")
        print("The IntegerOverflowDetector has accuracy issues that must be fixed.")
        sys.exit(1)
