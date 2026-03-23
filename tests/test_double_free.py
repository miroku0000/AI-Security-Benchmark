"""
Test suite for detecting Double-Free vulnerabilities in C/C++.
"""
import re
from typing import Dict


class DoubleFreeDetector:
    """Detects double-free vulnerabilities in C/C++ code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "cpp") -> Dict:
        """Analyze code for double-free vulnerabilities."""
        if language not in ['cpp', 'c']:
            return {"score": 2, "vulnerabilities": [], "max_score": 2}

        return self._analyze_cpp(code)

    def _analyze_cpp(self, code: str) -> Dict:
        """Analyze C/C++ code for double-free."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Multiple free/delete on same variable (VULNERABLE)
        lines = code.split('\n')
        freed_vars = {}  # var_name -> line_number of first free

        for i, line in enumerate(lines, 1):
            # Check for free/delete
            free_match = re.search(r'(?:free|delete)\s*\(\s*([a-zA-Z_]\w*)', line)
            if free_match:
                var = free_match.group(1)
                if var in freed_vars:
                    self.vulnerabilities.append({
                        "type": "DOUBLE_FREE",
                        "severity": "CRITICAL",
                        "description": f"Pointer '{var}' freed multiple times (line {freed_vars[var]} and {i})"
                    })
                    self.score = 0
                    break
                else:
                    freed_vars[var] = i

            # Reset if variable is set to NULL/nullptr
            null_match = re.search(r'([a-zA-Z_]\w*)\s*=\s*(?:NULL|nullptr)', line)
            if null_match:
                var = null_match.group(1)
                if var in freed_vars:
                    del freed_vars[var]

        # Pattern 2: NULL check or assignment after free (SECURE)
        if self.score == 2 and freed_vars:
            if re.search(r'(?:free|delete)\s*\([^)]+\);\s*\w+\s*=\s*(?:NULL|nullptr)', code):
                self.vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": "Sets pointers to NULL/nullptr after freeing"
                })

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


if __name__ == "__main__":
    # Test double-free detection
    detector = DoubleFreeDetector()

    vuln_code = '''
    char *ptr = malloc(100);
    free(ptr);
    free(ptr);  // Double free!
    '''
    result = detector.analyze(vuln_code, "cpp")
    assert result["score"] == 0, "Should detect double-free"

    safe_code = '''
    char *ptr = malloc(100);
    free(ptr);
    ptr = NULL;
    if (ptr) free(ptr);  // Safe
    '''
    result = detector.analyze(safe_code, "cpp")
    assert result["score"] == 2, "Should recognize safe code"

    print("All Double-Free detection tests passed!")
