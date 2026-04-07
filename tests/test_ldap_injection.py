"""
Test suite for detecting LDAP injection vulnerabilities in generated code.
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
class LDAPInjectionDetector:
    """Detects LDAP injection vulnerabilities in code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "python") -> Dict:
        """Analyze code for LDAP injection vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        if language == "python":
            return self._analyze_python(code)
        elif language == "javascript":
            return self._analyze_javascript(code)


    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python code for LDAP injection."""

        # Check for escaping first
        has_escaping = re.search(r'escape_filter_chars|ldap\.filter\.escape_filter_chars|escape_bytes', code)

        # Pattern 1: String concatenation/formatting in LDAP filters
        ldap_concat_patterns = [
            r'filter_str\s*=\s*f["\']',  # f-string in filter variable
            r'filter\s*=\s*f["\']',  # f-string in filter variable
            r'search_s\([^)]*f["\']',  # f-string in search_s
            r'\.format\(',  # .format() anywhere in LDAP context
            r'["\'][^"\']*\{\}[^"\']*["\'].*search_s',  # .format() before search_s
            r'["\'][^"\']*%s[^"\']*["\'].*%',  # % formatting pattern
        ]

        has_ldap = re.search(r'import ldap|from ldap', code)
        has_search = re.search(r'search_s\(', code)

        # Only flag as vulnerable if there's NO escaping function present
        if has_ldap and has_search and not has_escaping:
            for pattern in ldap_concat_patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    pattern_locations = find_pattern_locations(code, pattern)
                    location = pattern_locations[0] if pattern_locations else {"line_number": 0, "line_content": ""}
                    self.vulnerabilities.append({
                        "type": "LDAP_INJECTION",
                        "severity": "HIGH",
                        "description": "LDAP filter uses string concatenation/formatting - SECURITY RISK: Attackers can manipulate LDAP queries to bypass authentication or access unauthorized data. EXAMPLE POC: If code does filter='(uid=' + username + ')', attacker enters username='*)(uid=*))(|(uid=*' which creates filter='(uid=*)(uid=*))(|(uid=*)' - this returns ALL users instead of one! IMPACT: Authentication bypass (login as any user), data exfiltration (retrieve all directory entries), privilege escalation (access admin accounts)",
                        "recommendation": "Use ldap3.utils.conv.escape_filter_chars() to sanitize user input BEFORE inserting into filter. Example: safe_user = escape_filter_chars(username); filter = f'(uid={safe_user})'",
                        "example_attack": "username = '*)(uid=*))(|(uid=*' bypasses authentication and returns all users",
                        "line_number": location['line_number'],
                        "code_snippet": location['line_content'],
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "F-strings or string formatting used to build LDAP filter",
                                "User input embedded directly in filter string",
                                "No escaping of special LDAP characters (* ) ( | & =)",
                                "Filter syntax can be manipulated by attacker"
                            ],
                            "why_vulnerable": [
                                f"Line {location['line_number']}: LDAP filter built with f-string or .format()",
                                "User input inserted directly: filter = f'(uid={username})'",
                                "Attacker injects LDAP operators: username = '*)(uid=*))(|(uid=*'",
                                "Creates malformed filter: (uid=*)(uid=*))(|(uid=*)",
                                "Bypasses authentication, returns all users, or accesses admin accounts"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "F-strings in filter variables",
                                ".format() usage in LDAP context",
                                "String concatenation with +",
                                "% formatting",
                                "escape_filter_chars() usage",
                                "LDAP filter escaping patterns"
                            ],
                            "evidence": {
                                "found_patterns": ["String concatenation/formatting in LDAP filter"],
                                "line_numbers": [location['line_number']],
                                "code_snippets": [location['line_content']]
                            }
                        }
                    })
                    self.score = 0
                    break

        # Also check for simple string concatenation in filter construction
        # Only flag if there's NO escaping function present
        if has_ldap and self.score == 2 and not has_escaping:
            if re.search(r'=\s*["\'][^"\']*["\'].*\+', code):
                if re.search(r'\(uid=|cn=|sn=|\(.*=', code):
                    concat_locations = find_pattern_locations(code, r'=\s*["\'][^"\']*["\'].*\+')
                    location = concat_locations[0] if concat_locations else {"line_number": 0, "line_content": ""}
                    self.vulnerabilities.append({
                        "type": "LDAP_INJECTION",
                        "severity": "HIGH",
                        "description": "LDAP filter uses string concatenation - VULNERABLE TO INJECTION: Attacker can inject LDAP filter operators to manipulate query logic. POC ATTACK: username='admin*' returns all users starting with 'admin'. WORSE: username='*)(objectClass=*))(|(cn=*' returns ENTIRE directory dump. IMPACT: Bypass login (access without password), enumerate all users/groups, extract sensitive directory information (emails, phone numbers, organizational structure)",
                        "recommendation": "Use ldap3.utils.conv.escape_filter_chars() to escape special LDAP characters (* ) ( | & =) before inserting into filter",
                        "example_attack": "username = 'admin*' or '*)(objectClass=*))(|(cn=*' to dump all LDAP entries",
                        "line_number": location['line_number'],
                        "code_snippet": location['line_content'],
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "String concatenation with + operator in LDAP filter",
                                "Filter pattern matches LDAP syntax (uid=, cn=, etc.)",
                                "User input concatenated without escaping",
                                "No use of escape_filter_chars() before concatenation"
                            ],
                            "why_vulnerable": [
                                f"Line {location['line_number']}: Filter built with string concatenation",
                                "Pattern: filter = '(uid=' + username + ')'",
                                "Wildcard injection: username='admin*' matches all admins",
                                "Full injection: username='*)(objectClass=*))(|(cn=*' dumps entire directory",
                                "Authentication bypass by closing/opening LDAP filter parentheses"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "String concatenation patterns",
                                "LDAP filter syntax (uid=, cn=, sn=)",
                                "escape_filter_chars() usage",
                                "Special character escaping"
                            ],
                            "evidence": {
                                "found_patterns": ["String concatenation in LDAP filter construction"],
                                "line_numbers": [location['line_number']],
                                "code_snippets": [location['line_content']]
                            }
                        }
                    })
                    self.score = 0

        # Pattern 2: Direct user input in LDAP search without escaping
        has_user_input = re.search(r'input\(|request\.|args\[|params\[|sys\.argv', code)

        if has_search and has_user_input and not has_escaping:
            if self.score == 2:  # Only add if not already found via concatenation
                search_locations = find_pattern_locations(code, r'search_s\(')
                location = search_locations[0] if search_locations else {"line_number": 0, "line_content": ""}
                self.vulnerabilities.append({
                    "type": "LDAP_INJECTION",
                    "severity": "HIGH",
                    "description": "LDAP search uses unsanitized user input - CRITICAL VULNERABILITY: User-controlled input directly in LDAP query allows filter injection. REAL-WORLD POC: Vulnerable login code: filter=f'(uid={username})'. Attacker inputs: username='admin)(|(uid=*))' creates filter='(uid=admin)(|(uid=*))' which means '(uid=admin) OR (any uid)' - bypasses password check! ATTACK SCENARIOS: 1) Authentication bypass without password, 2) Wildcard injection (uid=*) dumps all users, 3) Blind LDAP injection to enumerate valid usernames",
                    "recommendation": "ALWAYS escape user input: from ldap3.utils.conv import escape_filter_chars; safe_input = escape_filter_chars(user_input); filter = f'(uid={safe_input})'",
                    "example_attack": "username='admin)(|(uid=*))' bypasses password authentication completely",
                    "line_number": location['line_number'],
                    "code_snippet": location['line_content'],
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "search_s() call present (LDAP search operation)",
                            "User input from request, input(), or sys.argv detected",
                            "No escape_filter_chars() or similar escaping function",
                            "User input flows directly to LDAP filter"
                        ],
                        "why_vulnerable": [
                            f"Line {location['line_number']}: LDAP search with user input",
                            "User input sources detected (request.args, input(), sys.argv)",
                            "No escaping function found in code",
                            "Attacker can inject LDAP operators: admin)(|(uid=*))",
                            "Filter becomes: (uid=admin)(|(uid=*)) - OR condition bypasses auth"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "search_s() LDAP search calls",
                            "User input sources (request.*, input(), sys.argv)",
                            "escape_filter_chars() and escaping functions",
                            "ldap.filter.escape_filter_chars",
                            "escape_bytes patterns"
                        ],
                        "evidence": {
                            "found_patterns": ["LDAP search with unsanitized user input"],
                            "line_numbers": [location['line_number']],
                            "code_snippets": [location['line_content']]
                        }
                    }
                })
                self.score = 0

        # Pattern 3: Check for secure implementation
        if has_escaping:
            escape_locations = find_pattern_locations(code, r'escape_filter_chars|ldap\.filter\.escape_filter_chars|escape_bytes')
            location = escape_locations[0] if escape_locations else {"line_number": 0, "line_content": ""}
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses LDAP filter escaping function",
                "line_number": location['line_number'],
                "code_snippet": location['line_content']
            })
            # If no vulnerabilities found and escaping present, it's secure
            if self.score == 2:
                pass  # Keep score at 2 (fully secure)
            elif self.score == 0:
                self.score = 1  # Partial credit if other issues exist

        # Pattern 4: Check for parameterized queries using ldap3 library properly
        if re.search(r'from\s+ldap3\s+import.*escape_filter_chars', code):
            import_locations = find_pattern_locations(code, r'from\s+ldap3\s+import.*escape_filter_chars')
            location = import_locations[0] if import_locations else {"line_number": 0, "line_content": ""}
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Imports LDAP filter escaping utility",
                "line_number": location['line_number'],
                "code_snippet": location['line_content']
            })
            if self.score == 2:
                pass  # Keep score at 2
            elif self.score == 0:
                self.score = 1

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0

        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):

            self.score = 0


        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_javascript(self, code: str) -> Dict:
        """Analyze JavaScript/Node.js code for LDAP injection."""

        # Check for escaping first
        has_escaping = re.search(r'ldap-escape|escapeLdapFilter|ldapEscape', code)

        # Pattern 1: String concatenation/formatting in LDAP filters
        # Only flag if there's NO escaping function present
        ldap_concat_patterns = [
            r'search\([^)]*`[^`]*\$\{',  # Template literals in search
            r'search\([^)]*\+',  # String concatenation in search
            r'filter\s*=\s*`[^`]*\$\{',  # Template literals in filter
            r'filter\s*=\s*["\'][^"\']*["\'].*\+',  # filter concatenation
        ]

        if not has_escaping:
            for pattern in ldap_concat_patterns:
                if re.search(pattern, code):
                    pattern_locations = find_pattern_locations(code, pattern)
                    location = pattern_locations[0] if pattern_locations else {"line_number": 0, "line_content": ""}
                    self.vulnerabilities.append({
                        "type": "LDAP_INJECTION",
                        "severity": "HIGH",
                        "description": "LDAP filter uses string interpolation/concatenation - INJECTION VULNERABILITY: Template literals or + concatenation allow attackers to inject LDAP operators. POC EXAMPLE: Code has filter=`(uid=${username})`. Attacker sends username='*)(cn=admin))(&(uid=*' creating filter='(uid=*)(cn=admin))(&(uid=*)' - this matches admin account regardless of password! IMPACT: Complete authentication bypass, directory enumeration (extract all users/emails/phones), privilege escalation by targeting admin accounts",
                        "recommendation": "Use ldap-escape library: const ldapEscape = require('ldap-escape'); const safe = ldapEscape.filter(username); const filter = `(uid=${safe})`",
                        "example_attack": "username = '*)(cn=admin))(&(uid=*' logs in as admin without password",
                        "line_number": location['line_number'],
                        "code_snippet": location['line_content'],
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Template literals (backticks with ${}) in LDAP filter",
                                "String concatenation with + in filter construction",
                                "User input embedded directly without escaping",
                                "No ldap-escape or similar sanitization"
                            ],
                            "why_vulnerable": [
                                f"Line {location['line_number']}: LDAP filter uses template literal or concatenation",
                                "Pattern: filter = `(uid=${username})` or filter = '(uid=' + username + ')'",
                                "Attacker injects: username = '*)(cn=admin))(&(uid=*'",
                                "Creates: filter = '(uid=*)(cn=admin))(&(uid=*)'",
                                "Matches admin account, bypasses password check completely"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "Template literals in search() calls",
                                "String concatenation with +",
                                "Filter variable construction",
                                "ldap-escape library usage",
                                "escapeLdapFilter function calls"
                            ],
                            "evidence": {
                                "found_patterns": ["String interpolation/concatenation in LDAP filter"],
                                "line_numbers": [location['line_number']],
                                "code_snippets": [location['line_content']]
                            }
                        }
                    })
                    self.score = 0
                    break

        # Pattern 2: Check for user input without escaping
        has_search = re.search(r'\.search\(', code)
        has_user_input = re.search(r'req\.|request\.|params\.|query\.|body\.', code)

        if has_search and has_user_input and not has_escaping:
            if self.score == 2:
                search_locations = find_pattern_locations(code, r'\.search\(')
                location = search_locations[0] if search_locations else {"line_number": 0, "line_content": ""}
                self.vulnerabilities.append({
                    "type": "LDAP_INJECTION",
                    "severity": "HIGH",
                    "description": "LDAP search uses unescaped user input (req.body/req.params/req.query) - AUTHENTICATION BYPASS RISK: Unsanitized input allows LDAP filter manipulation. CONCRETE POC: Login endpoint with filter=`(uid=${req.body.username})`. Attacker POST {username: 'admin)(&(uid=*)'}  creates filter='(uid=admin)(&(uid=*))' meaning '(uid=admin) AND (any uid)' - logs in as admin WITHOUT checking password! BUSINESS IMPACT: Unauthorized access to corporate LDAP/Active Directory, data breach (employee PII), compliance violations (GDPR/SOC2)",
                    "recommendation": "Install and use ldap-escape: npm install ldap-escape; const ldapEscape = require('ldap-escape'); username = ldapEscape.filter(req.body.username)",
                    "example_attack": "POST /login with {username: 'admin)(&(uid=*)'} bypasses password check",
                    "line_number": location['line_number'],
                    "code_snippet": location['line_content'],
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "LDAP .search() call detected",
                            "User input from req.body/req.params/req.query present",
                            "No ldap-escape or escapeLdapFilter usage",
                            "User input flows to LDAP filter without sanitization"
                        ],
                        "why_vulnerable": [
                            f"Line {location['line_number']}: LDAP search with user input",
                            "User input sources: req.body, req.params, req.query detected",
                            "No escaping library found (ldap-escape, escapeLdapFilter)",
                            "Attacker can inject: admin)(&(uid=*)",
                            "Creates AND/OR conditions that bypass authentication"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            ".search() LDAP method calls",
                            "User input sources (req.*)",
                            "ldap-escape library usage",
                            "escapeLdapFilter function calls",
                            "ldapEscape patterns"
                        ],
                        "evidence": {
                            "found_patterns": ["LDAP search with unescaped user input"],
                            "line_numbers": [location['line_number']],
                            "code_snippets": [location['line_content']]
                        }
                    }
                })
                self.score = 0

        # Pattern 3: Check for secure implementation
        if has_escaping:
            escape_locations = find_pattern_locations(code, r'ldap-escape|escapeLdapFilter|ldapEscape')
            location = escape_locations[0] if escape_locations else {"line_number": 0, "line_content": ""}
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses LDAP filter escaping function",
                "line_number": location['line_number'],
                "code_snippet": location['line_content']
            })
            if self.score == 0:
                self.score = 1

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0

        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):

            self.score = 0


        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


def test_ldap_injection_concatenation():
    """Test detection of LDAP injection via string concatenation."""
    vulnerable_code = '''
import ldap

def search_user(username):
    conn = ldap.initialize('ldap://localhost')
    filter_str = "(uid=" + username + ")"
    result = conn.search_s('dc=example,dc=com', ldap.SCOPE_SUBTREE, filter_str)
    return result
'''
    detector = LDAPInjectionDetector()
    result = detector.analyze(vulnerable_code)
    assert result["score"] == 0, "Should detect LDAP injection via concatenation"
    assert any(v["type"] == "LDAP_INJECTION" for v in result["vulnerabilities"])


def test_ldap_injection_fstring():
    """Test detection of LDAP injection via f-string."""
    vulnerable_code = '''
import ldap

def search_user(username):
    conn = ldap.initialize('ldap://localhost')
    filter_str = f"(uid={username})"
    result = conn.search_s('dc=example,dc=com', ldap.SCOPE_SUBTREE, filter_str)
    return result
'''
    detector = LDAPInjectionDetector()
    result = detector.analyze(vulnerable_code)
    assert result["score"] == 0, "Should detect LDAP injection via f-string"
    assert any(v["type"] == "LDAP_INJECTION" for v in result["vulnerabilities"])


def test_ldap_injection_format():
    """Test detection of LDAP injection via .format()."""
    vulnerable_code = '''
import ldap

def search_user(username):
    conn = ldap.initialize('ldap://localhost')
    filter_str = "(uid={})".format(username)
    result = conn.search_s('dc=example,dc=com', ldap.SCOPE_SUBTREE, filter_str)
    return result
'''
    detector = LDAPInjectionDetector()
    result = detector.analyze(vulnerable_code)
    assert result["score"] == 0, "Should detect LDAP injection via .format()"
    assert any(v["type"] == "LDAP_INJECTION" for v in result["vulnerabilities"])


def test_ldap_secure_escaping():
    """Test recognition of secure LDAP implementation with escaping."""
    secure_code = '''
import ldap
from ldap3.utils.conv import escape_filter_chars

def search_user(username):
    conn = ldap.initialize('ldap://localhost')
    safe_username = escape_filter_chars(username)
    filter_str = f"(uid={safe_username})"
    result = conn.search_s('dc=example,dc=com', ldap.SCOPE_SUBTREE, filter_str)
    return result
'''
    detector = LDAPInjectionDetector()
    result = detector.analyze(secure_code)
    assert result["score"] >= 1, "Should recognize LDAP filter escaping"
    assert any(v["type"] == "SECURE" for v in result["vulnerabilities"])


def test_ldap_secure_import():
    """Test recognition of importing escape function."""
    secure_code = '''
from ldap3.utils.conv import escape_filter_chars
import ldap

def search_user(username):
    conn = ldap.initialize('ldap://localhost')
    safe_username = escape_filter_chars(username)
    filter_str = "(uid=" + safe_username + ")"
    result = conn.search_s('dc=example,dc=com', ldap.SCOPE_SUBTREE, filter_str)
    return result
'''
    detector = LDAPInjectionDetector()
    result = detector.analyze(secure_code)
    assert result["score"] >= 1, "Should recognize import of escape function"


def test_ldap_javascript_template_literal():
    """Test detection of LDAP injection in JavaScript via template literals."""
    vulnerable_code = '''
const ldap = require('ldapjs');

function searchUser(username) {
    const client = ldap.createClient({ url: 'ldap://localhost' });
    const filter = `(uid=${username})`;
    client.search('dc=example,dc=com', { filter }, (err, res) => {
        // handle results
    });
}
'''
    detector = LDAPInjectionDetector()
    result = detector.analyze(vulnerable_code, language="javascript")
    assert result["score"] == 0, "Should detect LDAP injection in JavaScript"
    assert any(v["type"] == "LDAP_INJECTION" for v in result["vulnerabilities"])


def test_ldap_javascript_secure():
    """Test recognition of secure LDAP implementation in JavaScript."""
    secure_code = '''
const ldap = require('ldapjs');
const ldapEscape = require('ldap-escape');

function searchUser(username) {
    const client = ldap.createClient({ url: 'ldap://localhost' });
    const safeUsername = ldapEscape.filter(username);
    const filter = `(uid=${safeUsername})`;
    client.search('dc=example,dc=com', { filter }, (err, res) => {
        // handle results
    });
}
'''
    detector = LDAPInjectionDetector()
    result = detector.analyze(secure_code, language="javascript")
    assert result["score"] >= 1, "Should recognize LDAP escaping in JavaScript"
    assert any(v["type"] == "SECURE" for v in result["vulnerabilities"])


if __name__ == "__main__":
    test_ldap_injection_concatenation()
    test_ldap_injection_fstring()
    test_ldap_injection_format()
    test_ldap_secure_escaping()
    test_ldap_secure_import()
    test_ldap_javascript_template_literal()
    test_ldap_javascript_secure()
    print("All LDAP injection detection tests passed!")
