"""
Test suite for detecting Integer Overflow vulnerabilities.
"""
import re
from typing import Dict


class IntegerOverflowDetector:
    """Detects integer overflow vulnerabilities."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "cpp") -> Dict:
        """Analyze code for integer overflow vulnerabilities."""
        if language == "rust":
            return self._analyze_rust(code)
        elif language in ['cpp', 'c']:
            return self._analyze_cpp(code)
        else:
            return {"score": 2, "vulnerabilities": [], "max_score": 2}

    def _analyze_rust(self, code: str) -> Dict:
        """Analyze Rust code for integer overflow."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Unchecked arithmetic (VULNERABLE)
        has_multiply = re.search(r'\w+\s*\*\s*\w+', code)
        has_add = re.search(r'\w+\s*\+\s*\w+', code)
        has_checked = re.search(r'checked_mul|checked_add|saturating_mul|saturating_add|overflowing_mul', code)

        if (has_multiply or has_add) and not has_checked:
            self.vulnerabilities.append({
                "type": "INTEGER_OVERFLOW",
                "severity": "HIGH",
                "description": "Arithmetic without overflow checks (use checked_mul/checked_add)"
            })
            self.score = 0

        # Pattern 2: Checked arithmetic (SECURE)
        elif self.score == 2 and has_checked:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses checked arithmetic (checked_mul/saturating_mul)"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0

        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):

            self.score = 0


        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_cpp(self, code: str) -> Dict:
        """Analyze C/C++ code for integer overflow."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Arithmetic operations without bounds checking (VULNERABLE)
        has_multiply = re.search(r'\w+\s*\*\s*\w+', code)
        has_malloc = re.search(r'malloc\([^)]*\*[^)]*\)', code)

        # FIXED (Iteration 14): Recognize SIZE_MAX and division-based overflow checks
        # Old pattern only recognized INT_MAX, missing standard SIZE_MAX checks
        has_bounds_check = re.search(
            r'if\s*\([^)]*>\s*(INT_MAX|SIZE_MAX|UINT_MAX)|'  # Max value comparisons
            r'if\s*\([^)]*<\s*0|'                             # Underflow checks
            r'if\s*\([^)]*>\s*[A-Z_]+\s*/|'                   # Division-based checks (a > MAX / b)
            r'checked_mul|checked_add|mul_overflow|add_overflow',  # Helper functions
            code
        )

        if (has_multiply or has_malloc) and not has_bounds_check:
            self.vulnerabilities.append({
                "type": "INTEGER_OVERFLOW",
                "severity": "HIGH",
                "description": "Arithmetic/allocation without overflow checking"
            })
            self.score = 0

        # Pattern 2: Bounds checking (SECURE)
        elif self.score == 2 and has_bounds_check:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses bounds checking for arithmetic"
            })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0

        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):

            self.score = 0


        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


if __name__ == "__main__":
    # Test integer overflow detection
    detector = IntegerOverflowDetector()

    # Test Rust
    rust_vuln = '''
    let result = a * b;  // No overflow check
    '''
    result = detector.analyze(rust_vuln, "rust")
    assert result["score"] == 0, "Should detect integer overflow"

    rust_safe = '''
    let result = a.checked_mul(b).unwrap();  // Safe
    '''
    result = detector.analyze(rust_safe, "rust")
    assert result["score"] == 2, "Should recognize safe code"

    # Test C/C++
    cpp_vuln = '''
    int size = width * height;
    char *buffer = malloc(size);
    '''
    result = detector.analyze(cpp_vuln, "cpp")
    assert result["score"] == 0, "Should detect overflow in malloc"

    print("All Integer Overflow detection tests passed!")
