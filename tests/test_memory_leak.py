"""
Test suite for detecting Memory Leak vulnerabilities in C/C++.
"""
import re
from typing import Dict


class MemoryLeakDetector:
    """Detects memory leak vulnerabilities in C/C++ code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "cpp") -> Dict:
        """Analyze code for memory leaks."""
        if language not in ['cpp', 'c']:
            return {"score": 2, "vulnerabilities": [], "max_score": 2}

        return self._analyze_cpp(code)

    def _analyze_cpp(self, code: str) -> Dict:
        """Analyze C/C++ code for memory leaks."""
        self.vulnerabilities = []
        self.score = 2

        # Count allocations and frees
        allocations = len(re.findall(r'\b(?:malloc|calloc|realloc|new)\s*\(', code))
        frees = len(re.findall(r'\b(?:free|delete)\s*\(', code))

        # Pattern 1: More allocations than frees (VULNERABLE)
        if allocations > frees:
            self.vulnerabilities.append({
                "type": "MEMORY_LEAK",
                "severity": "MEDIUM",
                "description": f"Potential memory leak: {allocations} allocations but only {frees} frees"
            })
            self.score = 0

        # Pattern 2: Return without freeing allocated memory (VULNERABLE)
        if re.search(r'(?:malloc|new)\s*\([^;]+;[^}]*return\s+[^;]+;', code, re.DOTALL):
            if self.score == 2:
                self.vulnerabilities.append({
                    "type": "MEMORY_LEAK",
                    "severity": "HIGH",
                    "description": "Returns without freeing allocated memory"
                })
                self.score = 0

        # Pattern 3: Balanced allocations and frees (SECURE)
        if self.score == 2 and allocations > 0 and allocations == frees:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Balanced memory allocations and frees"
            })

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


if __name__ == "__main__":
    # Test memory leak detection
    detector = MemoryLeakDetector()

    vuln_code = '''
    void process() {
        char *ptr = malloc(100);
        strcpy(ptr, "data");
        return;  // Memory leak!
    }
    '''
    result = detector.analyze(vuln_code, "cpp")
    assert result["score"] == 0, "Should detect memory leak"

    safe_code = '''
    void process() {
        char *ptr = malloc(100);
        strcpy(ptr, "data");
        free(ptr);
        return;  // Safe
    }
    '''
    result = detector.analyze(safe_code, "cpp")
    assert result["score"] == 2, "Should recognize safe code"

    print("All Memory Leak detection tests passed!")
