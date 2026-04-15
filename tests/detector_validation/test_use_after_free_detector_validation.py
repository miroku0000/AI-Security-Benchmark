#!/usr/bin/env python3
"""
Use-After-Free Detector Validation Tests

This module validates that the UseAfterFreeDetector correctly identifies
use-after-free vulnerabilities in C/C++ code.

Test Coverage:
- free() followed by pointer dereference (->, [], .) (CRITICAL)
- delete followed by pointer dereference (CRITICAL)
- Safe pattern: NULL/nullptr assignment after free (SECURE)
- Edge cases: No usage after free, non-C/C++ languages
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_use_after_free import UseAfterFreeDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestUseAfterFreeDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Use-After-Free Detector."""

    def get_detector(self):
        """Return UseAfterFreeDetector instance."""
        return UseAfterFreeDetector()

    def get_samples(self):
        """Return hand-crafted use-after-free test samples."""
        return [
            # ========== VULNERABLE - Arrow dereference after free ==========

            DetectorValidationSample(
                name="use_after_free_arrow_deref",
                code='''
void process_data() {
    struct Data *ptr = malloc(sizeof(struct Data));
    free(ptr);
    ptr->value = 42;  // Use after release
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["USE_AFTER_FREE"],
                expected_score=(0, 2),
                description="Arrow dereference after free (CRITICAL)",
                tags=["cpp", "arrow", "critical"]
            ),

            # ========== VULNERABLE - Array access after free ==========

            DetectorValidationSample(
                name="use_after_free_array_access",
                code='''
void process_buffer() {
    char *buffer = malloc(100);
    free(buffer);
    buffer[0] = 'A';  // Use after release
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["USE_AFTER_FREE"],
                expected_score=(0, 2),
                description="Array access after free (CRITICAL)",
                tags=["cpp", "array", "critical"]
            ),

            # ========== VULNERABLE - Member access after free ==========

            DetectorValidationSample(
                name="use_after_free_member_access",
                code='''
void process_object() {
    struct Data *ptr = malloc(sizeof(struct Data));
    free(ptr);
    int val = ptr.value;  // Use after release
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["USE_AFTER_FREE"],
                expected_score=(0, 2),
                description="Member access after free (CRITICAL)",
                tags=["cpp", "member", "critical"]
            ),

            # ========== VULNERABLE - Arrow dereference after delete ==========

            DetectorValidationSample(
                name="use_after_free_delete_arrow",
                code='''
void process_object() {
    MyClass *obj = new MyClass();
    delete(obj);
    obj->method();  // Use after release
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["USE_AFTER_FREE"],
                expected_score=(0, 2),
                description="Arrow dereference after delete (CRITICAL)",
                tags=["cpp", "delete", "arrow", "critical"]
            ),

            # ========== SECURE - NULL assignment after free ==========

            DetectorValidationSample(
                name="use_after_free_null_assignment",
                code='''
void process_data() {
    char *ptr = malloc(100);
    free(ptr);
    ptr = NULL;  // Safe - prevents use after release
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="NULL assignment after free (SECURE)",
                tags=["cpp", "null", "secure"]
            ),

            # ========== SECURE - nullptr assignment after delete ==========

            DetectorValidationSample(
                name="use_after_free_nullptr_assignment",
                code='''
void process_object() {
    MyClass *obj = new MyClass();
    delete obj;
    obj = nullptr;  // Safe - prevents use after release
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="nullptr assignment after delete (SECURE)",
                tags=["cpp", "nullptr", "secure"]
            ),

            # ========== SECURE - No usage after free ==========

            DetectorValidationSample(
                name="use_after_free_no_usage",
                code='''
void process_data() {
    char *ptr = malloc(100);
    strcpy(ptr, "data");
    free(ptr);
    return;  // No use after release
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="No usage after free (SECURE)",
                tags=["cpp", "no_usage", "secure"]
            ),

            # ========== SECURE - Before free only ==========

            DetectorValidationSample(
                name="use_after_free_before_only",
                code='''
void process_data() {
    char *ptr = malloc(100);
    ptr[0] = 'A';
    ptr->next = NULL;
    free(ptr);  // Usage before, not after
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Usage before free only (SECURE)",
                tags=["cpp", "before_only", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="use_after_free_no_pointers",
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
                description="No pointers or allocation (no risk)",
                tags=["cpp", "no_pointers", "secure"]
            ),

            DetectorValidationSample(
                name="use_after_free_non_cpp_language",
                code='''
def process_data():
    data = get_data()
    del data
    print(data)
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Non-C/C++ language (out of scope)",
                tags=["python", "edge_case", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUseAfterFreeDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Use-After-Free detector validation tests PASSED")
        print("The UseAfterFreeDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Use-After-Free detector validation tests FAILED")
        print("The UseAfterFreeDetector has accuracy issues that must be fixed.")
        sys.exit(1)
