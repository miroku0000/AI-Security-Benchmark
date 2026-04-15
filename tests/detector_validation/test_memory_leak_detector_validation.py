#!/usr/bin/env python3
"""
Memory Leak Detector Validation Tests

This module validates that the MemoryLeakDetector correctly identifies
memory leak vulnerabilities in C/C++ code.

Test Coverage:
- Unbalanced allocations: More allocations than frees
- Return without free: Function returns before freeing allocated memory
- Balanced allocations and frees (secure)
- Edge cases: No allocations, non-C/C++ languages
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_memory_leak import MemoryLeakDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestMemoryLeakDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Memory Leak Detector."""

    def get_detector(self):
        """Return MemoryLeakDetector instance."""
        return MemoryLeakDetector()

    def get_samples(self):
        """Return hand-crafted memory leak test samples."""
        return [
            # ========== VULNERABLE - Unbalanced Allocations ==========

            DetectorValidationSample(
                name="memory_leak_malloc_no_free",
                code='''
void process_data() {
    char *buffer = malloc(100);
    strcpy(buffer, "data");
    // Memory leak - buffer not freed
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MEMORY_LEAK"],
                expected_score=(0, 2),
                description="malloc without free (MEDIUM)",
                tags=["cpp", "malloc", "unbalanced"]
            ),

            DetectorValidationSample(
                name="memory_leak_calloc_no_free",
                code='''
void allocate_array() {
    int *arr = calloc(10, sizeof(int));
    arr[0] = 42;
    // Memory leak - arr not cleaned up
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MEMORY_LEAK"],
                expected_score=(0, 2),
                description="calloc without free (MEDIUM)",
                tags=["cpp", "calloc", "unbalanced"]
            ),

            DetectorValidationSample(
                name="memory_leak_multiple_malloc",
                code='''
void process() {
    char *ptr1 = malloc(100);
    char *ptr2 = malloc(200);
    char *ptr3 = malloc(300);

    free(ptr1);
    // Memory leak - ptr2 and ptr3 not cleaned up
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MEMORY_LEAK"],
                expected_score=(0, 2),
                description="Multiple allocations with insufficient frees (MEDIUM)",
                tags=["cpp", "multiple", "unbalanced"]
            ),

            # ========== VULNERABLE - Return Without Free ==========

            DetectorValidationSample(
                name="memory_leak_return_without_free",
                code='''
void process() {
    char *ptr = malloc(100);
    strcpy(ptr, "data");
    return;  // Returns without freeing ptr
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MEMORY_LEAK"],
                expected_score=(0, 2),
                description="Returns without freeing allocated memory (HIGH)",
                tags=["cpp", "return", "high"]
            ),

            DetectorValidationSample(
                name="memory_leak_early_return",
                code='''
int process(int condition) {
    char *buffer = malloc(1024);
    if (condition > 10) {
        return -1;  // Early return without freeing buffer
    }
    process_buffer(buffer);
    return 0;
}
''',
                language="cpp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MEMORY_LEAK"],
                expected_score=(0, 2),
                description="Early return path leaks memory (HIGH)",
                tags=["cpp", "early_return", "high"]
            ),

            # ========== SECURE - Balanced Allocations ==========

            DetectorValidationSample(
                name="memory_leak_malloc_with_free",
                code='''
void process_data() {
    char *buffer = malloc(100);
    strcpy(buffer, "data");
    free(buffer);  // Properly freed
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="malloc with matching free (SECURE)",
                tags=["cpp", "malloc", "secure"]
            ),

            DetectorValidationSample(
                name="memory_leak_multiple_balanced",
                code='''
void process() {
    char *ptr1 = malloc(100);
    char *ptr2 = malloc(200);

    process_data(ptr1, ptr2);

    free(ptr1);
    free(ptr2);  // All allocations freed
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Multiple allocations with matching frees (SECURE)",
                tags=["cpp", "multiple", "secure"]
            ),

            DetectorValidationSample(
                name="memory_leak_new_with_delete",
                code='''
void create_object() {
    MyClass *obj = new MyClass();
    obj->initialize();
    delete(obj);  // Cleaned up properly
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="new with matching delete (SECURE)",
                tags=["cpp", "new", "delete", "secure"]
            ),

            DetectorValidationSample(
                name="memory_leak_return_after_free",
                code='''
void process() {
    char *ptr = malloc(100);
    strcpy(ptr, "data");
    free(ptr);
    return;  // Returns after freeing - safe
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Returns after freeing memory (SECURE)",
                tags=["cpp", "return", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="memory_leak_no_allocations",
                code='''
void process_data(char *existing_buffer) {
    strcpy(existing_buffer, "data");
    // No allocations to free
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="No memory allocations (no risk)",
                tags=["cpp", "no_allocations", "secure"]
            ),

            DetectorValidationSample(
                name="memory_leak_non_cpp_language",
                code='''
def process_data():
    data = ["item1", "item2"]
    return data
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Non-C/C++ language (out of scope)",
                tags=["python", "edge_case", "secure"]
            ),

            DetectorValidationSample(
                name="memory_leak_realloc_with_free",
                code='''
void expand_buffer(char *old_buffer) {
    char *new_buffer = realloc(old_buffer, 200);
    strcpy(new_buffer, "expanded data");
    free(new_buffer);
}
''',
                language="cpp",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="realloc with matching free (SECURE)",
                tags=["cpp", "realloc", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMemoryLeakDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Memory Leak detector validation tests PASSED")
        print("The MemoryLeakDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Memory Leak detector validation tests FAILED")
        print("The MemoryLeakDetector has accuracy issues that must be fixed.")
        sys.exit(1)
