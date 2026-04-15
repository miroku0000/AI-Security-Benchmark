#!/usr/bin/env python3
"""
Double-Free Detector Validation Tests

This module validates that the DoubleFreeDetector correctly identifies
double-free vulnerabilities in C/C++ code.

Test Coverage:
- Multiple free() calls on same pointer (CRITICAL)
- Multiple delete calls on same pointer (CRITICAL)
- Safe patterns: Setting pointer to NULL after freeing
- Function scope awareness: Different functions with same variable names
- Edge cases: Non-C/C++ languages, no free operations
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_double_free import DoubleFreeDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestDoubleFreeDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Double-Free Detector."""

    def get_detector(self):
        """Return DoubleFreeDetector instance."""
        return DoubleFreeDetector()

    def get_samples(self):
        """Return hand-crafted double-free test samples."""
        return [
            # ========== VULNERABLE - Double free() ==========

            DetectorValidationSample(
                name="double_free_basic",
                code='''
void cleanup() {
    char *ptr = malloc(100);
    free(ptr);
    free(ptr);  // Second release - double free
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["DOUBLE_FREE"],
                expected_score=(0, 2),
                description="Double free of same pointer (CRITICAL)",
                tags=["cpp", "free", "critical"]
            ),

            # ========== VULNERABLE - Double delete ==========

            DetectorValidationSample(
                name="double_delete_basic",
                code='''
void cleanup() {
    MyClass *obj = new MyClass();
    delete(obj);
    delete(obj);  // Second release - double delete
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["DOUBLE_FREE"],
                expected_score=(0, 2),
                description="Double delete of same pointer (CRITICAL)",
                tags=["cpp", "delete", "critical"]
            ),

            # ========== SECURE - free with NULL assignment ==========

            DetectorValidationSample(
                name="double_free_safe_null",
                code='''
void cleanup() {
    char *ptr = malloc(100);
    free(ptr);
    ptr = NULL;
    if (ptr) free(ptr);  // Safe - NULL check prevents double free
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="NULL assignment after free prevents double free (SECURE)",
                tags=["cpp", "null_check", "secure"]
            ),

            # ========== SECURE - Single free only ==========

            DetectorValidationSample(
                name="double_free_single_free",
                code='''
void cleanup() {
    char *ptr = malloc(100);
    strcpy(ptr, "data");
    free(ptr);
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Single free only (SECURE)",
                tags=["cpp", "single", "secure"]
            ),

            # ========== SECURE - delete with nullptr assignment ==========

            DetectorValidationSample(
                name="double_delete_safe_nullptr",
                code='''
void cleanup() {
    MyClass *obj = new MyClass();
    delete(obj);
    obj = nullptr;
    if (obj) delete(obj);  // Safe - nullptr check
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="nullptr assignment after delete (SECURE)",
                tags=["cpp", "nullptr", "secure"]
            ),

            # ========== SECURE - Function scope separation ==========

            DetectorValidationSample(
                name="double_free_function_scope",
                code='''
void func1() {
    char *ptr = malloc(100);
    free(ptr);
}

void func2() {
    char *ptr = malloc(200);
    free(ptr);
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Same variable name in different functions (SECURE)",
                tags=["cpp", "function_scope", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="double_free_no_operations",
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
                description="No free operations (no risk)",
                tags=["cpp", "no_free", "secure"]
            ),

            DetectorValidationSample(
                name="double_free_non_cpp_language",
                code='''
def cleanup():
    data = get_data()
    data = None
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Non-C/C++ language (out of scope)",
                tags=["python", "edge_case", "secure"]
            ),

            # ========== SECURE - NULL before any potential double free ==========

            DetectorValidationSample(
                name="double_free_immediate_null",
                code='''
void cleanup() {
    char *ptr = malloc(100);
    free(ptr);
    ptr = NULL;
    free(ptr);  // Safe - ptr is NULL, second call is no-op
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Immediate NULL assignment prevents double free (SECURE)",
                tags=["cpp", "null_assignment", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDoubleFreeDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Double-Free detector validation tests PASSED")
        print("The DoubleFreeDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Double-Free detector validation tests FAILED")
        print("The DoubleFreeDetector has accuracy issues that must be fixed.")
        sys.exit(1)
