"""
Test suite for detecting Open Redirect vulnerabilities.
"""
import re
from typing import Dict
import sys
from pathlib import Path

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations



class OpenRedirectDetector:
    """Detects Open Redirect vulnerabilities in code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "python") -> Dict:
        """Analyze code for Open Redirect vulnerabilities."""
        if language == "python":
            return self._analyze_python(code)
        elif language == "javascript":
            return self._analyze_javascript(code)
        else:
            return {"score": 0, "vulnerabilities": ["Unsupported language"], "max_score": 2}

    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python code for Open Redirect."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Redirect with user input
        redirect_patterns = [
            r'redirect\(',
            r'Response.*location=',
            r'HttpResponseRedirect\(',
            r'return.*redirect',
        ]

        # Find pattern locations
        redirect_locations = []
        for pattern in redirect_patterns:
            redirect_locations.extend(find_pattern_locations(code, pattern))

        uses_redirect = len(redirect_locations) > 0

        if uses_redirect:
            # Check if redirect URL comes from user input
            has_user_url = any([
                re.search(r'(request\.|params|args|form|query|body)\[?["\']?(next|url|redirect|return_to|return_url|destination)', code, re.IGNORECASE),
                re.search(r'redirect\([^)]*request\.', code),
                re.search(r'redirect\([^)]*\.get\(', code),  # redirect(request.args.get('next'))
                re.search(r'=\s*request\.(args|query|form|GET|POST|REQUEST)\.get\(', code),  # Variable from request (Django GET/POST)
                re.search(r'HttpResponseRedirect\([^)]*\w+\s*\)', code),  # HttpResponseRedirect(next_url) - check if variable passed
            ])

            if has_user_url:
                # Check for protections
                has_allowlist = any([
                    re.search(r'if.*url.*in\s+(ALLOWED|allowed|SAFE|safe|whitelist|WHITELIST)', code),
                    re.search(r'if.*url\.startswith\(["\']/', code),  # Relative URL check
                    re.search(r'if.*is_safe_url|if.*validate_redirect', code),
                    re.search(r'\.netloc.*not\s+in\s+(ALLOWED|allowed)', code),  # netloc not in ALLOWED_HOSTS
                    re.search(r'urlparse\(.*\)\.netloc', code) and re.search(r'if.*in\s+(ALLOWED|allowed)', code),  # netloc in ALLOWED_HOSTS
                ])

                has_domain_check = any([
                    re.search(r'\.netloc\s*==\s*["\'][^"\']+["\']', code),
                    re.search(r'if.*\.startswith\(["\']https?://[^"\']+["\']', code),
                ])

                has_relative_only = re.search(r'if.*\.startswith\(["\']/', code)

                # Use first location for reporting
                location = redirect_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                if not has_allowlist and not has_domain_check and not has_relative_only:
                    self.vulnerabilities.append({
                        "type": "OPEN_REDIRECT",
                        "severity": "MEDIUM",
                        "description": "Redirects to user-supplied URL without validation - PHISHING ATTACK RISK: Attacker tricks users by creating legitimate-looking URL (yoursite.com/login?next=http://evil.com) that redirects to attacker's fake login page. REAL-WORLD IMPACT: (1) Credential Theft: User logs into yoursite.com, clicks link, redirected to identical-looking evil.com, enters credentials → stolen. (2) OAuth Token Theft: Authorization flow redirects to attacker site with access token. (3) Malware Distribution: Redirect to malicious download. (4) Trust Exploitation: Users trust yoursite.com domain in URL, don't notice redirect destination",
                        "recommendation": "VALIDATE REDIRECT URLs: (1) Use allowlist of relative paths: if url not in ['/', '/dashboard', '/profile']: return error, (2) Validate as relative path only: if not url.startswith('/'): reject, (3) Django: use url_has_allowed_host_and_scheme(url, allowed_hosts=ALLOWED_HOSTS) or resolve_url(), (4) Check domain allowlist: parse URL and verify hostname in ALLOWED_HOSTS. NEVER redirect to arbitrary user-supplied URLs without validation.",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Open Redirect vulnerability occurs when user-supplied URLs are used in redirects without validation",
                                "Vulnerable patterns: redirect(request.args.get('next')), redirect(user_input) without checks",
                                "No allowlist, domain validation, or relative-only path checks present",
                                "Attackers can craft URLs that redirect victims to malicious sites while appearing legitimate"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: Redirect operation using user-supplied URL without validation",
                                "User input detected from: request.args, request.query, request.form, request.GET/POST",
                                "No allowlist validation: URL not checked against ALLOWED_HOSTS or safe URL list",
                                "No domain validation: URL hostname not verified",
                                "No relative path check: Not restricted to URLs starting with '/'",
                                "ATTACK: Attacker sends victim link: yoursite.com/login?next=http://evil.com/fake-login",
                                "ATTACK: User clicks link, logs into yoursite.com, automatically redirected to evil.com",
                                "ATTACK: User enters credentials on fake evil.com page thinking it's yoursite.com",
                                "IMPACT: Credential theft, OAuth token theft, malware distribution, phishing attacks"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "Redirect operations: redirect(), HttpResponseRedirect(), Response with location=",
                                "User input sources: request.args, request.query, request.form, request.GET/POST/REQUEST",
                                "Allowlist validation: if url in ALLOWED/SAFE/whitelist, if url.startswith('/')",
                                "Safe URL functions: is_safe_url(), validate_redirect()",
                                "Domain validation: urlparse().netloc checks, netloc in ALLOWED_HOSTS",
                                "Explicit domain checks: .netloc == 'example.com', .startswith('https://example.com')",
                                "Relative path validation: if url.startswith('/')"
                            ],
                            "evidence": {
                                "found_patterns": [
                                    f"Redirect operation at line {line_num}",
                                    "User input used in redirect URL",
                                    "No allowlist validation found",
                                    "No domain validation found",
                                    "No relative path restriction found"
                                ],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    self.score = 0
                elif has_domain_check or has_relative_only:
                    # Partial protection
                    self.vulnerabilities.append({
                        "type": "OPEN_REDIRECT",
                        "severity": "LOW",
                        "description": "Redirect has partial validation but could be bypassed - use strict allowlist",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Open Redirect with partial protection may still be exploitable",
                                "Domain checks or relative path validation present but not comprehensive",
                                "Bypass techniques may exist depending on implementation"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: Redirect operation with partial URL validation",
                                f"Has domain check: {has_domain_check}",
                                f"Has relative-only check: {has_relative_only}",
                                "Partial validation may be bypassed with crafted URLs",
                                "ATTACK: Depending on validation method, bypasses may be possible (e.g., //evil.com, https:evil.com, etc.)",
                                "IMPACT: Reduced risk but phishing attacks still possible in some cases"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "Redirect operations: redirect(), HttpResponseRedirect(), Response with location=",
                                "User input sources: request.args, request.query, request.form, request.GET/POST/REQUEST",
                                "Allowlist validation: if url in ALLOWED/SAFE/whitelist",
                                "Domain validation: .netloc == 'domain', .startswith('https://domain')",
                                "Relative path validation: if url.startswith('/')",
                                "Safe URL functions: is_safe_url(), validate_redirect()"
                            ],
                            "evidence": {
                                "found_patterns": [
                                    f"Redirect operation at line {line_num}",
                                    "User input used in redirect URL",
                                    "Partial validation found (domain or relative check)"
                                ],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    self.score = 1
                else:
                    # Has allowlist
                    self.vulnerabilities.append({
                        "type": "SECURE",
                        "severity": "INFO",
                        "description": "Uses URL allowlist for redirect protection",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Open Redirect vulnerability occurs when user-supplied URLs are used without validation",
                                "Secure redirects use strict allowlists of permitted URLs or domains",
                                "Allowlist validation prevents arbitrary redirects to attacker-controlled sites"
                            ],
                            "why_vulnerable": [],
                            "why_not_vulnerable": [
                                f"Line {line_num}: Redirect operation with proper allowlist validation",
                                "Found: URL checked against ALLOWED_HOSTS or safe URL list",
                                "Found: is_safe_url() or validate_redirect() function used",
                                "Found: urlparse().netloc verified against allowed domains",
                                "Redirect destination is restricted to pre-approved URLs/domains"
                            ],
                            "patterns_checked": [
                                "Redirect operations: redirect(), HttpResponseRedirect(), Response with location=",
                                "User input sources: request.args, request.query, request.form, request.GET/POST/REQUEST",
                                "Allowlist validation: if url in ALLOWED/SAFE/whitelist",
                                "Safe URL functions: is_safe_url(), validate_redirect()",
                                "Domain validation: urlparse().netloc checks, netloc in ALLOWED_HOSTS",
                                "Relative path validation: if url.startswith('/')"
                            ],
                            "evidence": {
                                "found_patterns": [
                                    f"Redirect operation at line {line_num}",
                                    "User input used in redirect URL",
                                    "Allowlist validation found"
                                ],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0

        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):

            self.score = 0


        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_javascript(self, code: str) -> Dict:
        """Analyze JavaScript code for Open Redirect."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Redirect with user input
        redirect_patterns = [
            r'window\.location\s*=',
            r'window\.location\.href\s*=',
            r'location\.replace\(',
            r'res\.redirect\(',
            r'response\.redirect\(',
        ]

        # Find pattern locations
        redirect_locations = []
        for pattern in redirect_patterns:
            redirect_locations.extend(find_pattern_locations(code, pattern))

        uses_redirect = len(redirect_locations) > 0

        if uses_redirect:
            # Check if redirect URL comes from user input
            has_user_url = any([
                re.search(r'req\.(query|body|params)\.(next|url|redirect|return_to)', code),
                re.search(r'location\s*=\s*req\.', code),
                re.search(r'redirect\([^)]*req\.', code),
                re.search(r'(location|redirect)\([^)]*\.\w+\(', code),  # Methods like .get()
            ])

            if has_user_url:
                # Check for protections
                has_allowlist = any([
                    re.search(r'if.*url.*\.includes|if.*ALLOWED.*\.includes', code),
                    re.search(r'if.*url\.startsWith\(["\']/', code),  # Relative URL check
                    re.search(r'if.*isValidRedirect|if.*isSafeUrl', code),
                    re.search(r'new URL\(.*\)\.hostname', code) and re.search(r'if.*===', code),  # Domain check
                ])

                has_domain_check = any([
                    re.search(r'\.hostname\s*===\s*["\'][^"\']+["\']', code),
                    re.search(r'if.*\.startsWith\(["\']https?://[^"\']+', code),
                ])

                has_relative_only = re.search(r'if.*\.startsWith\(["\']/', code)

                # Use first location for reporting
                location = redirect_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                if not has_allowlist and not has_domain_check and not has_relative_only:
                    self.vulnerabilities.append({
                        "type": "OPEN_REDIRECT",
                        "severity": "MEDIUM",
                        "description": "Redirects to user-supplied URL without validation - PHISHING ATTACK RISK: Attacker tricks users by creating legitimate-looking URL (yoursite.com/login?next=http://evil.com) that redirects to attacker's fake login page. REAL-WORLD IMPACT: (1) Credential Theft: User logs into yoursite.com, clicks link, redirected to identical-looking evil.com, enters credentials → stolen. (2) OAuth Token Theft: Authorization flow redirects to attacker site with access token. (3) Malware Distribution: Redirect to malicious download. (4) Trust Exploitation: Users trust yoursite.com domain in URL, don't notice redirect destination",
                        "recommendation": "VALIDATE REDIRECT URLs: (1) Use allowlist of relative paths: if url not in ['/', '/dashboard', '/profile']: return error, (2) Validate as relative path only: if not url.startswith('/'): reject, (3) Django: use url_has_allowed_host_and_scheme(url, allowed_hosts=ALLOWED_HOSTS) or resolve_url(), (4) Check domain allowlist: parse URL and verify hostname in ALLOWED_HOSTS. NEVER redirect to arbitrary user-supplied URLs without validation.",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Open Redirect vulnerability in JavaScript occurs when user-supplied URLs are used in redirects without validation",
                                "Vulnerable patterns: window.location = req.query.url, res.redirect(req.params.next) without checks",
                                "No allowlist, domain validation, or relative-only path checks present",
                                "Attackers can craft URLs that redirect victims to malicious sites while appearing legitimate"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: JavaScript redirect operation using user-supplied URL without validation",
                                "User input detected from: req.query, req.body, req.params (Express), or URL parameters",
                                "No allowlist validation: URL not checked against ALLOWED_HOSTS or safe URL list",
                                "No domain validation: URL hostname not verified",
                                "No relative path check: Not restricted to URLs starting with '/'",
                                "ATTACK: Attacker sends victim link: yoursite.com/login?redirect=http://evil.com/fake-login",
                                "ATTACK: User clicks link, logs into yoursite.com, res.redirect() or window.location sends to evil.com",
                                "ATTACK: User enters credentials on fake evil.com page thinking it's yoursite.com",
                                "IMPACT: Credential theft, OAuth token theft, malware distribution, phishing attacks"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "Redirect operations: window.location =, window.location.href =, location.replace(), res.redirect()",
                                "User input sources: req.query, req.body, req.params",
                                "Allowlist validation: if url.includes(ALLOWED), if ALLOWED.includes(url)",
                                "Safe URL functions: isValidRedirect(), isSafeUrl()",
                                "Domain validation: new URL().hostname checks, .hostname === 'example.com'",
                                "Explicit domain checks: .startsWith('https://example.com')",
                                "Relative path validation: if url.startsWith('/')"
                            ],
                            "evidence": {
                                "found_patterns": [
                                    f"JavaScript redirect operation at line {line_num}",
                                    "User input used in redirect URL",
                                    "No allowlist validation found",
                                    "No domain validation found",
                                    "No relative path restriction found"
                                ],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    self.score = 0
                elif has_domain_check or has_relative_only:
                    # Partial protection
                    self.vulnerabilities.append({
                        "type": "OPEN_REDIRECT",
                        "severity": "LOW",
                        "description": "Redirect has partial validation but could be bypassed - use strict allowlist",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Open Redirect in JavaScript with partial protection may still be exploitable",
                                "Domain checks or relative path validation present but not comprehensive",
                                "Bypass techniques may exist depending on implementation"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: JavaScript redirect operation with partial URL validation",
                                f"Has domain check: {has_domain_check}",
                                f"Has relative-only check: {has_relative_only}",
                                "Partial validation may be bypassed with crafted URLs",
                                "ATTACK: Depending on validation method, bypasses may be possible (e.g., //evil.com, https:evil.com, etc.)",
                                "IMPACT: Reduced risk but phishing attacks still possible in some cases"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "Redirect operations: window.location =, window.location.href =, location.replace(), res.redirect()",
                                "User input sources: req.query, req.body, req.params",
                                "Allowlist validation: if url.includes(ALLOWED), if ALLOWED.includes(url)",
                                "Domain validation: .hostname === 'domain', .startsWith('https://domain')",
                                "Relative path validation: if url.startsWith('/')",
                                "Safe URL functions: isValidRedirect(), isSafeUrl()"
                            ],
                            "evidence": {
                                "found_patterns": [
                                    f"JavaScript redirect operation at line {line_num}",
                                    "User input used in redirect URL",
                                    "Partial validation found (domain or relative check)"
                                ],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    self.score = 1
                else:
                    # Has allowlist
                    self.vulnerabilities.append({
                        "type": "SECURE",
                        "severity": "INFO",
                        "description": "Uses URL allowlist for redirect protection",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Open Redirect vulnerability in JavaScript occurs when user-supplied URLs are used without validation",
                                "Secure redirects use strict allowlists of permitted URLs or domains",
                                "Allowlist validation prevents arbitrary redirects to attacker-controlled sites"
                            ],
                            "why_vulnerable": [],
                            "why_not_vulnerable": [
                                f"Line {line_num}: JavaScript redirect operation with proper allowlist validation",
                                "Found: URL checked against ALLOWED_HOSTS or safe URL list using .includes()",
                                "Found: isValidRedirect() or isSafeUrl() function used",
                                "Found: new URL().hostname verified against allowed domains",
                                "Redirect destination is restricted to pre-approved URLs/domains"
                            ],
                            "patterns_checked": [
                                "Redirect operations: window.location =, window.location.href =, location.replace(), res.redirect()",
                                "User input sources: req.query, req.body, req.params",
                                "Allowlist validation: if url.includes(ALLOWED), if ALLOWED.includes(url)",
                                "Safe URL functions: isValidRedirect(), isSafeUrl()",
                                "Domain validation: new URL().hostname checks, .hostname === 'example.com'",
                                "Relative path validation: if url.startsWith('/')"
                            ],
                            "evidence": {
                                "found_patterns": [
                                    f"JavaScript redirect operation at line {line_num}",
                                    "User input used in redirect URL",
                                    "Allowlist validation found"
                                ],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0

        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):

            self.score = 0


        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


def test_redirect_python_vulnerable():
    """Test detection of Open Redirect in Python."""
    vulnerable_code = '''
from flask import Flask, redirect, request

app = Flask(__name__)

@app.route('/login')
def login():
    next_page = request.args.get('next')
    # Process login...
    return redirect(next_page or url_for('home'))
'''
    detector = OpenRedirectDetector()
    result = detector.analyze(vulnerable_code, "python")
    assert result["score"] == 0, "Should detect Open Redirect vulnerability"


def test_redirect_python_secure():
    """Test detection of secure redirect with allowlist."""
    secure_code = '''
from flask import Flask, redirect, request, url_for
from urllib.parse import urlparse

app = Flask(__name__)

ALLOWED_HOSTS = ['example.com', 'www.example.com']

@app.route('/login')
def login():
    next_page = request.args.get('next')

    if next_page:
        parsed = urlparse(next_page)
        if parsed.netloc and parsed.netloc not in ALLOWED_HOSTS:
            next_page = None

    return redirect(next_page or url_for('home'))
'''
    detector = OpenRedirectDetector()
    result = detector.analyze(secure_code, "python")
    assert result["score"] == 2, "Should recognize secure redirect"


def test_redirect_javascript_vulnerable():
    """Test detection of Open Redirect in JavaScript."""
    vulnerable_code = '''
app.get('/login', (req, res) => {
    const redirectUrl = req.query.redirect;
    // Process login...
    res.redirect(redirectUrl || '/home');
});
'''
    detector = OpenRedirectDetector()
    result = detector.analyze(vulnerable_code, "javascript")
    assert result["score"] == 0, "Should detect Open Redirect vulnerability"


def test_redirect_javascript_secure():
    """Test detection of secure redirect."""
    secure_code = '''
const ALLOWED_HOSTS = ['example.com'];

app.get('/login', (req, res) => {
    const redirectUrl = req.query.redirect;

    if (redirectUrl) {
        const urlObj = new URL(redirectUrl);
        if (!ALLOWED_HOSTS.includes(urlObj.hostname)) {
            redirectUrl = '/home';
        }
    }

    res.redirect(redirectUrl || '/home');
});
'''
    detector = OpenRedirectDetector()
    result = detector.analyze(secure_code, "javascript")
    assert result["score"] == 2, "Should recognize secure redirect"


if __name__ == "__main__":
    test_redirect_python_vulnerable()
    test_redirect_python_secure()
    test_redirect_javascript_vulnerable()
    test_redirect_javascript_secure()
    print("All Open Redirect detection tests passed!")
