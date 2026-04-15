#!/usr/bin/env python3
"""
Unsafe Code Detector Validation Tests

This module validates that the UnsafeCodeDetector correctly identifies
unsafe code blocks in Rust.

Test Coverage:
- Rust: unsafe block with raw pointers (MEDIUM)
- Rust: unsafe block with transmute (MEDIUM)
- Rust: unsafe block with FFI (MEDIUM)
- Rust: unsafe block with raw pointer dereference (MEDIUM)
- Rust: safe code without unsafe blocks (SECURE)
- Edge cases: Non-Rust languages
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_unsafe_code import UnsafeCodeDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestUnsafeCodeDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Unsafe Code Detector."""

    def get_detector(self):
        """Return UnsafeCodeDetector instance."""
        return UnsafeCodeDetector()

    def get_samples(self):
        """Return hand-crafted unsafe code test samples."""
        return [
            # ========== VULNERABLE - unsafe with raw pointers ==========

            DetectorValidationSample(
                name="unsafe_code_raw_ptr",
                code='''
fn dangerous_operation() {
    unsafe {
        let ptr: *mut u8 = std::ptr::null_mut();
        *ptr = 42;
    }
}
''',
                language="rust",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["UNSAFE_CODE"],
                expected_score=(1, 2),
                description="Rust unsafe block with raw pointer (MEDIUM)",
                tags=["rust", "unsafe", "raw_ptr", "medium"]
            ),

            # ========== VULNERABLE - unsafe with transmute ==========

            DetectorValidationSample(
                name="unsafe_code_transmute",
                code='''
fn cast_data() {
    unsafe {
        let value: u32 = 42;
        let bytes: [u8; 4] = std::mem::transmute(value);
    }
}
''',
                language="rust",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["UNSAFE_CODE"],
                expected_score=(1, 2),
                description="Rust unsafe block with transmute (MEDIUM)",
                tags=["rust", "unsafe", "transmute", "medium"]
            ),

            # ========== VULNERABLE - unsafe with FFI ==========

            DetectorValidationSample(
                name="unsafe_code_ffi",
                code='''
extern "C" {
    fn external_function();
}

fn call_external() {
    unsafe {
        external_function();
    }
}
''',
                language="rust",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["UNSAFE_CODE"],
                expected_score=(1, 2),
                description="Rust unsafe block with FFI call (MEDIUM)",
                tags=["rust", "unsafe", "ffi", "medium"]
            ),

            # ========== VULNERABLE - unsafe with pointer dereference ==========

            DetectorValidationSample(
                name="unsafe_code_deref",
                code='''
fn access_memory() {
    unsafe {
        let x = 42;
        let ptr = &x as *const i32;
        let value = *ptr;
    }
}
''',
                language="rust",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["UNSAFE_CODE"],
                expected_score=(1, 2),
                description="Rust unsafe block with pointer dereference (MEDIUM)",
                tags=["rust", "unsafe", "deref", "medium"]
            ),

            # ========== VULNERABLE - unsafe block with unclear operations ==========

            DetectorValidationSample(
                name="unsafe_code_unclear",
                code='''
fn mysterious_operation() {
    unsafe {
        // Some operation
        let x = 42;
    }
}
''',
                language="rust",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["UNSAFE_CODE"],
                expected_score=(1, 2),
                description="Rust unsafe block with unclear operations (MEDIUM)",
                tags=["rust", "unsafe", "unclear", "medium"]
            ),

            # ========== SECURE - safe Rust code ==========

            DetectorValidationSample(
                name="unsafe_code_safe",
                code='''
fn safe_operation(data: Vec<u32>) -> Vec<u32> {
    data.iter().map(|x| x * 2).collect()
}
''',
                language="rust",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Rust safe code without unsafe blocks (SECURE)",
                tags=["rust", "safe", "secure"]
            ),

            DetectorValidationSample(
                name="unsafe_code_safe_vec",
                code='''
fn process_data(data: &[u8]) -> Vec<u8> {
    let mut result = Vec::new();
    for byte in data {
        result.push(byte * 2);
    }
    result
}
''',
                language="rust",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Rust safe iteration without unsafe (SECURE)",
                tags=["rust", "safe", "iteration", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="unsafe_code_python_language",
                code='''
def process_data(data):
    return [x * 2 for x in data]
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Non-Rust language (out of scope)",
                tags=["python", "edge_case", "secure"]
            ),

            DetectorValidationSample(
                name="unsafe_code_cpp_language",
                code='''
void process() {
    int* ptr = new int(42);
    delete ptr;
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="C++ language (out of scope)",
                tags=["cpp", "edge_case", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUnsafeCodeDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Unsafe Code detector validation tests PASSED")
        print("The UnsafeCodeDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Unsafe Code detector validation tests FAILED")
        print("The UnsafeCodeDetector has accuracy issues that must be fixed.")
        sys.exit(1)
