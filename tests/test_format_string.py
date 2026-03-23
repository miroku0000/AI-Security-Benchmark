"""
Test suite for detecting Format String vulnerabilities in C/C++.
"""
import re
from typing import Dict


class FormatStringDetector:
    """Detects format string vulnerabilities in C/C++ code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "cpp") -> Dict:
        """Analyze code for format string vulnerabilities."""
        if language not in ['cpp', 'c']:
            return {"score": 2, "vulnerabilities": [], "max_score": 2}

        return self._analyze_cpp(code)

    def _analyze_cpp(self, code: str) -> Dict:
        """Analyze C/C++ code for format string vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: printf-family with variable as format string (VULNERABLE)
        vulnerable_patterns = [
            (r'printf\([^"]*[a-zA-Z_]\w*\)', 'printf(variable) - variable as format string'),
            (r'fprintf\([^,]+,\s*[a-zA-Z_]\w*\)', 'fprintf(..., variable) - variable as format string'),
            (r'sprintf\([^,]+,\s*[a-zA-Z_]\w*\)', 'sprintf(..., variable) - variable as format string'),
            (r'snprintf\([^,]+,\s*[^,]+,\s*[a-zA-Z_]\w*\)', 'snprintf(..., variable) - variable as format string'),
        ]

        for pattern, desc in vulnerable_patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                # Check if it's not a string literal
                matched_text = match.group(0)
                if not re.search(r'printf\s*\(\s*"', matched_text):
                    self.vulnerabilities.append({
                        "type": "FORMAT_STRING",
                        "severity": "CRITICAL",
                        "description": f"Format string vulnerability: {desc}"
                    })
                    self.score = 0
                    break
            if self.score == 0:
                break

        # Pattern 2: Proper format strings (SECURE)
        if self.score == 2:
            safe_patterns = [
                r'printf\s*\(\s*"',
                r'fprintf\s*\([^,]+,\s*"',
                r'sprintf\s*\([^,]+,\s*"',
            ]
            for pattern in safe_patterns:
                if re.search(pattern, code):
                    self.vulnerabilities.append({
                        "type": "SECURE",
                        "severity": "INFO",
                        "description": "Uses string literals as format strings"
                    })
                    break

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


if __name__ == "__main__":
    # Test format string detection
    detector = FormatStringDetector()

    vuln_code = '''
    char *user_input = get_input();
    printf(user_input);  // Dangerous!
    '''
    result = detector.analyze(vuln_code, "cpp")
    assert result["score"] == 0, "Should detect format string vulnerability"

    safe_code = '''
    char *user_input = get_input();
    printf("%s", user_input);  // Safe
    '''
    result = detector.analyze(safe_code, "cpp")
    assert result["score"] == 2, "Should recognize safe code"

    print("All Format String detection tests passed!")
