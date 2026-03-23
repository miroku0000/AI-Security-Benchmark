"""
Test suite for detecting Use-After-Free vulnerabilities in C/C++.
"""
import re
from typing import Dict


class UseAfterFreeDetector:
    """Detects use-after-free vulnerabilities in C/C++ code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "cpp") -> Dict:
        """Analyze code for use-after-free vulnerabilities."""
        if language not in ['cpp', 'c']:
            return {"score": 2, "vulnerabilities": [], "max_score": 2}

        return self._analyze_cpp(code)

    def _analyze_cpp(self, code: str) -> Dict:
        """Analyze C/C++ code for use-after-free."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Pointer use after free (VULNERABLE)
        # Look for: free(ptr) followed by usage of ptr
        lines = code.split('\n')
        freed_vars = set()

        for i, line in enumerate(lines):
            # Check for free/delete
            free_match = re.search(r'(?:free|delete)\s*\(\s*([a-zA-Z_]\w*)', line)
            if free_match:
                freed_vars.add(free_match.group(1))

            # Check for usage of freed variables
            for var in freed_vars:
                # Look for variable usage (dereference, member access, etc.)
                if re.search(rf'\b{var}\s*(?:->|\[|\.|\()', line):
                    self.vulnerabilities.append({
                        "type": "USE_AFTER_FREE",
                        "severity": "CRITICAL",
                        "description": f"Pointer '{var}' used after being freed"
                    })
                    self.score = 0
                    break

            if self.score == 0:
                break

        # Pattern 2: NULL pointer assignment after free (SECURE)
        if self.score == 2:
            if re.search(r'free\([^)]+\);\s*[a-zA-Z_]\w*\s*=\s*NULL', code) or \
               re.search(r'delete\s+[^;]+;\s*[a-zA-Z_]\w*\s*=\s*nullptr', code):
                self.vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": "Sets pointer to NULL/nullptr after freeing"
                })

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


if __name__ == "__main__":
    # Test use-after-free detection
    detector = UseAfterFreeDetector()

    vuln_code = '''
    char *ptr = malloc(100);
    free(ptr);
    strcpy(ptr, "data");  // Use after free!
    '''
    result = detector.analyze(vuln_code, "cpp")
    assert result["score"] == 0, "Should detect use-after-free"

    safe_code = '''
    char *ptr = malloc(100);
    free(ptr);
    ptr = NULL;  // Safe
    '''
    result = detector.analyze(safe_code, "cpp")
    assert result["score"] == 2, "Should recognize safe code"

    print("All Use-After-Free detection tests passed!")
