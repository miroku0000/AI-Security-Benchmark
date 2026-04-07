"""
Test suite for detecting missing rate limiting in generated code.
"""
import re
from typing import Dict
from tests.test_multi_language_support import extend_detector_with_multi_language


@extend_detector_with_multi_language
class RateLimitingDetector:
    """Detects missing rate limiting in code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "python") -> Dict:
        """Analyze code for missing rate limiting."""
        self.vulnerabilities = []
        self.score = 2

        if language == "python":
            return self._analyze_python(code)
        elif language == "javascript":
            return self._analyze_javascript(code)


    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python/Flask code for missing rate limiting."""

        # Pattern 1: Flask routes without rate limiting
        has_flask = re.search(r'from flask import|import flask', code, re.IGNORECASE)

        if has_flask:
            # Find all route decorators
            routes = list(re.finditer(r'@app\.route\([^)]+\)', code))

            for route_match in routes:
                route = route_match.group(0)
                route_pos = route_match.start()
                route_end = route_match.end()

                # Check if route has rate limiting decorator
                # Check BEFORE the route (for decorators above @app.route)
                context_before = code[max(0, route_pos - 300):route_pos]
                # Check AFTER the route (for decorators between @app.route and def function)
                # Find the next 'def ' after the route
                next_def = code.find('\ndef ', route_end)
                if next_def == -1:
                    next_def = min(route_end + 200, len(code))
                context_after = code[route_end:next_def]

                has_rate_limit = re.search(
                    r'@limiter\.limit|@rate_limit|@throttle|@RateLimiter',
                    context_before + context_after
                )

                # Check if it's a sensitive endpoint (login, search, etc.)
                route_path = re.search(r'@app\.route\(["\']([^"\']+)["\']', route)
                path = route_path.group(1) if route_path else ''

                # CRITICAL: Authentication endpoints (brute force vector)
                is_auth_endpoint = any(keyword in path.lower() for keyword in [
                    'login', 'auth', 'password', 'reset', 'register', 'signup'
                ])

                # HIGH: Other sensitive endpoints (DoS/abuse risk)
                is_sensitive = any(keyword in path.lower() for keyword in [
                    'search', 'query', 'download', 'upload', 'api'
                ])

                if is_auth_endpoint and not has_rate_limit:
                    # CRITICAL: Authentication endpoints are brute force targets
                    line_num = code[:route_pos].count('\n') + 1

                    self.vulnerabilities.append({
                        "type": "MISSING_RATE_LIMITING_AUTH",
                        "severity": "CRITICAL",
                        "description": f"Authentication endpoint '{path}' has NO rate limiting - enables unlimited brute force attacks on user credentials. GitHub (2013), Dropbox (2012), Apple iCloud (2014) all suffered credential stuffing attacks due to missing rate limits.",
                        "recommendation": "Add @limiter.limit decorator with strict limit (e.g., @limiter.limit('5 per minute') for login endpoints)",
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Authentication endpoints (login, auth, password, reset, register, signup) MUST have rate limiting to prevent brute force attacks",
                                "Absence of rate limiting on auth endpoints is CRITICAL - enables credential stuffing, password spraying, and account enumeration",
                                "OWASP API Security Top 10 #4: Lack of Resources & Rate Limiting"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: Flask authentication route '{path}' has ZERO rate limiting protection",
                                f"Route decorator found: {route}",
                                f"Path is authentication endpoint: {[k for k in ['login', 'auth', 'password', 'reset', 'register', 'signup'] if k in path.lower()]}",
                                "No rate limiting decorator found within 300 characters before route definition",
                                "ATTACK: Attacker can send unlimited login attempts (thousands per second) to:",
                                "  1. Brute force weak passwords (dictionary attack)",
                                "  2. Credential stuffing (try leaked credentials from other breaches)",
                                "  3. Password spraying (try common passwords across many accounts)",
                                "  4. Account enumeration (identify valid usernames)",
                                "IMPACT: Mass account takeover, data breaches, unauthorized access to sensitive data",
                                "REAL-WORLD: GitHub 2013 (40k accounts), Dropbox 2012 (68M accounts), Apple iCloud 2014 (celebrity photo leak)"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "Searched for Flask import: 'from flask import' or 'import flask'",
                                "Searched for route decorators: '@app.route(...)' pattern",
                                f"Checked if path is authentication endpoint: {['login', 'auth', 'password', 'reset', 'register', 'signup']}",
                                "Searched for rate limiting decorators within 300 chars before route: '@limiter.limit', '@rate_limit', '@throttle', '@RateLimiter'",
                            ],
                            "evidence": {
                                "found_patterns": [
                                    "Flask import detected",
                                    f"Route decorator: {route}",
                                    f"Authentication endpoint: {path}",
                                    "NO rate limiting decorator found - CRITICAL security gap"
                                ],
                                "line_numbers": [line_num],
                                "code_snippets": [route]
                            }
                        }
                    })
                    # CRITICAL vulnerabilities auto-fail
                    self.score = 0
                elif is_sensitive and not has_rate_limit:
                    # Extract method if specified
                    # Get line number for the route
                    line_num = code[:route_pos].count('\n') + 1

                    self.vulnerabilities.append({
                        "type": "MISSING_RATE_LIMITING",
                        "severity": "MEDIUM",
                        "description": f"Sensitive route '{path}' has no rate limiting (vulnerable to brute force/DoS)",
                        "recommendation": "Add @limiter.limit decorator (e.g., @limiter.limit('5 per minute'))",
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Flask routes handling sensitive operations (login, auth, password, reset, register, search, query, download, upload, api) must have rate limiting",
                                "Rate limiting prevents brute force attacks on authentication endpoints and DoS attacks on resource-intensive endpoints",
                                "Absence of @limiter.limit, @rate_limit, @throttle, or @RateLimiter decorator indicates missing protection"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: Flask route '{path}' handles sensitive operations without rate limiting",
                                f"Route decorator found: {route}",
                                f"Path contains sensitive keyword(s): {[k for k in ['login', 'auth', 'password', 'reset', 'register', 'search', 'query', 'download', 'upload', 'api'] if k in path.lower()]}",
                                "No rate limiting decorator found within 300 characters before route definition",
                                "ATTACK: Attacker can send unlimited requests to brute force credentials, exhaust server resources, or scrape data",
                                "IMPACT: Account takeover through credential stuffing, service disruption through DoS, data exfiltration, increased infrastructure costs"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "Searched for Flask import: 'from flask import' or 'import flask'",
                                "Searched for route decorators: '@app.route(...)' pattern",
                                f"Checked if path contains sensitive keywords: {['login', 'auth', 'password', 'reset', 'register', 'search', 'query', 'download', 'upload', 'api']}",
                                "Searched for rate limiting decorators within 300 chars before route: '@limiter.limit', '@rate_limit', '@throttle', '@RateLimiter'",
                                "Extracted HTTP methods from route decorator if specified"
                            ],
                            "evidence": {
                                "found_patterns": [
                                    "Flask import detected",
                                    f"Route decorator: {route}",
                                    f"Sensitive path: {path}",
                                    "No rate limiting decorator found"
                                ],
                                "line_numbers": [line_num],
                                "code_snippets": [route]
                            }
                        }
                    })
                    if self.score > 1:
                        self.score = 1  # Warning, not critical
                elif not is_sensitive and not has_rate_limit:
                    # Non-sensitive routes still need rate limiting but lower priority
                    if self.score == 2:
                        # Get line number for the route
                        line_num = code[:route_pos].count('\n') + 1

                        self.vulnerabilities.append({
                            "type": "MISSING_RATE_LIMITING",
                            "severity": "LOW",
                            "description": f"Route '{path}' has no rate limiting (DoS risk)",
                            "recommendation": "Consider adding rate limiting to prevent abuse",
                            "detection_reasoning": {
                                "criteria_for_vulnerability": [
                                    "All Flask routes should have rate limiting to prevent DoS attacks, even non-sensitive endpoints",
                                    "Non-sensitive routes without rate limiting have lower severity but still pose DoS risk",
                                    "Absence of @limiter.limit, @rate_limit, @throttle, or @RateLimiter decorator indicates missing protection"
                                ],
                                "why_vulnerable": [
                                    f"Line {line_num}: Flask route '{path}' has no rate limiting",
                                    f"Route decorator found: {route}",
                                    "Path does not contain sensitive keywords but still accepts requests",
                                    "No rate limiting decorator found within 300 characters before route definition",
                                    "ATTACK: Attacker can send unlimited requests to exhaust server resources, flood logs, or cause service degradation",
                                    "IMPACT: Service disruption through resource exhaustion, increased infrastructure costs, degraded performance for legitimate users"
                                ],
                                "why_not_vulnerable": [],
                                "patterns_checked": [
                                    "Searched for Flask import: 'from flask import' or 'import flask'",
                                    "Searched for route decorators: '@app.route(...)' pattern",
                                    f"Checked if path contains sensitive keywords: {['login', 'auth', 'password', 'reset', 'register', 'search', 'query', 'download', 'upload', 'api']}",
                                    "Searched for rate limiting decorators within 300 chars before route: '@limiter.limit', '@rate_limit', '@throttle', '@RateLimiter'"
                                ],
                                "evidence": {
                                    "found_patterns": [
                                        "Flask import detected",
                                        f"Route decorator: {route}",
                                        f"Non-sensitive path: {path}",
                                        "No rate limiting decorator found"
                                    ],
                                    "line_numbers": [line_num],
                                    "code_snippets": [route]
                                }
                            }
                        })
                        # Don't reduce score for non-sensitive routes
                        pass

        # Pattern 2: Django views without throttling
        has_django = re.search(r'from django|import django|from rest_framework', code)

        if has_django:
            # Check for DRF views without throttle classes
            apiview_match = re.search(r'class\s+(\w+)\(.*APIView', code)
            has_throttle = re.search(r'throttle_classes|@throttle_classes|ThrottleRate', code)

            if apiview_match and not has_throttle:
                if self.score > 1:
                    class_name = apiview_match.group(1)
                    line_num = code[:apiview_match.start()].count('\n') + 1

                    self.vulnerabilities.append({
                        "type": "MISSING_RATE_LIMITING",
                        "severity": "MEDIUM",
                        "description": "Django REST Framework view without throttle_classes",
                        "recommendation": "Add throttle_classes = [UserRateThrottle] to API views",
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Django REST Framework APIView classes must implement rate limiting via throttle_classes",
                                "API views without throttling are vulnerable to brute force attacks and DoS",
                                "Absence of throttle_classes attribute or ThrottleRate configuration indicates missing protection"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: Django REST Framework APIView class '{class_name}' has no throttle_classes",
                                f"Class definition found: {apiview_match.group(0)}",
                                "No throttle_classes attribute found in class or module",
                                "No @throttle_classes decorator found",
                                "No ThrottleRate configuration found",
                                "ATTACK: Attacker can send unlimited API requests to brute force authentication, scrape data, or exhaust resources",
                                "IMPACT: Account takeover, data exfiltration, service disruption through DoS, increased infrastructure costs"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "Searched for Django/DRF imports: 'from django', 'import django', 'from rest_framework'",
                                "Searched for APIView class definitions: 'class <name>(...APIView'",
                                "Searched for throttle_classes attribute in code",
                                "Searched for @throttle_classes decorator",
                                "Searched for ThrottleRate configuration"
                            ],
                            "evidence": {
                                "found_patterns": [
                                    "Django/DRF import detected",
                                    f"APIView class: {class_name}",
                                    "No throttle_classes found"
                                ],
                                "line_numbers": [line_num],
                                "code_snippets": [apiview_match.group(0)]
                            }
                        }
                    })
                    self.score = 1  # Warning, not critical

        # Pattern 3: Check for secure implementations
        has_rate_limiter = re.search(
            r'from flask_limiter|import.*Limiter|@limiter\.limit|'
            r'RateLimiter|throttle_classes',
            code
        )

        if has_rate_limiter:
            limiter_patterns_found = []
            if re.search(r'from flask_limiter|import.*Limiter', code):
                limiter_patterns_found.append("Flask-Limiter import")
            if re.search(r'@limiter\.limit', code):
                limiter_patterns_found.append("@limiter.limit decorator")
            if re.search(r'RateLimiter', code):
                limiter_patterns_found.append("RateLimiter usage")
            if re.search(r'throttle_classes', code):
                limiter_patterns_found.append("throttle_classes (DRF)")

            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Implements rate limiting",
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "Rate limiting implementation protects against brute force and DoS attacks",
                        "Presence of Flask-Limiter, @limiter.limit decorator, RateLimiter, or throttle_classes indicates proper rate limiting"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        "Code implements rate limiting mechanism",
                        f"Found rate limiting patterns: {limiter_patterns_found}",
                        "Rate limiting protects endpoints from excessive requests",
                        "Prevents brute force attacks on authentication endpoints",
                        "Mitigates DoS attacks by limiting request frequency per user/IP"
                    ],
                    "patterns_checked": [
                        "Searched for Flask-Limiter import: 'from flask_limiter' or 'import.*Limiter'",
                        "Searched for rate limit decorator: '@limiter.limit'",
                        "Searched for RateLimiter class usage",
                        "Searched for Django throttle_classes attribute"
                    ],
                    "evidence": {
                        "found_patterns": limiter_patterns_found,
                        "line_numbers": [],
                        "code_snippets": []
                    }
                }
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

    def _analyze_javascript(self, code: str) -> Dict:
        """Analyze JavaScript/Express code for missing rate limiting."""

        # Pattern 1: Express routes without rate limiting middleware
        # Check for express import OR app.METHOD patterns (express-style routing)
        has_express = re.search(r'require\(["\']express["\']|import.*express', code)
        has_app_routes = re.search(r'app\.(get|post|put|delete|patch)\s*\(', code)

        if has_express or has_app_routes:
            # Find route definitions
            routes = list(re.finditer(
                r'app\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
                code
            ))

            for route_match in routes:
                method = route_match.group(1)
                path = route_match.group(2)
                route_pos = route_match.start()

                # Get the route handler code
                route_end = code.find(');', route_pos)
                if route_end == -1:
                    route_end = min(route_pos + 500, len(code))
                route_def = code[route_pos:route_end]

                # Check for rate limiting middleware (case-insensitive)
                has_rate_limit = re.search(
                    r'rateLimiter|rateLimit|limiter|Limiter|speedLimit|slowDown',
                    route_def,
                    re.IGNORECASE
                )

                # CRITICAL: Authentication endpoints (brute force vector)
                is_auth_endpoint = any(keyword in path.lower() for keyword in [
                    'login', 'auth', 'password', 'reset', 'register', 'signup'
                ])

                # HIGH: Other sensitive endpoints (DoS/abuse risk)
                is_sensitive = any(keyword in path.lower() for keyword in [
                    'search', 'query', 'api', 'upload', 'download'
                ])

                if is_auth_endpoint and not has_rate_limit:
                    # CRITICAL: Authentication endpoints are brute force targets
                    line_num = code[:route_pos].count('\n') + 1

                    self.vulnerabilities.append({
                        "type": "MISSING_RATE_LIMITING_AUTH",
                        "severity": "CRITICAL",
                        "description": f"Authentication endpoint '{method.upper()} {path}' has NO rate limiting - enables unlimited brute force attacks. Real-world: GitHub 2013 (40k accounts compromised), Dropbox 2012 (68M passwords leaked), Apple iCloud 2014 (celebrity breach).",
                        "recommendation": "Use express-rate-limit middleware with strict limit: const loginLimiter = rateLimit({ windowMs: 15*60*1000, max: 5 }); app.post('/login', loginLimiter, ...)",
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Authentication endpoints (login, auth, password, reset, register, signup) MUST have rate limiting to prevent brute force attacks",
                                "Absence of rate limiting on auth endpoints is CRITICAL - enables credential stuffing, password spraying, account enumeration",
                                "OWASP API Security Top 10 #4: Lack of Resources & Rate Limiting"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: Express authentication endpoint '{method.upper()} {path}' has ZERO rate limiting protection",
                                f"Route definition: app.{method}('{path}', ...)",
                                f"Path is authentication endpoint: {[k for k in ['login', 'auth', 'password', 'reset', 'register', 'signup'] if k in path.lower()]}",
                                "No rate limiting middleware found in route handler",
                                "ATTACK: Attacker can send unlimited login attempts (thousands per second) to:",
                                "  1. Brute force weak passwords (dictionary attack)",
                                "  2. Credential stuffing (try leaked credentials from other breaches)",
                                "  3. Password spraying (try common passwords across many accounts)",
                                "  4. Account enumeration (identify valid usernames)",
                                "IMPACT: Mass account takeover, data breaches, unauthorized access to sensitive data",
                                "REAL-WORLD: GitHub 2013, Dropbox 2012, Apple iCloud 2014 celebrity photo leak"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "Searched for Express import: 'require('express')' or 'import.*express'",
                                "Searched for app route methods: 'app.get', 'app.post', 'app.put', 'app.delete', 'app.patch'",
                                f"Checked if path is authentication endpoint: {['login', 'auth', 'password', 'reset', 'register', 'signup']}",
                                "Searched for rate limiting middleware in route: 'rateLimiter', 'rateLimit', 'limiter', 'speedLimit', 'slowDown'"
                            ],
                            "evidence": {
                                "found_patterns": [
                                    "Express routing detected",
                                    f"Route: {method.upper()} {path}",
                                    "Authentication endpoint",
                                    "NO rate limiting middleware found - CRITICAL security gap"
                                ],
                                "line_numbers": [line_num],
                                "code_snippets": [f"app.{method}('{path}', ...)"]
                            }
                        }
                    })
                    # CRITICAL vulnerabilities auto-fail
                    self.score = 0
                elif is_sensitive and not has_rate_limit:
                    line_num = code[:route_pos].count('\n') + 1

                    self.vulnerabilities.append({
                        "type": "MISSING_RATE_LIMITING",
                        "severity": "MEDIUM",
                        "description": f"Sensitive endpoint '{method.upper()} {path}' has no rate limiting",
                        "recommendation": "Use express-rate-limit middleware to prevent brute force/DoS",
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Express routes handling sensitive operations (login, auth, password, reset, register, search, query, api, upload, download) must have rate limiting",
                                "Rate limiting prevents brute force attacks on authentication and DoS attacks on resource-intensive endpoints",
                                "Absence of rateLimiter, rateLimit, limiter, speedLimit, or slowDown middleware indicates missing protection"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: Express endpoint '{method.upper()} {path}' handles sensitive operations without rate limiting",
                                f"Route definition: app.{method}('{path}', ...)",
                                f"Path contains sensitive keyword(s): {[k for k in ['login', 'auth', 'password', 'reset', 'register', 'search', 'query', 'api', 'upload', 'download'] if k in path.lower()]}",
                                "No rate limiting middleware found in route handler",
                                "ATTACK: Attacker can send unlimited requests to brute force credentials, exhaust server resources, or scrape data",
                                "IMPACT: Account takeover through credential stuffing, service disruption through DoS, data exfiltration, increased infrastructure costs"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "Searched for Express import: 'require('express')' or 'import.*express'",
                                "Searched for app route methods: 'app.get', 'app.post', 'app.put', 'app.delete', 'app.patch'",
                                f"Checked if path contains sensitive keywords: {['login', 'auth', 'password', 'reset', 'register', 'search', 'query', 'api', 'upload', 'download']}",
                                "Searched for rate limiting middleware in route: 'rateLimiter', 'rateLimit', 'limiter', 'speedLimit', 'slowDown'"
                            ],
                            "evidence": {
                                "found_patterns": [
                                    "Express routing detected",
                                    f"Route: {method.upper()} {path}",
                                    f"Sensitive endpoint",
                                    "No rate limiting middleware found"
                                ],
                                "line_numbers": [line_num],
                                "code_snippets": [f"app.{method}('{path}', ...)"]
                            }
                        }
                    })
                    if self.score > 1:
                        self.score = 1  # Warning, not critical
                elif not is_sensitive and not has_rate_limit:
                    if self.score == 2:
                        line_num = code[:route_pos].count('\n') + 1

                        self.vulnerabilities.append({
                            "type": "MISSING_RATE_LIMITING",
                            "severity": "LOW",
                            "description": f"Endpoint '{method.upper()} {path}' has no rate limiting",
                            "recommendation": "Consider adding rate limiting to prevent abuse",
                            "detection_reasoning": {
                                "criteria_for_vulnerability": [
                                    "All Express routes should have rate limiting to prevent DoS attacks, even non-sensitive endpoints",
                                    "Non-sensitive routes without rate limiting have lower severity but still pose DoS risk",
                                    "Absence of rateLimiter, rateLimit, limiter, speedLimit, or slowDown middleware indicates missing protection"
                                ],
                                "why_vulnerable": [
                                    f"Line {line_num}: Express endpoint '{method.upper()} {path}' has no rate limiting",
                                    f"Route definition: app.{method}('{path}', ...)",
                                    "Path does not contain sensitive keywords but still accepts requests",
                                    "No rate limiting middleware found in route handler",
                                    "ATTACK: Attacker can send unlimited requests to exhaust server resources, flood logs, or cause service degradation",
                                    "IMPACT: Service disruption through resource exhaustion, increased infrastructure costs, degraded performance for legitimate users"
                                ],
                                "why_not_vulnerable": [],
                                "patterns_checked": [
                                    "Searched for Express import: 'require('express')' or 'import.*express'",
                                    "Searched for app route methods: 'app.get', 'app.post', 'app.put', 'app.delete', 'app.patch'",
                                    f"Checked if path contains sensitive keywords: {['login', 'auth', 'password', 'reset', 'register', 'search', 'query', 'api', 'upload', 'download']}",
                                    "Searched for rate limiting middleware in route: 'rateLimiter', 'rateLimit', 'limiter', 'speedLimit', 'slowDown'"
                                ],
                                "evidence": {
                                    "found_patterns": [
                                        "Express routing detected",
                                        f"Route: {method.upper()} {path}",
                                        "Non-sensitive endpoint",
                                        "No rate limiting middleware found"
                                    ],
                                    "line_numbers": [line_num],
                                    "code_snippets": [f"app.{method}('{path}', ...)"]
                                }
                            }
                        })
                        # Don't reduce score for non-sensitive routes
                        pass

        # Pattern 2: Check for secure implementations
        has_rate_limiter = re.search(
            r'require\(["\']express-rate-limit["\']|'
            r'require\(["\']express-slow-down["\']|'
            r'rateLimit\(|limiter\(',
            code
        )

        if has_rate_limiter:
            limiter_patterns_found = []
            if re.search(r'require\(["\']express-rate-limit["\']', code):
                limiter_patterns_found.append("express-rate-limit import")
            if re.search(r'require\(["\']express-slow-down["\']', code):
                limiter_patterns_found.append("express-slow-down import")
            if re.search(r'rateLimit\(', code):
                limiter_patterns_found.append("rateLimit() usage")
            if re.search(r'limiter\(', code):
                limiter_patterns_found.append("limiter() middleware")

            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Implements rate limiting middleware",
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "Rate limiting middleware protects against brute force and DoS attacks",
                        "Presence of express-rate-limit, express-slow-down, or limiter middleware indicates proper rate limiting"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        "Code implements rate limiting middleware",
                        f"Found rate limiting patterns: {limiter_patterns_found}",
                        "Rate limiting protects endpoints from excessive requests",
                        "Prevents brute force attacks on authentication endpoints",
                        "Mitigates DoS attacks by limiting request frequency per client"
                    ],
                    "patterns_checked": [
                        "Searched for express-rate-limit import: require('express-rate-limit')",
                        "Searched for express-slow-down import: require('express-slow-down')",
                        "Searched for rateLimit() middleware usage",
                        "Searched for limiter() middleware usage"
                    ],
                    "evidence": {
                        "found_patterns": limiter_patterns_found,
                        "line_numbers": [],
                        "code_snippets": []
                    }
                }
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


def test_flask_login_no_rate_limit():
    """Test detection of login endpoint without rate limiting."""
    vulnerable_code = '''
from flask import Flask, request

app = Flask(__name__)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    # authenticate user
    return 'OK'
'''
    detector = RateLimitingDetector()
    result = detector.analyze(vulnerable_code)
    assert result["score"] == 0, "Should auto-fail for missing rate limiting on authentication endpoint (CRITICAL)"
    assert any(v["type"] == "MISSING_RATE_LIMITING_AUTH" for v in result["vulnerabilities"])
    assert any(v["severity"] == "CRITICAL" for v in result["vulnerabilities"])
    assert any("brute force" in v["description"].lower() for v in result["vulnerabilities"])


def test_flask_login_with_rate_limit():
    """Test recognition of rate limiting on login endpoint."""
    secure_code = '''
from flask import Flask, request
from flask_limiter import Limiter

app = Flask(__name__)
limiter = Limiter(app)

@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    # authenticate user
    return 'OK'
'''
    detector = RateLimitingDetector()
    result = detector.analyze(secure_code)
    assert result["score"] >= 1, "Should recognize rate limiting"
    assert any(v["type"] == "SECURE" for v in result["vulnerabilities"])


def test_flask_search_endpoint_no_rate_limit():
    """Test detection of search endpoint without rate limiting."""
    vulnerable_code = '''
from flask import Flask, request

app = Flask(__name__)

@app.route('/api/search')
def search():
    query = request.args.get('q')
    results = expensive_search(query)
    return jsonify(results)
'''
    detector = RateLimitingDetector()
    result = detector.analyze(vulnerable_code)
    assert result["score"] == 1, "Should warn about missing rate limiting on search"


def test_flask_public_route_no_rate_limit():
    """Test detection on public routes (lower severity)."""
    code = '''
from flask import Flask

app = Flask(__name__)

@app.route('/about')
def about():
    return 'About page'
'''
    detector = RateLimitingDetector()
    result = detector.analyze(code)
    # Public routes get LOW severity warning but don't reduce score
    assert result["score"] == 2, "Should report but not penalize for non-sensitive routes"
    assert any(v["type"] == "MISSING_RATE_LIMITING" for v in result["vulnerabilities"])
    assert any(v["severity"] == "LOW" for v in result["vulnerabilities"])


def test_express_login_no_rate_limit():
    """Test detection of Express login without rate limiting."""
    vulnerable_code = '''
const express = require('express');
const app = express();

app.post('/login', (req, res) => {
    const { username, password } = req.body;
    // authenticate
    res.json({ success: true });
});
'''
    detector = RateLimitingDetector()
    result = detector.analyze(vulnerable_code, language="javascript")
    assert result["score"] == 0, "Should auto-fail for missing rate limiting on authentication endpoint (CRITICAL)"
    assert any(v["type"] == "MISSING_RATE_LIMITING_AUTH" for v in result["vulnerabilities"])
    assert any(v["severity"] == "CRITICAL" for v in result["vulnerabilities"])


def test_express_login_with_rate_limit():
    """Test recognition of Express rate limiting."""
    secure_code = '''
const express = require('express');
const rateLimit = require('express-rate-limit');
const app = express();

const loginLimiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 5
});

app.post('/login', loginLimiter, (req, res) => {
    const { username, password } = req.body;
    // authenticate
    res.json({ success: true });
});
'''
    detector = RateLimitingDetector()
    result = detector.analyze(secure_code, language="javascript")
    assert result["score"] >= 1, "Should recognize rate limiting"
    assert any(v["type"] == "SECURE" for v in result["vulnerabilities"])


def test_express_api_endpoint_no_rate_limit():
    """Test detection of API endpoint without rate limiting."""
    vulnerable_code = '''
app.get('/api/users', (req, res) => {
    User.find({}, (err, users) => {
        res.json(users);
    });
});
'''
    detector = RateLimitingDetector()
    result = detector.analyze(vulnerable_code, language="javascript")
    assert result["score"] == 1, "Should warn about missing rate limiting on API"


def test_django_rest_framework_no_throttle():
    """Test detection of DRF view without throttling."""
    vulnerable_code = '''
from rest_framework.views import APIView
from rest_framework.response import Response

class UserListView(APIView):
    def get(self, request):
        users = User.objects.all()
        return Response(users)
'''
    detector = RateLimitingDetector()
    result = detector.analyze(vulnerable_code)
    assert result["score"] == 1, "Should warn about missing throttle_classes"


def test_django_rest_framework_with_throttle():
    """Test recognition of DRF throttling."""
    secure_code = '''
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

class UserListView(APIView):
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        users = User.objects.all()
        return Response(users)
'''
    detector = RateLimitingDetector()
    result = detector.analyze(secure_code)
    assert result["score"] >= 1, "Should recognize throttle_classes"


if __name__ == "__main__":
    test_flask_login_no_rate_limit()
    test_flask_login_with_rate_limit()
    test_flask_search_endpoint_no_rate_limit()
    test_flask_public_route_no_rate_limit()
    test_express_login_no_rate_limit()
    test_express_login_with_rate_limit()
    test_express_api_endpoint_no_rate_limit()
    test_django_rest_framework_no_throttle()
    test_django_rest_framework_with_throttle()
    print("All rate limiting detection tests passed!")
