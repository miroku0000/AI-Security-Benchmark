#!/usr/bin/env python3
"""
Null Pointer Dereference Detector Validation Tests

This module validates that the NullPointerDetector correctly identifies
null pointer dereference vulnerabilities in C/C++ code.

Test Coverage:
- malloc/calloc/realloc/new followed by dereference without NULL check
- Pointer dereference with proper NULL checks (secure)
- Various dereference patterns: ->, [], *ptr
- Edge cases: no allocations, untracked pointers
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_null_pointer import NullPointerDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestNullPointerDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Null Pointer Dereference Detector."""

    def get_detector(self):
        """Return NullPointerDetector instance."""
        return NullPointerDetector()

    def get_samples(self):
        """Return hand-crafted null pointer test samples."""
        return [
            # ========== VULNERABLE - malloc without NULL check ==========

            DetectorValidationSample(
                name="null_ptr_malloc_no_check",
                code='''
void process_data() {
    char *ptr = malloc(100);
    ptr[0] = 'A';  // Array dereference without NULL check
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["NULL_POINTER_DEREFERENCE"],
                expected_score=(0, 2),
                description="malloc followed by array access without NULL check (CRITICAL)",
                tags=["cpp", "malloc", "critical"]
            ),

            DetectorValidationSample(
                name="null_ptr_calloc_arrow_deref",
                code='''
struct Data {
    int value;
};

void process() {
    struct Data *ptr = calloc(1, sizeof(struct Data));
    ptr->value = 42;  // Arrow dereference without NULL check
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["NULL_POINTER_DEREFERENCE"],
                expected_score=(0, 2),
                description="calloc followed by -> dereference without NULL check (CRITICAL)",
                tags=["cpp", "calloc", "arrow"]
            ),

            DetectorValidationSample(
                name="null_ptr_realloc_array_access",
                code='''
void expand_buffer(char *buf) {
    char *ptr = realloc(buf, 200);
    ptr[0] = 'A';  // Array access without NULL check
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["NULL_POINTER_DEREFERENCE"],
                expected_score=(0, 2),
                description="realloc followed by array access without NULL check (CRITICAL)",
                tags=["cpp", "realloc", "array"]
            ),

            # ========== SECURE - With NULL checks ==========

            DetectorValidationSample(
                name="null_ptr_malloc_with_null_check",
                code='''
void process_data() {
    char *ptr = malloc(100);
    if (ptr != NULL) {
        strcpy(ptr, "data");
    }
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="malloc with != NULL check before dereference (SECURE)",
                tags=["cpp", "malloc", "secure"]
            ),

            DetectorValidationSample(
                name="null_ptr_calloc_with_nullptr_check",
                code='''
struct Data {
    int value;
};

void process() {
    struct Data *ptr = calloc(1, sizeof(struct Data));
    if (ptr != nullptr) {
        ptr->value = 42;
    }
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="calloc with != nullptr check (SECURE)",
                tags=["cpp", "calloc", "nullptr", "secure"]
            ),

            DetectorValidationSample(
                name="null_ptr_realloc_with_eq_null_check",
                code='''
void expand_buffer(char *buf) {
    char *ptr = realloc(buf, 200);
    if (ptr == NULL) {
        return;
    }
    ptr[0] = 'A';
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="realloc with == NULL check (SECURE)",
                tags=["cpp", "realloc", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="null_ptr_no_allocation",
                code='''
void process_data() {
    int value = 42;
    printf("%d", value);
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="No pointer allocation (no risk)",
                tags=["cpp", "no_allocation", "secure"]
            ),

            DetectorValidationSample(
                name="null_ptr_non_cpp_language",
                code='''
def process_data():
    data = []
    data.append(42)
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Non-C/C++ language (out of scope)",
                tags=["python", "edge_case", "secure"]
            ),

            DetectorValidationSample(
                name="null_ptr_allocation_no_deref",
                code='''
void allocate_only() {
    char *ptr = malloc(100);
    // Leak but no dereference
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Allocation without dereference (no NULL deref risk)",
                tags=["cpp", "no_deref", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNullPointerDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Null Pointer detector validation tests PASSED")
        print("The NullPointerDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Null Pointer detector validation tests FAILED")
        print("The NullPointerDetector has accuracy issues that must be fixed.")
        sys.exit(1)
