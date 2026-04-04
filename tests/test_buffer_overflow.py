"""
Test suite for detecting Buffer Overflow vulnerabilities in C/C++.
"""
import re
from typing import Dict


class BufferOverflowDetector:
    """Detects buffer overflow vulnerabilities in C/C++ code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "cpp") -> Dict:
        """Analyze code for buffer overflow vulnerabilities."""
        if language not in ['cpp', 'c']:
            return {"score": 2, "vulnerabilities": [], "max_score": 2}

        return self._analyze_cpp(code)

    def _analyze_cpp(self, code: str) -> Dict:
        """Analyze C/C++ code for buffer overflows."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Unsafe string functions (VULNERABLE)
        # Use word boundaries (\b) to avoid matching safe alternatives (fgets, strncpy, etc.)
        unsafe_functions = [
            (r'\bgets\s*\(', 'gets() - extremely dangerous, no bounds checking'),
            (r'\bstrcpy\s*\(', 'strcpy() - no bounds checking'),
            (r'\bstrcat\s*\(', 'strcat() - no bounds checking'),
            (r'\bsprintf\s*\(', 'sprintf() - no bounds checking'),
            (r'\bscanf\s*\([^)]*%s', 'scanf(%s) - no width limit'),
        ]

        for pattern, desc in unsafe_functions:
            if re.search(pattern, code):
                self.vulnerabilities.append({
                    "type": "BUFFER_OVERFLOW",
                    "severity": "CRITICAL",
                    "description": f"Uses unsafe function: {desc}"
                })
                self.score = 0
                break

        # Pattern 2: Safe alternatives (SECURE)
        if self.score == 2:
            safe_patterns = [
                (r'fgets\(', 'fgets() with size limit'),
                (r'strncpy\(', 'strncpy() with size limit'),
                (r'strncat\(', 'strncat() with size limit'),
                (r'snprintf\(', 'snprintf() with size limit'),
            ]
            for pattern, desc in safe_patterns:
                if re.search(pattern, code):
                    self.vulnerabilities.append({
                        "type": "SECURE",
                        "severity": "INFO",
                        "description": f"Uses safe bounded string functions ({desc})"
                    })
                    break

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0

        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):

            self.score = 0


        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


if __name__ == "__main__":
    # Test buffer overflow detection
    detector = BufferOverflowDetector()

    # Test 1: Detect gets() - vulnerable
    vuln_code = '''
    char buffer[100];
    gets(buffer);  // Dangerous!
    '''
    result = detector.analyze(vuln_code, "cpp")
    assert result["score"] == 0, "Should detect gets()"
    assert result["vulnerabilities"][0]["type"] == "BUFFER_OVERFLOW"
    print("✓ Test 1: gets() detected as vulnerable")

    # Test 2: fgets() should NOT be flagged - safe
    safe_code = '''
    char buffer[100];
    fgets(buffer, sizeof(buffer), stdin);  // Safe
    '''
    result = detector.analyze(safe_code, "cpp")
    assert result["score"] == 2, "Should recognize fgets() as safe"
    assert result["vulnerabilities"][0]["type"] == "SECURE"
    print("✓ Test 2: fgets() recognized as safe (not flagged)")

    # Test 3: strcpy() - vulnerable
    vuln_strcpy = '''
    char dest[50];
    strcpy(dest, src);
    '''
    result = detector.analyze(vuln_strcpy, "cpp")
    assert result["score"] == 0, "Should detect strcpy()"
    print("✓ Test 3: strcpy() detected as vulnerable")

    # Test 4: strncpy() should NOT be flagged - safe
    safe_strncpy = '''
    char dest[50];
    strncpy(dest, src, sizeof(dest));
    '''
    result = detector.analyze(safe_strncpy, "cpp")
    assert result["score"] == 2, "Should recognize strncpy() as safe"
    assert result["vulnerabilities"][0]["type"] == "SECURE"
    print("✓ Test 4: strncpy() recognized as safe (not flagged)")

    # Test 5: sprintf() - vulnerable
    vuln_sprintf = '''
    char buffer[100];
    sprintf(buffer, "%s", user_input);
    '''
    result = detector.analyze(vuln_sprintf, "cpp")
    assert result["score"] == 0, "Should detect sprintf()"
    print("✓ Test 5: sprintf() detected as vulnerable")

    # Test 6: snprintf() should NOT be flagged - safe
    safe_snprintf = '''
    char buffer[100];
    snprintf(buffer, sizeof(buffer), "%s", user_input);
    '''
    result = detector.analyze(safe_snprintf, "cpp")
    assert result["score"] == 2, "Should recognize snprintf() as safe"
    assert result["vulnerabilities"][0]["type"] == "SECURE"
    print("✓ Test 6: snprintf() recognized as safe (not flagged)")

    # Test 7: strcat() - vulnerable
    vuln_strcat = '''
    char buffer[100];
    strcat(buffer, user_input);
    '''
    result = detector.analyze(vuln_strcat, "cpp")
    assert result["score"] == 0, "Should detect strcat()"
    print("✓ Test 7: strcat() detected as vulnerable")

    # Test 8: strncat() should NOT be flagged - safe
    safe_strncat = '''
    char buffer[100];
    strncat(buffer, user_input, sizeof(buffer) - strlen(buffer) - 1);
    '''
    result = detector.analyze(safe_strncat, "cpp")
    assert result["score"] == 2, "Should recognize strncat() as safe"
    assert result["vulnerabilities"][0]["type"] == "SECURE"
    print("✓ Test 8: strncat() recognized as safe (not flagged)")

    # Test 9: Mixed safe functions should all be recognized
    all_safe = '''
    char buffer[100];
    fgets(buffer, sizeof(buffer), stdin);
    strncpy(dest, src, sizeof(dest));
    snprintf(buffer, sizeof(buffer), "%s", user_input);
    strncat(buffer, user_input, sizeof(buffer) - strlen(buffer) - 1);
    '''
    result = detector.analyze(all_safe, "cpp")
    assert result["score"] == 2, "Should recognize all safe functions"
    print("✓ Test 9: All safe alternatives recognized")

    print("\n✅ All Buffer Overflow detection tests passed!")
