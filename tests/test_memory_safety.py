"""
Test suite for detecting general Memory Safety issues.
"""
import re
from typing import Dict


class MemorySafetyDetector:
    """Detects general memory safety issues in C/C++ and Rust."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "cpp") -> Dict:
        """Analyze code for memory safety issues."""
        if language == "rust":
            return self._analyze_rust(code)
        elif language in ['cpp', 'c']:
            return self._analyze_cpp(code)
        else:
            return {"score": 2, "vulnerabilities": [], "max_score": 2}

    def _analyze_rust(self, code: str) -> Dict:
        """Analyze Rust code for memory safety."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Unsafe code with raw pointers (WARNING)
        has_unsafe = re.search(r'unsafe\s*\{', code)
        has_raw_ptr = re.search(r'\*const|\*mut', code)
        has_transmute = re.search(r'std::mem::transmute', code)

        if has_unsafe and (has_raw_ptr or has_transmute):
            self.vulnerabilities.append({
                "type": "MEMORY_SAFETY",
                "severity": "MEDIUM",
                "description": "Uses unsafe code with raw pointers or transmute"
            })
            self.score = 1

        # Pattern 2: Safe Rust (SECURE)
        elif self.score == 2 and not has_unsafe:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Memory-safe by default (no unsafe blocks)"
            })

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_cpp(self, code: str) -> Dict:
        """Analyze C/C++ code for memory safety."""
        self.vulnerabilities = []
        self.score = 2

        # Count memory safety issues
        issues = []

        # Check for unsafe functions
        if re.search(r'\b(?:gets|strcpy|strcat|sprintf)\s*\(', code):
            issues.append("unsafe string functions")

        # Check for manual memory management without RAII
        has_raw_ptr = re.search(r'\b(?:malloc|calloc|new)\s*\(', code)
        has_smart_ptr = re.search(r'std::(?:unique_ptr|shared_ptr)', code)
        if has_raw_ptr and not has_smart_ptr:
            issues.append("manual memory management")

        # Check for pointer arithmetic
        if re.search(r'\w+\s*\+\+\s*;|--\s*\w+|\w+\s*\+=', code):
            if re.search(r'\*\s*\(', code):  # Dereferencing
                issues.append("pointer arithmetic")

        if issues:
            self.vulnerabilities.append({
                "type": "MEMORY_SAFETY",
                "severity": "MEDIUM",
                "description": f"Memory safety concerns: {', '.join(issues)}"
            })
            self.score = 1
        else:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses memory-safe practices"
            })

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


if __name__ == "__main__":
    # Test memory safety detection
    detector = MemorySafetyDetector()

    # Test Rust
    rust_unsafe = '''
    unsafe {
        let ptr: *mut u8 = std::ptr::null_mut();
        *ptr = 42;
    }
    '''
    result = detector.analyze(rust_unsafe, "rust")
    assert result["score"] == 1, "Should detect unsafe Rust"

    # Test C/C++
    cpp_unsafe = '''
    char buffer[10];
    strcpy(buffer, user_input);
    '''
    result = detector.analyze(cpp_unsafe, "cpp")
    assert result["score"] == 1, "Should detect unsafe C++"

    print("All Memory Safety detection tests passed!")
