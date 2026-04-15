"""
Test suite for detecting HTTP Header Injection / Response Splitting vulnerabilities.

HTTP Header Injection occurs when user-controlled input is directly placed into HTTP
response headers without sanitization. Attackers can inject CRLF characters (\\r\\n)
to split the response, inject additional headers, or perform XSS attacks.

Attack Example:
    filename = "test.pdf\\r\\nContent-Type: text/html\\r\\n\\r\\n<script>alert(1)</script>"
    response.setHeader("Content-Disposition", "attachment; filename=\\"" + filename + "\\"");

Result:
    Content-Disposition: attachment; filename="test.pdf
    Content-Type: text/html

    <script>alert(1)</script>"

This allows:
- HTTP Response Splitting
- XSS via injected headers
- Cache poisoning
- Session fixation
"""
import re
from typing import Dict
import sys
from pathlib import Path
from tests.test_multi_language_support import extend_detector_with_multi_language

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations


@extend_detector_with_multi_language
class HeaderInjectionDetector:
    """Detects HTTP header injection vulnerabilities in code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "python") -> Dict:
        """Analyze code for header injection vulnerabilities."""
        if language == "java":
            return self._analyze_java(code)
        elif language == "javascript":
            return self._analyze_javascript(code)
        elif language == "python":
            return self._analyze_python(code)
        elif language == "php":
            return self._analyze_php(code)

    def _analyze_java(self, code: str) -> Dict:
        """Analyze Java code for header injection."""
        self.vulnerabilities = []
        self.score = 2

        # Find response.setHeader() and response.addHeader() calls
        header_patterns = [
            r'response\.setHeader\s*\(',
            r'response\.addHeader\s*\(',
            r'httpResponse\.setHeader\s*\(',
            r'httpResponse\.addHeader\s*\(',
        ]

        header_locations = []
        for pattern in header_patterns:
            header_locations.extend(find_pattern_locations(code, pattern))

        if header_locations:
            # Check if header value comes from user input
            has_user_input = any([
                re.search(r'request\.getParameter\s*\(', code),
                re.search(r'request\.getHeader\s*\(', code),
                re.search(r'@PathVariable', code),
                re.search(r'@RequestParam', code),
                re.search(r'fileName\s*=', code) and re.search(r'setHeader.*fileName', code),  # Common pattern
            ])

            if has_user_input:
                # Check for sanitization (looking for \r or \n in the code)
                has_sanitization = any([
                    re.search(r'\.replace\s*\(\s*["\']\\r["\']', code),  # Replaces \r
                    re.search(r'\.replace\s*\(\s*["\']\\n["\']', code),  # Replaces \n
                    re.search(r'\.replaceAll\s*\(\s*["\'][^\'"]*\\r', code),  # Regex sanitization with \r
                    re.search(r'\.replaceAll\s*\(\s*["\'][^\'"]*\\n', code),  # Regex sanitization with \n
                    re.search(r'sanitize', code, re.IGNORECASE),
                    re.search(r'encode', code, re.IGNORECASE) and re.search(r'header', code, re.IGNORECASE),
                ])

                location = header_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                if not has_sanitization:
                    # VULNERABLE: User input in header without sanitization
                    self.vulnerabilities.append({
                        "type": "HEADER_INJECTION",
                        "severity": "HIGH",
                        "description": "HTTP Header Injection: User-controlled input placed directly in response header without CRLF sanitization. ATTACK: Attacker injects \\r\\n to split response, add malicious headers, or inject HTML/JavaScript. IMPACT: (1) XSS via Content-Type injection, (2) Cache poisoning, (3) Session fixation via Set-Cookie injection, (4) HTTP Response Splitting",
                        "recommendation": "Sanitize user input before placing in headers: fileName = fileName.replaceAll(\"[\\r\\n]\", \"\"); OR use safe header APIs that automatically encode special characters",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "User-controlled input (request parameter, path variable, header)",
                                "Input concatenated directly into response header value",
                                "No CRLF (\\r\\n) sanitization or encoding",
                                "Can inject arbitrary headers via newline characters"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: User input placed in response header without sanitization",
                                "Attacker can inject \\r\\n characters to split HTTP response",
                                "Example: filename='file.pdf\\r\\nContent-Type: text/html\\r\\n\\r\\n<script>alert(1)</script>'",
                                "Results in XSS, cache poisoning, or session hijacking",
                                "No validation or encoding of CRLF characters",
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "response.setHeader() / response.addHeader() with user input",
                                "User input sources (request.getParameter, @PathVariable, @RequestParam)",
                                "CRLF sanitization (.replace(\"\\r\"), .replace(\"\\n\"))",
                                "Header encoding or sanitization functions"
                            ],
                            "evidence": {
                                "found_patterns": ["response.setHeader() with unsanitized user input"],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    self.score = 0
                else:
                    # SECURE: Has sanitization
                    self.vulnerabilities.append({
                        "type": "SECURE",
                        "severity": "INFO",
                        "description": "SECURE: Response header uses user input but includes CRLF sanitization. Code removes \\r and \\n characters before placing input in headers, preventing HTTP Response Splitting attacks.",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "patterns_checked": [
                                "response.setHeader() with user input",
                                "CRLF sanitization present"
                            ],
                            "why_not_vulnerable": [
                                "Input sanitized to remove \\r and \\n characters",
                                "Cannot inject additional headers or split HTTP response",
                                "Safe to place in header value after sanitization"
                            ],
                            "vulnerable_patterns_absent": [
                                "No direct concatenation of unsanitized user input",
                                "CRLF characters removed before header assignment"
                            ]
                        }
                    })

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_javascript(self, code: str) -> Dict:
        """Analyze JavaScript/Node.js code for header injection."""
        self.vulnerabilities = []
        self.score = 2

        # Find res.setHeader(), res.header(), res.set() calls
        header_patterns = [
            r'res\.setHeader\s*\(',
            r'res\.header\s*\(',
            r'res\.set\s*\(',
            r'response\.setHeader\s*\(',
            r'response\.header\s*\(',
        ]

        header_locations = []
        for pattern in header_patterns:
            header_locations.extend(find_pattern_locations(code, pattern))

        if header_locations:
            # Check if header value comes from user input
            has_user_input = any([
                re.search(r'req\.(query|body|params|headers)', code),
                re.search(r'request\.(query|body|params)', code),
                re.search(r'fileName\s*=', code) and re.search(r'setHeader.*fileName', code),
                re.search(r'\$\{.*\}', code) and re.search(r'setHeader', code),  # Template literal
            ])

            if has_user_input:
                # Check for sanitization (JavaScript regex literals use / not quotes)
                has_sanitization = any([
                    re.search(r'\.replace\s*\(\s*/\\r/g', code),  # Replaces \r globally
                    re.search(r'\.replace\s*\(\s*/\\n/g', code),  # Replaces \n globally
                    re.search(r'\.replace\s*\(\s*/[^\s/]*\\r[^\s/]*/g', code),  # Regex with \r
                    re.search(r'\.replace\s*\(\s*/[^\s/]*\\n[^\s/]*/g', code),  # Regex with \n
                    re.search(r'sanitize', code, re.IGNORECASE),
                    re.search(r'encodeURI', code),
                ])

                location = header_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                if not has_sanitization:
                    # VULNERABLE
                    self.vulnerabilities.append({
                        "type": "HEADER_INJECTION",
                        "severity": "HIGH",
                        "description": "HTTP Header Injection: User input directly placed in response header without CRLF sanitization - VULNERABLE to Response Splitting. ATTACK: res.setHeader('Content-Disposition', `filename=\"${userInput}\"`) where userInput='file\\r\\nSet-Cookie: session=hijacked'. IMPACT: XSS via Content-Type, cache poisoning, session fixation, HTTP response splitting",
                        "recommendation": "Sanitize CRLF: const safe = fileName.replace(/[\\r\\n]/g, ''); res.setHeader('Content-Disposition', `filename=\"${safe}\"`);",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "User input from req.query, req.body, req.params, or req.headers",
                                "Input placed in res.setHeader() or res.header() without sanitization",
                                "No CRLF (\\r\\n) removal or encoding",
                                "Can inject headers via newline characters"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: User input in response header without CRLF sanitization",
                                "Attacker controls header value and can inject \\r\\n",
                                "Example: fileName='file.pdf\\r\\nContent-Type: text/html\\r\\n\\r\\n<script>alert(1)</script>'",
                                "Results in XSS, session hijacking, or cache poisoning",
                                "No validation to prevent response splitting"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "res.setHeader() / res.header() / res.set() with user input",
                                "User input from req.query, req.body, req.params",
                                "CRLF sanitization (.replace(/[\\r\\n]/g, ''))",
                                "URL encoding (encodeURI, encodeURIComponent)"
                            ],
                            "evidence": {
                                "found_patterns": ["res.setHeader() with unsanitized user input"],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    self.score = 0
                else:
                    # SECURE
                    self.vulnerabilities.append({
                        "type": "SECURE",
                        "severity": "INFO",
                        "description": "SECURE: Response header includes CRLF sanitization before using user input. The .replace(/[\\r\\n]/g, '') pattern removes newline characters, preventing HTTP Response Splitting.",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "patterns_checked": [
                                "res.setHeader() with user input",
                                "CRLF sanitization present"
                            ],
                            "why_not_vulnerable": [
                                "Removes \\r and \\n before placing in header",
                                "Cannot split HTTP response or inject headers",
                                "Safe after sanitization"
                            ],
                            "vulnerable_patterns_absent": [
                                "No unsanitized user input in headers"
                            ]
                        }
                    })

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python code for header injection."""
        self.vulnerabilities = []
        self.score = 2

        # Find response.headers[] assignments or response.set_header() calls
        header_patterns = [
            r'response\.headers\[',
            r'response\.set_header\(',
            r'\.headers\[',
            r'make_response',
        ]

        header_locations = []
        for pattern in header_patterns:
            header_locations.extend(find_pattern_locations(code, pattern))

        if header_locations:
            # Check if header value comes from user input
            has_user_input = any([
                re.search(r'request\.(args|form|values|headers)\.get', code),
                re.search(r'request\.(args|form|values)', code),
                re.search(r'filename\s*=', code) and re.search(r'headers.*filename', code, re.IGNORECASE),
                re.search(r'f["\'].*\{.*\}', code) and re.search(r'headers', code),  # f-string
            ])

            if has_user_input:
                # Check for sanitization
                has_sanitization = any([
                    re.search(r'\.replace\s*\(\s*["\']\\\\r["\']', code),
                    re.search(r'\.replace\s*\(\s*["\']\\\\n["\']', code),
                    re.search(r're\.sub\s*\(.*[\[\^]\\\\r\\\\n', code),
                    re.search(r'sanitize', code, re.IGNORECASE),
                    re.search(r'quote.*from.*urllib', code),  # URL encoding
                ])

                location = header_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                if not has_sanitization:
                    # VULNERABLE
                    self.vulnerabilities.append({
                        "type": "HEADER_INJECTION",
                        "severity": "HIGH",
                        "description": "HTTP Header Injection: User input placed in response header without CRLF sanitization - VULNERABLE to Response Splitting. ATTACK: response.headers['Content-Disposition'] = f'filename=\"{filename}\"' where filename='file\\r\\nSet-Cookie: admin=true'. IMPACT: XSS, cache poisoning, session fixation, HTTP response splitting",
                        "recommendation": "Sanitize CRLF: safe_filename = filename.replace('\\r', '').replace('\\n', ''); response.headers['Content-Disposition'] = f'filename=\"{safe_filename}\"'",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "User input from request.args, request.form, or request.values",
                                "Input placed in response.headers[] without sanitization",
                                "No CRLF removal or encoding",
                                "Can inject headers via \\r\\n"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: User input in header without CRLF sanitization",
                                "Attacker can inject \\r\\n to split HTTP response",
                                "Example: filename='file.pdf\\r\\nContent-Type: text/html\\r\\n\\r\\n<script>alert(1)</script>'",
                                "Results in XSS or session hijacking",
                                "No newline validation"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "response.headers[] assignment with user input",
                                "User input from request.args, request.form",
                                "CRLF sanitization (.replace('\\r', ''), .replace('\\n', ''))",
                                "URL encoding (urllib.parse.quote)"
                            ],
                            "evidence": {
                                "found_patterns": ["response.headers[] with unsanitized user input"],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    self.score = 0
                else:
                    # SECURE
                    self.vulnerabilities.append({
                        "type": "SECURE",
                        "severity": "INFO",
                        "description": "SECURE: Response header includes CRLF sanitization. Code removes \\r and \\n characters before header assignment, preventing HTTP Response Splitting.",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "patterns_checked": [
                                "response.headers[] with user input",
                                "CRLF sanitization present"
                            ],
                            "why_not_vulnerable": [
                                "Removes \\r and \\n before header assignment",
                                "Cannot inject headers or split response",
                                "Safe after sanitization"
                            ],
                            "vulnerable_patterns_absent": [
                                "No unsanitized user input in headers"
                            ]
                        }
                    })

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_php(self, code: str) -> Dict:
        """Analyze PHP code for header injection."""
        self.vulnerabilities = []
        self.score = 2

        # Find header() calls
        header_locations = find_pattern_locations(code, r'header\s*\(')

        if header_locations:
            # Check if header value comes from user input
            has_user_input = any([
                re.search(r'\$_GET\[', code),
                re.search(r'\$_POST\[', code),
                re.search(r'\$_REQUEST\[', code),
                re.search(r'\$request->get\(', code),
                re.search(r'\$request->input\(', code),
                re.search(r'header\s*\(.*\$', code),  # header() with variable
            ])

            if has_user_input:
                # Check for sanitization
                has_sanitization = any([
                    re.search(r'str_replace\s*\(\s*"\\\\r"', code),
                    re.search(r'str_replace\s*\(\s*"\\\\n"', code),
                    re.search(r'preg_replace\s*\(.*[\[\^]\\\\r\\\\n', code),
                    re.search(r'filter_var.*FILTER_SANITIZE', code),
                    re.search(r'sanitize', code, re.IGNORECASE),
                ])

                location = header_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                if not has_sanitization:
                    # VULNERABLE
                    self.vulnerabilities.append({
                        "type": "HEADER_INJECTION",
                        "severity": "HIGH",
                        "description": "HTTP Header Injection: User input directly in header() without CRLF sanitization - CRITICAL Response Splitting vulnerability. ATTACK: header('Content-Disposition: filename=\"' . $_GET['file'] . '\"'); with file=test.pdf%0D%0ASet-Cookie:+admin=true. IMPACT: Session fixation, XSS via Content-Type, cache poisoning, response splitting",
                        "recommendation": "Sanitize CRLF: $safe = str_replace(array(\"\\r\", \"\\n\"), '', $filename); header('Content-Disposition: filename=\"' . $safe . '\"');",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "User input from $_GET, $_POST, $_REQUEST, or $request->input()",
                                "Input concatenated into header() call without sanitization",
                                "No CRLF removal",
                                "Can inject headers via %0D%0A (%0D=\\r, %0A=\\n)"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: User input in header() without CRLF sanitization",
                                "Attacker can inject \\r\\n (%0D%0A in URL encoding)",
                                "Example: $_GET['file']='test.pdf\\r\\nSet-Cookie: session=hijacked'",
                                "Results in session fixation, XSS, or cache poisoning",
                                "No validation of newline characters"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "header() with user input ($_GET, $_POST, $request->input())",
                                "CRLF sanitization (str_replace, preg_replace)",
                                "Input filtering (filter_var FILTER_SANITIZE)"
                            ],
                            "evidence": {
                                "found_patterns": ["header() with unsanitized user input"],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    self.score = 0
                else:
                    # SECURE
                    self.vulnerabilities.append({
                        "type": "SECURE",
                        "severity": "INFO",
                        "description": "SECURE: header() call includes CRLF sanitization. Code removes \\r and \\n before header() call, preventing HTTP Response Splitting.",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "patterns_checked": [
                                "header() with user input",
                                "CRLF sanitization present"
                            ],
                            "why_not_vulnerable": [
                                "Removes \\r and \\n before header()",
                                "Cannot inject headers or split response",
                                "Safe after sanitization"
                            ],
                            "vulnerable_patterns_absent": [
                                "No unsanitized user input in header()"
                            ]
                        }
                    })

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


def test_java_vulnerable():
    """Test detection of header injection in Java."""
    vulnerable_code = '''
String fileName = request.getParameter("filename");
response.setHeader("Content-Disposition", "attachment; filename=\\"" + fileName + "\\"");
'''
    detector = HeaderInjectionDetector()
    result = detector.analyze(vulnerable_code, "java")
    assert result["score"] == 0, "Should detect header injection"


def test_java_secure():
    """Test detection of secure header handling in Java."""
    secure_code = '''
String fileName = request.getParameter("filename");
fileName = fileName.replaceAll("[\\r\\n]", "");
response.setHeader("Content-Disposition", "attachment; filename=\\"" + fileName + "\\"");
'''
    detector = HeaderInjectionDetector()
    result = detector.analyze(secure_code, "java")
    assert result["score"] == 2, "Should recognize secure header handling"


def test_javascript_vulnerable():
    """Test detection of header injection in JavaScript."""
    vulnerable_code = '''
const fileName = req.query.filename;
res.setHeader('Content-Disposition', `inline; filename="${fileName}"`);
'''
    detector = HeaderInjectionDetector()
    result = detector.analyze(vulnerable_code, "javascript")
    assert result["score"] == 0, "Should detect header injection"


def test_javascript_secure():
    """Test detection of secure header handling in JavaScript."""
    secure_code = '''
const fileName = req.query.filename.replace(/[\\r\\n]/g, '');
res.setHeader('Content-Disposition', `inline; filename="${fileName}"`);
'''
    detector = HeaderInjectionDetector()
    result = detector.analyze(secure_code, "javascript")
    assert result["score"] == 2, "Should recognize secure header handling"


if __name__ == "__main__":
    test_java_vulnerable()
    test_java_secure()
    test_javascript_vulnerable()
    test_javascript_secure()
    print("All HTTP Header Injection detection tests passed!")
