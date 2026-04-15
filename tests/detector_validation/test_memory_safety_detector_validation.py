#!/usr/bin/env python3
"""
Memory Safety Detector Validation Tests

This module validates that the MemorySafetyDetector correctly identifies
memory safety issues in C/C++ and Rust code.

Test Coverage:
- Rust: unsafe blocks with raw pointers (MEDIUM)
- Rust: safe code without unsafe blocks (SECURE)
- C/C++: Unsafe string functions (MEDIUM)
- C/C++: Manual memory management without smart pointers (MEDIUM)
- C/C++: Safe practices with smart pointers (SECURE)
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_memory_safety import MemorySafetyDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestMemorySafetyDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Memory Safety Detector."""

    def get_detector(self):
        """Return MemorySafetyDetector instance."""
        return MemorySafetyDetector()

    def get_samples(self):
        """Return hand-crafted memory safety test samples."""
        return [
            # ========== RUST - MEDIUM RISK - unsafe with raw pointers ==========

            DetectorValidationSample(
                name="memory_safety_rust_unsafe_raw_ptr",
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
                expected_vulnerabilities=["MEMORY_SAFETY"],
                expected_score=(1, 2),
                description="Rust unsafe block with raw pointer (MEDIUM)",
                tags=["rust", "unsafe", "raw_ptr", "medium"]
            ),

            DetectorValidationSample(
                name="memory_safety_rust_unsafe_transmute",
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
                expected_vulnerabilities=["MEMORY_SAFETY"],
                expected_score=(1, 2),
                description="Rust unsafe block with transmute (MEDIUM)",
                tags=["rust", "unsafe", "transmute", "medium"]
            ),

            # ========== RUST - SECURE - safe code ==========

            DetectorValidationSample(
                name="memory_safety_rust_safe",
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

            # ========== C/C++ - MEDIUM RISK - unsafe string functions ==========

            DetectorValidationSample(
                name="memory_safety_cpp_strcpy",
                code='''
void copy_data(char *user_input) {
    char buffer[100];
    strcpy(buffer, user_input);
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MEMORY_SAFETY"],
                expected_score=(1, 2),
                description="C++ uses unsafe strcpy (MEDIUM)",
                tags=["cpp", "strcpy", "medium"]
            ),

            DetectorValidationSample(
                name="memory_safety_cpp_gets",
                code='''
void read_input() {
    char buffer[100];
    gets(buffer);
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MEMORY_SAFETY"],
                expected_score=(1, 2),
                description="C++ uses unsafe gets (MEDIUM)",
                tags=["cpp", "gets", "medium"]
            ),

            # ========== C/C++ - MEDIUM RISK - manual memory management ==========

            DetectorValidationSample(
                name="memory_safety_cpp_malloc",
                code='''
void process_data() {
    char *buffer = malloc(100);
    process(buffer);
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MEMORY_SAFETY"],
                expected_score=(1, 2),
                description="C++ manual malloc without smart pointers (MEDIUM)",
                tags=["cpp", "malloc", "medium"]
            ),

            # ========== C/C++ - SECURE - smart pointers ==========

            DetectorValidationSample(
                name="memory_safety_cpp_unique_ptr",
                code='''
void create_object() {
    std::unique_ptr<MyClass> obj = std::make_unique<MyClass>();
    obj->process();
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="C++ uses unique_ptr (SECURE)",
                tags=["cpp", "unique_ptr", "secure"]
            ),

            DetectorValidationSample(
                name="memory_safety_cpp_shared_ptr",
                code='''
void share_object() {
    std::shared_ptr<MyClass> obj = std::make_shared<MyClass>();
    obj->process();
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="C++ uses shared_ptr (SECURE)",
                tags=["cpp", "shared_ptr", "secure"]
            ),

            # ========== C/C++ - SECURE - no memory operations ==========

            DetectorValidationSample(
                name="memory_safety_cpp_stack_only",
                code='''
void calculate_sum(int a, int b) {
    int result = a + b;
    return result;
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="C++ stack-only variables (SECURE)",
                tags=["cpp", "stack", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="memory_safety_python_language",
                code='''
def process_data(data):
    return [x * 2 for x in data]
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Python has automatic memory management (out of scope)",
                tags=["python", "edge_case", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMemorySafetyDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Memory Safety detector validation tests PASSED")
        print("The MemorySafetyDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Memory Safety detector validation tests FAILED")
        print("The MemorySafetyDetector has accuracy issues that must be fixed.")
        sys.exit(1)
