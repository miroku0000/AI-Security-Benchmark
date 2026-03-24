"""
Test suite for detecting Null Pointer Dereference vulnerabilities in C/C++.
"""
import re
from typing import Dict


class NullPointerDetector:
    """Detects null pointer dereference vulnerabilities in C/C++ code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "cpp") -> Dict:
        """Analyze code for null pointer dereferences."""
        if language not in ['cpp', 'c']:
            return {"score": 2, "vulnerabilities": [], "max_score": 2}

        return self._analyze_cpp(code)

    def _analyze_cpp(self, code: str) -> Dict:
        """Analyze C/C++ code for null pointer dereferences."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Pointer dereference without NULL check (VULNERABLE)
        # Look for malloc/new followed by dereference without NULL check
        lines = code.split('\n')
        allocated_vars = set()

        for i, line in enumerate(lines):
            # Check for allocation
            alloc_match = re.search(r'([a-zA-Z_]\w*)\s*=\s*(?:malloc|calloc|realloc|new)\s*\(', line)
            if alloc_match:
                var = alloc_match.group(1)
                allocated_vars.add(var)

            # Check for NULL check
            if re.search(r'if\s*\(\s*!?\s*([a-zA-Z_]\w*)\s*(?:==|!=)\s*(?:NULL|nullptr|0)\s*\)', line):
                # Remove from tracking if NULL checked
                null_check_var = re.search(r'if\s*\(\s*!?\s*([a-zA-Z_]\w*)', line)
                if null_check_var:
                    allocated_vars.discard(null_check_var.group(1))

            # Check for dereference of unvalidated pointer
            for var in list(allocated_vars):
                if re.search(rf'\b{var}\s*(?:->|\[|\*{var})', line):
                    self.vulnerabilities.append({
                        "type": "NULL_POINTER_DEREFERENCE",
                        "severity": "HIGH",
                        "description": f"Pointer '{var}' dereferenced without NULL check"
                    })
                    self.score = 0
                    allocated_vars.discard(var)
                    break

            if self.score == 0:
                break

        # Pattern 2: NULL checks present (SECURE)
        if self.score == 2:
            if re.search(r'if\s*\(\s*\w+\s*(?:==|!=)\s*(?:NULL|nullptr)', code):
                self.vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": "Validates pointers before use"
                })

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


if __name__ == "__main__":
    # Test null pointer detection
    detector = NullPointerDetector()

    vuln_code = '''
    char *ptr = malloc(100);
    strcpy(ptr, "data");  // No NULL check!
    '''
    result = detector.analyze(vuln_code, "cpp")
    assert result["score"] == 0, "Should detect null pointer dereference"

    safe_code = '''
    char *ptr = malloc(100);
    if (ptr != NULL) {
        strcpy(ptr, "data");  // Safe
    }
    '''
    result = detector.analyze(safe_code, "cpp")
    assert result["score"] == 2, "Should recognize safe code"

    print("All Null Pointer detection tests passed!")
