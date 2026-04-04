"""
Test suite for detecting Cross-Site Request Forgery (CSRF) vulnerabilities.
"""
import re
from typing import Dict
import sys
from pathlib import Path

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations


class CSRFDetector:
    """Detects CSRF vulnerabilities in code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "python") -> Dict:
        """Analyze code for CSRF vulnerabilities."""
        if language == "python":
            return self._analyze_python(code)
        elif language == "javascript":
            return self._analyze_javascript(code)
        elif language == "php":
            return self._analyze_php(code)
        elif language == "go":
            return self._analyze_go(code)
        elif language == "java":
            return self._analyze_java(code)
        elif language == "rust":
            return self._analyze_rust(code)
        elif language == "csharp":
            return self._analyze_csharp(code)
        elif language in ["cpp", "c"]:
            return self._analyze_cpp(code)
        else:
            return {"score": 0, "vulnerabilities": ["Unsupported language"], "max_score": 2}

    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python/Flask code for CSRF."""
        self.vulnerabilities = []
        self.score = 2

        # Check if this is a Flask app
        uses_flask = re.search(r'from\s+flask\s+import|import\s+flask', code)

        if not uses_flask:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: State-changing routes (POST, PUT, DELETE, PATCH)
        state_changing_routes = find_pattern_locations(code, r'@app\.route\([^)]*methods\s*=\s*\[[^]]*["\'](?:POST|PUT|DELETE|PATCH)["\']')

        # Also check for route() followed by def with methods
        post_routes = find_pattern_locations(code, r'@app\.route\([^)]*\)')

        if state_changing_routes or post_routes:
            # Check for CSRF protection mechanisms
            has_csrf_extension = re.search(r'from\s+flask_wtf\.csrf\s+import|CSRFProtect|flask_csrf|SeaSurf', code)
            has_csrf_decorator = re.search(r'@csrf\.exempt|@csrf_protect|@csrf_required', code)
            has_csrf_token_check = re.search(r'csrf_token|request\.form\[.*csrf|validate_csrf', code, re.IGNORECASE)

            # Check for session-based tokens
            has_session_token = re.search(r'session\[.*token|session\.get\(.*token', code, re.IGNORECASE)

            # Check if using Flask-WTF forms (auto CSRF protection)
            uses_flask_wtf = re.search(r'from\s+flask_wtf\s+import\s+FlaskForm|from\s+wtforms', code)

            if not (has_csrf_extension or has_csrf_decorator or has_csrf_token_check or has_session_token or uses_flask_wtf):
                # Find the state-changing route
                locations = state_changing_routes or post_routes
                if locations:
                    location = locations[0]
                    line_num = location['line_number']
                    code_snippet = location['line_content']

                    # Determine method from route
                    method_match = re.search(r'methods\s*=\s*\[[^]]*(["\'](?:POST|PUT|DELETE|PATCH)["\'])', code_snippet)
                    method = method_match.group(1).strip('"\'') if method_match else "POST"

                    self.vulnerabilities.append({
                        "type": "CSRF",
                        "severity": "HIGH",
                        "description": f"State-changing endpoint ({method}) lacks CSRF protection - ATTACK: Attacker creates malicious site with <form action='https://victim.com/transfer' method='POST'><input name='amount' value='1000'><input name='to' value='attacker'></form><script>document.forms[0].submit()</script>. Victim visits attacker site while logged into victim.com → Form auto-submits → Uses victim's session cookie → Unauthorized action executed. IMPACT: Account takeover, unauthorized transactions, data modification, privilege escalation",
                        "recommendation": "Add CSRF protection: (1) Use Flask-WTF: 'from flask_wtf.csrf import CSRFProtect; csrf = CSRFProtect(app)' OR (2) Use Flask-SeaSurf: 'from flask_seasurf import SeaSurf; csrf = SeaSurf(app)' OR (3) Manual token validation: Generate token in session, include in forms, validate on POST",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "State-changing HTTP method (POST/PUT/DELETE/PATCH) without CSRF token validation",
                                "Endpoint accepts requests without verifying origin or CSRF token",
                                "No CSRF protection middleware (Flask-WTF, SeaSurf) enabled",
                                "Session-based authentication vulnerable to cross-site request attacks"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: {method} endpoint found without CSRF protection",
                                "No CSRFProtect/SeaSurf middleware detected in code",
                                "No csrf_token validation in request processing",
                                "ATTACK: (1) Victim logs into victim.com, (2) Visits attacker.com, (3) Attacker site submits form to victim.com endpoint, (4) Browser includes victim's session cookie, (5) Server processes request as victim",
                                "REAL-WORLD: Banking transfers, password changes, email updates, privilege escalations all exploitable via CSRF",
                                "IMPACT: Unauthorized actions performed with victim's authentication, no user interaction needed beyond visiting malicious page"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "Flask-WTF CSRFProtect extension usage",
                                "Flask-SeaSurf extension usage",
                                "@csrf.exempt/@csrf_protect decorators",
                                "csrf_token in forms or request validation",
                                "Session-based token generation/validation",
                                "FlaskForm usage (auto CSRF protection)"
                            ],
                            "evidence": {
                                "found_patterns": [f"{method} endpoint without CSRF protection"],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    self.score = 0
            else:
                # Has some CSRF protection
                # Find protection location
                protection_locations = []
                protection_locations.extend(find_pattern_locations(code, r'CSRFProtect|flask_csrf|SeaSurf'))
                protection_locations.extend(find_pattern_locations(code, r'@csrf'))
                protection_locations.extend(find_pattern_locations(code, r'csrf_token'))

                if protection_locations:
                    location = protection_locations[0]
                    line_num = location['line_number']
                    code_snippet = location['line_content']

                    self.vulnerabilities.append({
                        "type": "SECURE",
                        "severity": "INFO",
                        "description": "Uses CSRF protection mechanism",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "patterns_checked": [
                                "State-changing endpoints (POST/PUT/DELETE/PATCH) without CSRF protection",
                                "Missing CSRFProtect/SeaSurf middleware",
                                "No csrf_token validation",
                                "Unprotected form submissions"
                            ],
                            "why_not_vulnerable": [
                                f"Line {line_num}: CSRF protection mechanism detected",
                                "Uses Flask-WTF CSRFProtect, SeaSurf, or manual token validation",
                                "CSRF tokens prevent cross-site forged requests - attacker cannot forge valid token",
                                "Server validates token before processing state-changing requests",
                                "Tokens tied to user session - cannot be reused across sessions or users"
                            ],
                            "vulnerable_patterns_absent": [
                                "No unprotected POST/PUT/DELETE/PATCH endpoints",
                                "CSRF middleware/extension properly configured",
                                "Token validation enforced on state-changing operations",
                                "Cross-site request forgery attacks blocked by token validation"
                            ]
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
        """Analyze JavaScript/Express code for CSRF."""
        self.vulnerabilities = []
        self.score = 2

        # Check if this is an Express app
        uses_express = re.search(r'require\(["\']express["\']\)|from\s+["\']express["\']|app\.(post|put|delete|patch)\(', code)

        if not uses_express:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: State-changing routes (POST, PUT, DELETE, PATCH)
        state_changing_routes = []
        state_changing_routes.extend(find_pattern_locations(code, r'app\.post\('))
        state_changing_routes.extend(find_pattern_locations(code, r'app\.put\('))
        state_changing_routes.extend(find_pattern_locations(code, r'app\.delete\('))
        state_changing_routes.extend(find_pattern_locations(code, r'app\.patch\('))
        state_changing_routes.extend(find_pattern_locations(code, r'router\.post\('))

        if state_changing_routes:
            # Check for CSRF protection mechanisms
            has_csrf_middleware = re.search(r'csurf|csrf|cookie-parser.*csrf|express-csrf', code)
            has_csrf_token_check = re.search(r'csrfToken|_csrf|req\.csrfToken\(\)|validateCsrf', code)

            # Check for custom token validation
            has_custom_token = re.search(r'req\.headers\[.*x-csrf-token|req\.body\._csrf|req\.query\._csrf', code, re.IGNORECASE)

            if not (has_csrf_middleware or has_csrf_token_check or has_custom_token):
                # Find the state-changing route
                location = state_changing_routes[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                # Determine method from route
                method = "POST"
                if "put" in code_snippet.lower():
                    method = "PUT"
                elif "delete" in code_snippet.lower():
                    method = "DELETE"
                elif "patch" in code_snippet.lower():
                    method = "PATCH"

                self.vulnerabilities.append({
                    "type": "CSRF",
                    "severity": "HIGH",
                    "description": f"State-changing endpoint ({method}) lacks CSRF protection - ATTACK: Attacker hosts malicious page: '<form action=\"https://victim.com/api/transfer\" method=\"POST\"><input name=\"amount\" value=\"1000\"><input name=\"to\" value=\"attacker\"></form><script>fetch(\"https://victim.com/api/transfer\", {{method: \"POST\", credentials: \"include\", body: JSON.stringify({{amount: 1000, to: \"attacker\"}})}})</script>'. Victim visits while logged in → Request uses victim's cookies → Unauthorized action. IMPACT: Fund transfers, password changes, account deletion, privilege escalation",
                    "recommendation": "Add CSRF protection: (1) Use csurf middleware: 'const csrf = require(\"csurf\"); app.use(csrf({{ cookie: true }}));' (2) Include token in forms: '<input type=\"hidden\" name=\"_csrf\" value=\"{{{{ csrfToken }}}}\">' (3) Validate token: middleware automatically validates tokens in POST body/headers",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "State-changing HTTP method (POST/PUT/DELETE/PATCH) without CSRF token validation",
                            "Express endpoint accepts requests without origin verification",
                            "No csurf middleware or custom CSRF protection",
                            "Cookie-based sessions vulnerable to cross-site request forgery"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: {method} endpoint found without CSRF protection",
                            "No csurf middleware detected (require('csurf') not found)",
                            "No req.csrfToken() or CSRF token validation in request processing",
                            "ATTACK: (1) Victim authenticates to victim.com, (2) Opens attacker.com in another tab, (3) Attacker script calls fetch('victim.com/api/transfer', {credentials: 'include'}), (4) Browser includes victim's cookies, (5) Server processes as victim",
                            "REAL-WORLD: Social media actions (post/like/follow), financial transactions, account modifications all exploitable",
                            "IMPACT: Unauthorized state changes (transfers, deletions, privilege escalations) with victim's authentication"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "csurf middleware usage (require('csurf'))",
                            "express-csrf or cookie-parser with CSRF",
                            "req.csrfToken() or csrfToken validation",
                            "Custom token validation (req.headers['x-csrf-token'])",
                            "State-changing routes (POST/PUT/DELETE/PATCH)"
                        ],
                        "evidence": {
                            "found_patterns": [f"{method} endpoint without CSRF protection"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0
            else:
                # Has some CSRF protection
                protection_locations = []
                protection_locations.extend(find_pattern_locations(code, r'csurf|csrf'))
                protection_locations.extend(find_pattern_locations(code, r'csrfToken'))

                if protection_locations:
                    location = protection_locations[0]
                    line_num = location['line_number']
                    code_snippet = location['line_content']

                    self.vulnerabilities.append({
                        "type": "SECURE",
                        "severity": "INFO",
                        "description": "Uses CSRF protection mechanism",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "patterns_checked": [
                                "State-changing endpoints (POST/PUT/DELETE/PATCH) without CSRF protection",
                                "Missing csurf middleware",
                                "No csrfToken() or token validation",
                                "Unprotected fetch/form submissions"
                            ],
                            "why_not_vulnerable": [
                                f"Line {line_num}: CSRF protection mechanism detected",
                                "Uses csurf middleware or custom CSRF token validation",
                                "CSRF tokens prevent cross-site forged requests - attacker cannot forge valid token",
                                "Server validates CSRF token in POST body or x-csrf-token header before processing",
                                "Tokens are cryptographically secure and tied to user session"
                            ],
                            "vulnerable_patterns_absent": [
                                "No unprotected POST/PUT/DELETE/PATCH routes",
                                "csurf middleware properly configured and active",
                                "Token validation enforced on all state-changing operations",
                                "Cross-site request forgery attacks blocked by token verification"
                            ]
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

    def _analyze_go(self, code: str) -> Dict:
        """Analyze Go code for CSRF vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses a web framework
        uses_web_framework = re.search(r'net/http|gorilla/mux|gin-gonic/gin|echo', code)
        if not uses_web_framework:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: State-changing HTTP handlers (POST, PUT, DELETE)
        state_changing_handlers = []
        state_changing_handlers.extend(find_pattern_locations(code, r'\.Post\('))
        state_changing_handlers.extend(find_pattern_locations(code, r'\.PUT\('))
        state_changing_handlers.extend(find_pattern_locations(code, r'\.DELETE\('))
        state_changing_handlers.extend(find_pattern_locations(code, r'\.PATCH\('))
        state_changing_handlers.extend(find_pattern_locations(code, r'HandleFunc\([^)]*,.*func.*http\.ResponseWriter'))

        # Check if method is checked in handler
        has_method_check = re.search(r'r\.Method\s*==\s*["\']POST|r\.Method\s*==\s*["\']PUT|r\.Method\s*==\s*["\']DELETE', code)

        if state_changing_handlers or has_method_check:
            # Check for CSRF protection mechanisms
            has_csrf_middleware = re.search(r'gorilla/csrf|csrf\.Protect|csrf\.Token|nosurf', code)
            has_csrf_token_check = re.search(r'csrf\.Token|VerifyCsrfToken|checkCSRF', code, re.IGNORECASE)
            has_custom_token_validation = re.search(r'r\.Header\.Get\(["\']X-CSRF-Token|r\.FormValue\(["\']csrf_token', code, re.IGNORECASE)

            if not (has_csrf_middleware or has_csrf_token_check or has_custom_token_validation):
                location = state_changing_handlers[0] if state_changing_handlers else {"line_number": 0, "line_content": ""}
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "CSRF",
                    "severity": "HIGH",
                    "description": "Go HTTP handler for state-changing operation lacks CSRF protection - ATTACK: Attacker creates malicious site with form/fetch targeting victim's Go application. When victim visits attacker site while logged in, their cookies/session is automatically sent with cross-site request. Server processes request as legitimate, enabling unauthorized actions (fund transfers, password changes, account modifications). IMPACT: Account takeover, unauthorized transactions, data modification, privilege escalation",
                    "recommendation": "Add CSRF protection: (1) Use gorilla/csrf middleware: 'CSRF := csrf.Protect([]byte(\"32-byte-key\"), csrf.Secure(false)); r.Use(CSRF)' (2) Include token in templates: '{{ .csrfToken }}' (3) Or use nosurf middleware: 'http.ListenAndServe(\":8080\", nosurf.New(handler))'",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "HTTP handler accepts state-changing methods (POST/PUT/DELETE/PATCH) without CSRF token validation",
                            "No gorilla/csrf or nosurf middleware detected",
                            "No CSRF token validation in request processing",
                            "Cookie/session-based authentication vulnerable to cross-site attacks"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: State-changing HTTP handler without CSRF protection",
                            "No gorilla/csrf or nosurf middleware found",
                            "No csrf token validation in handler",
                            "ATTACK: Attacker hosts malicious page with <form action='https://victim.com/transfer' method='POST'>. Victim visits while logged in → Browser sends cookies → Unauthorized action executed",
                            "IMPACT: Attackers can perform any action victim is authorized to do: transfers, deletions, account changes"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "gorilla/csrf middleware usage",
                            "nosurf middleware usage",
                            "csrf.Token() validation",
                            "X-CSRF-Token header checks",
                            "State-changing HTTP handlers (POST/PUT/DELETE/PATCH)"
                        ],
                        "evidence": {
                            "found_patterns": ["State-changing handler without CSRF protection"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0
            else:
                # Has CSRF protection
                protection_locations = []
                protection_locations.extend(find_pattern_locations(code, r'csrf\.Protect|csrf\.Token|nosurf'))

                if protection_locations:
                    location = protection_locations[0]
                    line_num = location['line_number']
                    code_snippet = location['line_content']

                    self.vulnerabilities.append({
                        "type": "SECURE",
                        "severity": "INFO",
                        "description": "Uses CSRF protection mechanism (gorilla/csrf or nosurf)",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "patterns_checked": [
                                "State-changing HTTP handlers without CSRF protection",
                                "Missing gorilla/csrf or nosurf middleware",
                                "No CSRF token validation"
                            ],
                            "why_not_vulnerable": [
                                f"Line {line_num}: CSRF protection middleware detected",
                                "Uses gorilla/csrf or nosurf for automatic token validation",
                                "CSRF tokens prevent cross-site forged requests - attacker cannot forge valid token",
                                "Middleware validates token on state-changing requests before processing",
                                "Tokens are cryptographically secure and tied to user session"
                            ],
                            "vulnerable_patterns_absent": [
                                "No unprotected POST/PUT/DELETE/PATCH handlers",
                                "CSRF middleware properly configured",
                                "Token validation enforced on state-changing operations"
                            ]
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

    def _analyze_java(self, code: str) -> Dict:
        """Analyze Java code for CSRF vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses Spring or Java EE
        uses_web_framework = re.search(r'@Controller|@RestController|@PostMapping|@PutMapping|@DeleteMapping|HttpServlet', code)
        if not uses_web_framework:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: State-changing endpoints without CSRF protection
        state_changing_endpoints = []
        state_changing_endpoints.extend(find_pattern_locations(code, r'@PostMapping'))
        state_changing_endpoints.extend(find_pattern_locations(code, r'@PutMapping'))
        state_changing_endpoints.extend(find_pattern_locations(code, r'@DeleteMapping'))
        state_changing_endpoints.extend(find_pattern_locations(code, r'@PatchMapping'))
        state_changing_endpoints.extend(find_pattern_locations(code, r'doPost\('))
        state_changing_endpoints.extend(find_pattern_locations(code, r'doPut\('))
        state_changing_endpoints.extend(find_pattern_locations(code, r'doDelete\('))

        if state_changing_endpoints:
            # Check for CSRF protection mechanisms
            has_spring_security = re.search(r'@EnableWebSecurity|SpringSecurity|CsrfToken|csrf\(\)', code)
            has_csrf_filter = re.search(r'CsrfFilter|CsrfTokenRepository', code)
            has_csrf_token_check = re.search(r'_csrf|csrfToken|X-CSRF-TOKEN', code)

            # Check if CSRF is explicitly disabled
            csrf_disabled = re.search(r'\.csrf\(\)\.disable\(\)', code)

            if csrf_disabled or not (has_spring_security or has_csrf_filter or has_csrf_token_check):
                location = state_changing_endpoints[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "CSRF",
                    "severity": "HIGH",
                    "description": "Java endpoint for state-changing operation lacks CSRF protection - ATTACK: Attacker creates malicious website that submits form or AJAX request to victim's Spring application. When authenticated user visits attacker site, browser automatically includes session cookies with cross-origin request. Server processes request with user's credentials, executing unauthorized actions. IMPACT: Account takeover, unauthorized data modifications, privilege escalation, financial fraud",
                    "recommendation": "Add CSRF protection: (1) Use Spring Security: Add '@EnableWebSecurity' and ensure CSRF is NOT disabled (enabled by default). (2) Include CSRF token in forms: '<input type=\"hidden\" name=\"${_csrf.parameterName}\" value=\"${_csrf.token}\"/>' (3) For AJAX: Add token to request headers: 'X-CSRF-TOKEN: ${_csrf.token}' (4) Ensure session cookies use SameSite attribute",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "State-changing endpoint (@PostMapping/@PutMapping/@DeleteMapping) without CSRF protection",
                            "No Spring Security @EnableWebSecurity or CSRF configuration",
                            "CSRF explicitly disabled via .csrf().disable()",
                            "No CSRF token validation in request processing"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: State-changing endpoint without CSRF protection",
                            "No Spring Security CSRF protection detected" if not has_spring_security else "CSRF protection explicitly disabled",
                            "No CsrfToken or _csrf token validation",
                            "ATTACK: Attacker creates <form action='https://victim-app.com/api/transfer' method='POST'><input name='amount' value='10000'><input name='to' value='attacker-account'></form><script>document.forms[0].submit()</script>. User visits attacker page → Form auto-submits with user's cookies → Unauthorized transfer executed",
                            "IMPACT: Any authenticated action can be forged: money transfers, password changes, account deletions, privilege escalations"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "@EnableWebSecurity and Spring Security CSRF",
                            "CsrfFilter or CsrfTokenRepository",
                            "_csrf or csrfToken in templates",
                            "X-CSRF-TOKEN header validation",
                            ".csrf().disable() patterns"
                        ],
                        "evidence": {
                            "found_patterns": ["State-changing endpoint without CSRF protection"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0
            else:
                # Has CSRF protection
                protection_locations = []
                protection_locations.extend(find_pattern_locations(code, r'@EnableWebSecurity|CsrfToken|csrf\(\)'))

                if protection_locations:
                    location = protection_locations[0]
                    line_num = location['line_number']
                    code_snippet = location['line_content']

                    self.vulnerabilities.append({
                        "type": "SECURE",
                        "severity": "INFO",
                        "description": "Uses Spring Security CSRF protection",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "patterns_checked": [
                                "State-changing endpoints without CSRF protection",
                                "Missing @EnableWebSecurity",
                                "CSRF explicitly disabled",
                                "No CSRF token validation"
                            ],
                            "why_not_vulnerable": [
                                f"Line {line_num}: Spring Security CSRF protection enabled",
                                "Spring Security automatically validates CSRF tokens on state-changing requests",
                                "CSRF tokens are synchronizer tokens tied to user session - cannot be forged by attacker",
                                "Invalid or missing CSRF token results in 403 Forbidden response",
                                "Token must match server-side session value to process request"
                            ],
                            "vulnerable_patterns_absent": [
                                "No unprotected @PostMapping/@PutMapping/@DeleteMapping endpoints",
                                "CSRF not explicitly disabled via .csrf().disable()",
                                "Token validation enforced by Spring Security framework"
                            ]
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

    def _analyze_rust(self, code: str) -> Dict:
        """Analyze Rust code for CSRF vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses web frameworks
        uses_web_framework = re.search(r'actix_web::|rocket::|warp::|axum::', code)
        if not uses_web_framework:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: State-changing routes (POST, PUT, DELETE)
        state_changing_routes = []
        state_changing_routes.extend(find_pattern_locations(code, r'\.route\([^)]*post\('))
        state_changing_routes.extend(find_pattern_locations(code, r'\.route\([^)]*put\('))
        state_changing_routes.extend(find_pattern_locations(code, r'\.route\([^)]*delete\('))
        state_changing_routes.extend(find_pattern_locations(code, r'#\[post\('))
        state_changing_routes.extend(find_pattern_locations(code, r'#\[put\('))
        state_changing_routes.extend(find_pattern_locations(code, r'#\[delete\('))
        state_changing_routes.extend(find_pattern_locations(code, r'Method::POST|Method::PUT|Method::DELETE'))

        if state_changing_routes:
            # Check for CSRF protection mechanisms
            has_csrf_middleware = re.search(r'rocket_csrf|actix-csrf|CsrfMiddleware|csrf_token', code)
            has_csrf_guard = re.search(r'CsrfToken|csrf::Token|#\[csrf\]', code)
            has_custom_token_check = re.search(r'X-CSRF-Token|csrf_token|verify_csrf', code, re.IGNORECASE)

            if not (has_csrf_middleware or has_csrf_guard or has_custom_token_check):
                location = state_changing_routes[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "CSRF",
                    "severity": "HIGH",
                    "description": "Rust route for state-changing operation lacks CSRF protection - ATTACK: Attacker crafts malicious webpage with form or fetch() request targeting victim's Rust web application. When authenticated victim visits attacker site, browser automatically sends session cookies with cross-origin request. Rust server processes request using victim's authentication, enabling unauthorized state changes. IMPACT: Account modifications, unauthorized transactions, data corruption, privilege escalation",
                    "recommendation": "Add CSRF protection: (1) For Rocket: Use rocket_csrf crate and add CsrfToken guard to routes: '#[post(\"/transfer\", data = \"<form>\")] fn transfer(csrf: CsrfToken, form: Form<Data>) { ... }' (2) For Actix-web: Use actix-csrf middleware: 'App::new().wrap(CsrfMiddleware::new())' (3) Manual: Generate token in session, validate on POST/PUT/DELETE",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "State-changing route (POST/PUT/DELETE) without CSRF token validation",
                            "No rocket_csrf or actix-csrf middleware detected",
                            "No CsrfToken guard in route handlers",
                            "Cookie/session-based authentication vulnerable to cross-site forgery"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: State-changing route without CSRF protection",
                            "No CSRF middleware (rocket_csrf, actix-csrf) detected",
                            "No CsrfToken guard or token validation",
                            "ATTACK: Attacker creates malicious site with fetch('https://victim-app.com/api/delete', {method: 'POST', credentials: 'include', body: JSON.stringify({id: 123})}). Victim visits attacker site while logged in → fetch includes cookies → Server processes deletion as victim → Data lost",
                            "IMPACT: All authenticated actions exploitable: money transfers, account deletions, email changes, admin privilege grants"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "rocket_csrf or actix-csrf middleware",
                            "CsrfToken guard in route handlers",
                            "csrf_token validation in requests",
                            "X-CSRF-Token header checks",
                            "State-changing routes (POST/PUT/DELETE)"
                        ],
                        "evidence": {
                            "found_patterns": ["State-changing route without CSRF protection"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0
            else:
                # Has CSRF protection
                protection_locations = []
                protection_locations.extend(find_pattern_locations(code, r'rocket_csrf|actix-csrf|CsrfMiddleware|CsrfToken'))

                if protection_locations:
                    location = protection_locations[0]
                    line_num = location['line_number']
                    code_snippet = location['line_content']

                    self.vulnerabilities.append({
                        "type": "SECURE",
                        "severity": "INFO",
                        "description": "Uses CSRF protection mechanism (rocket_csrf, actix-csrf, or custom token validation)",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "patterns_checked": [
                                "State-changing routes without CSRF protection",
                                "Missing rocket_csrf or actix-csrf middleware",
                                "No CsrfToken guard",
                                "No token validation"
                            ],
                            "why_not_vulnerable": [
                                f"Line {line_num}: CSRF protection mechanism detected",
                                "Uses rocket_csrf, actix-csrf, or custom CSRF token validation",
                                "CSRF tokens are cryptographically secure synchronizer tokens tied to session",
                                "Invalid/missing token causes request rejection before handler execution",
                                "Attacker cannot obtain or forge valid token due to Same-Origin Policy"
                            ],
                            "vulnerable_patterns_absent": [
                                "No unprotected POST/PUT/DELETE routes",
                                "CSRF middleware/guard properly configured",
                                "Token validation enforced on state-changing operations"
                            ]
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

    def _analyze_csharp(self, code: str) -> Dict:
        """Analyze C# code for CSRF vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses ASP.NET MVC or Web API
        uses_web_framework = re.search(r'Controller|HttpPost|HttpPut|HttpDelete|ApiController|ControllerBase', code)
        if not uses_web_framework:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: State-changing actions without [ValidateAntiForgeryToken]
        state_changing_actions = []
        state_changing_actions.extend(find_pattern_locations(code, r'\[HttpPost\]'))
        state_changing_actions.extend(find_pattern_locations(code, r'\[HttpPut\]'))
        state_changing_actions.extend(find_pattern_locations(code, r'\[HttpDelete\]'))
        state_changing_actions.extend(find_pattern_locations(code, r'\[HttpPatch\]'))

        if state_changing_actions:
            # Check for CSRF protection mechanisms
            has_antiforgery_token = re.search(r'\[ValidateAntiForgeryToken\]|ValidateAntiForgeryToken', code)
            has_antiforgery_service = re.search(r'IAntiforgery|AntiforgeryToken|@Html\.AntiForgeryToken', code)
            has_auto_validate = re.search(r'AutoValidateAntiforgeryToken', code)

            # Check if using API controllers (which typically use different CSRF protection)
            is_api_controller = re.search(r'\[ApiController\]|: ControllerBase', code)

            if not (has_antiforgery_token or has_antiforgery_service or has_auto_validate or is_api_controller):
                location = state_changing_actions[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "CSRF",
                    "severity": "HIGH",
                    "description": "C# action for state-changing operation lacks [ValidateAntiForgeryToken] attribute - ATTACK: Attacker creates malicious website with form or JavaScript that posts to victim's ASP.NET application. When authenticated user visits attacker site, their authentication cookies are automatically sent with cross-origin POST request. Server processes request as legitimate user action, enabling unauthorized operations. IMPACT: Account takeover, unauthorized data changes, privilege escalation, financial fraud",
                    "recommendation": "Add CSRF protection: (1) Add [ValidateAntiForgeryToken] attribute to POST/PUT/DELETE actions: '[ValidateAntiForgeryToken] [HttpPost] public IActionResult Transfer(TransferModel model) { ... }' (2) Include token in forms: '@Html.AntiForgeryToken()' in Razor views (3) For AJAX: Include __RequestVerificationToken in request body or headers (4) Or use [AutoValidateAntiforgeryToken] globally in Startup.cs",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "[HttpPost]/[HttpPut]/[HttpDelete] action without [ValidateAntiForgeryToken]",
                            "No IAntiforgery service usage detected",
                            "No [AutoValidateAntiforgeryToken] global filter",
                            "MVC Controller (not API) accepting state-changing requests"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: State-changing action without [ValidateAntiForgeryToken]",
                            "No antiforgery token validation on POST/PUT/DELETE endpoint",
                            "ASP.NET MVC does not validate CSRF tokens by default - must explicitly add attribute",
                            "ATTACK: Attacker creates <form action='https://victim-site.com/Account/Transfer' method='POST'><input name='Amount' value='10000'><input name='ToAccount' value='attacker'></form><script>document.forms[0].submit()</script>. User visits attacker page while logged in → Form submits with user's .ASPXAUTH cookie → Unauthorized transfer executed",
                            "IMPACT: Attackers can perform any action user is authorized for: account changes, data modifications, privilege escalations, financial transactions"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "[ValidateAntiForgeryToken] attribute on actions",
                            "IAntiforgery service injection and usage",
                            "@Html.AntiForgeryToken() in views",
                            "[AutoValidateAntiforgeryToken] global filter",
                            "[ApiController] attribute (uses different protection)"
                        ],
                        "evidence": {
                            "found_patterns": ["State-changing action without [ValidateAntiForgeryToken]"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0
            else:
                # Has CSRF protection
                protection_locations = []
                protection_locations.extend(find_pattern_locations(code, r'\[ValidateAntiForgeryToken\]|\[AutoValidateAntiforgeryToken\]'))
                protection_locations.extend(find_pattern_locations(code, r'IAntiforgery|AntiForgeryToken'))

                if protection_locations:
                    location = protection_locations[0]
                    line_num = location['line_number']
                    code_snippet = location['line_content']

                    self.vulnerabilities.append({
                        "type": "SECURE",
                        "severity": "INFO",
                        "description": "Uses [ValidateAntiForgeryToken] or AntiForgery services for CSRF protection",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "patterns_checked": [
                                "State-changing actions without [ValidateAntiForgeryToken]",
                                "Missing IAntiforgery service",
                                "No @Html.AntiForgeryToken() in views",
                                "No global [AutoValidateAntiforgeryToken] filter"
                            ],
                            "why_not_vulnerable": [
                                f"Line {line_num}: CSRF protection via [ValidateAntiForgeryToken] or AntiForgery service",
                                "ASP.NET validates antiforgery token in request against server-generated token",
                                "Token is cryptographically secure and tied to user session",
                                "Missing or invalid token results in 400 Bad Request / 403 Forbidden",
                                "Attacker cannot obtain or forge token due to Same-Origin Policy"
                            ],
                            "vulnerable_patterns_absent": [
                                "No unprotected [HttpPost]/[HttpPut]/[HttpDelete] actions",
                                "[ValidateAntiForgeryToken] or [AutoValidateAntiforgeryToken] present",
                                "AntiForgery token validation enforced on state-changing operations"
                            ]
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

    def _analyze_cpp(self, code: str) -> Dict:
        """Analyze C/C++ code for CSRF vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code is a CGI/web application
        uses_cgi = any([
            re.search(r'REQUEST_METHOD|CONTENT_TYPE|HTTP_', code),
            re.search(r'getenv\(["\']REQUEST_METHOD["\']', code),
            re.search(r'cgicc::|CGI|Cgicc', code),  # cgicc library
        ])

        if not uses_cgi:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: Check for POST/PUT/DELETE handlers
        has_post_handler = any([
            re.search(r'REQUEST_METHOD.*POST', code),
            re.search(r'if.*strcmp.*REQUEST_METHOD.*POST', code),
            re.search(r'method\(\)\s*==\s*"POST"', code),  # cgicc
        ])

        if has_post_handler:
            # Check for CSRF token validation
            has_csrf_protection = any([
                re.search(r'csrf.*token|token.*csrf|_csrf', code, re.IGNORECASE),
                re.search(r'verify.*token|validate.*token|check.*token', code, re.IGNORECASE),
                re.search(r'session.*token|getenv.*CSRF', code, re.IGNORECASE),
            ])

            if not has_csrf_protection:
                # Find POST handler location
                post_locations = []
                post_locations.extend(find_pattern_locations(code, r'REQUEST_METHOD.*POST'))
                post_locations.extend(find_pattern_locations(code, r'method\(\)\s*==\s*"POST"'))

                if post_locations:
                    location = post_locations[0]
                    line_num = location['line_number']
                    code_snippet = location['line_content']

                    self.vulnerabilities.append({
                        "type": "CSRF",
                        "severity": "HIGH",
                        "description": "C/C++ CGI POST handler lacks CSRF protection - ATTACK: Attacker creates malicious website with form/AJAX targeting victim's CGI application. When authenticated victim visits attacker site, browser automatically sends session cookies with cross-origin POST request. CGI script processes request as legitimate user action. IMPACT: Account takeover, unauthorized transactions, data modification, privilege escalation.",
                        "recommendation": "Add CSRF protection: (1) Generate random CSRF token in session: token = generate_random_token(); set_session(\"csrf_token\", token), (2) Include token in forms: printf(\"<input type='hidden' name='csrf_token' value='%s'>\", get_session(\"csrf_token\")), (3) Validate token on POST: if (strcmp(form_token, session_token) != 0) { return error; }, (4) Use SameSite cookie attribute",
                        "example_attack": "Attacker hosts malicious page: <form action='https://victim-cgi.com/transfer.cgi' method='POST'><input name='amount' value='10000'><input name='to' value='attacker'></form><script>document.forms[0].submit()</script>. Victim visits page while logged in → Form auto-submits with victim's cookies → Unauthorized transfer executed",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "POST/PUT/DELETE handler without CSRF token validation",
                                "No csrf_token in request processing",
                                "Missing token verification functions",
                                "Cookie/session-based authentication vulnerable to cross-site attacks"
                            ],
                            "why_vulnerable": [
                                f"Line {line_num}: POST handler without CSRF protection",
                                "No CSRF token validation detected",
                                "CGI application accepts cross-origin POST requests",
                                "ATTACK: Attacker creates malicious form targeting CGI endpoint",
                                "Victim's browser includes session cookies with forged request",
                                "CGI processes request with victim's authentication"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "REQUEST_METHOD == POST checks",
                                "csrf_token validation",
                                "verify_token/validate_token functions",
                                "Session token checking"
                            ],
                            "evidence": {
                                "found_patterns": ["POST handler without CSRF protection"],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    self.score = 0
            else:
                # Has CSRF protection
                csrf_locations = find_pattern_locations(code, r'csrf.*token|verify.*token|validate.*token')
                if csrf_locations:
                    location = csrf_locations[0]
                    line_num = location['line_number']
                    code_snippet = location['line_content']

                    self.vulnerabilities.append({
                        "type": "SECURE",
                        "severity": "INFO",
                        "description": "Uses CSRF token validation - Validates CSRF tokens on state-changing requests to prevent cross-site request forgery attacks.",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "POST/PUT/DELETE handlers without CSRF protection",
                                "Missing token validation",
                                "No session-based token checking"
                            ],
                            "why_vulnerable": [],
                            "why_not_vulnerable": [
                                f"Line {line_num}: CSRF token validation detected",
                                "Validates tokens before processing state-changing requests",
                                "Prevents cross-site forged requests",
                                "Attacker cannot forge valid CSRF token"
                            ],
                            "patterns_checked": [
                                "csrf_token validation patterns",
                                "verify_token/validate_token functions",
                                "Session token checking",
                                "POST handlers"
                            ],
                            "evidence": {
                                "found_patterns": ["CSRF token validation"],
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

    def _analyze_php(self, code: str) -> Dict:
        """Analyze PHP code for CSRF vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 0: Check for state-changing operations via GET (CRITICAL CSRF vulnerability)
        has_get_with_state_change = re.search(r'\$_GET\[', code) and any([
            re.search(r'INSERT\s+INTO|UPDATE\s+|DELETE\s+FROM', code, re.IGNORECASE),
            re.search(r'\$stmt\s*=\s*\$conn->prepare\(["\'](?:INSERT|UPDATE|DELETE)', code, re.IGNORECASE),
            re.search(r'mysqli_query\([^,]+,\s*["\'](?:INSERT|UPDATE|DELETE)', code, re.IGNORECASE),
        ])

        if has_get_with_state_change:
            # Find GET parameter usage
            get_locations = find_pattern_locations(code, r'\$_GET\[')
            if get_locations:
                location = get_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "CSRF",
                    "severity": "CRITICAL",
                    "description": "PHP state-changing operation via GET parameters - CRITICAL CSRF + METHOD MISUSE: Using GET for state-changing operations (INSERT/UPDATE/DELETE) violates HTTP standards and enables trivial CSRF attacks. ATTACK: Attacker sends victim link: 'https://victim.com/transfer.php?to=attacker&amount=1000'. Victim clicks link (email, chat, forum) → Browser sends GET request with victim's cookies → Unauthorized action executed. No form needed, just a link. IMPACT: (1) CLICKABLE EXPLOIT - simple link in email/chat triggers attack, (2) IMAGE TAG - <img src='https://victim.com/delete.php?id=123'> auto-executes on page load, (3) PREFETCH - browser prefetching can trigger unintended state changes, (4) HISTORY LEAKAGE - URLs with sensitive operations logged in browser history/server logs. REAL-WORLD: Account deletion, fund transfers, password changes, privilege escalation all exploitable via simple link sharing.",
                    "recommendation": "NEVER use GET for state-changing operations: (1) Use POST/PUT/DELETE for ALL state changes (INSERT/UPDATE/DELETE), (2) Check REQUEST_METHOD: if ($_SERVER['REQUEST_METHOD'] !== 'POST') die('Method not allowed');, (3) Add CSRF token validation as described below, (4) HTTP GET should be idempotent (safe to repeat without side effects) - only for data retrieval",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "State-changing database operations (INSERT/UPDATE/DELETE) using $_GET parameters",
                            "HTTP GET method used for non-idempotent operations",
                            "Violates HTTP RFC 7231 (GET must be safe and idempotent)",
                            "Trivially exploitable via links, images, or any HTTP GET request"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: $_GET parameters used with state-changing SQL operations",
                            "GET requests include parameters in URL - visible in logs, browser history, referrer headers",
                            "No request body or form submission required - simple link click triggers attack",
                            "ATTACK VECTOR 1 (Link): Attacker sends email with malicious link → Victim clicks → State change executed",
                            "ATTACK VECTOR 2 (Image): Attacker embeds <img src='victim.com/delete.php?id=123'> in forum post → Auto-loads when victim views page → Deletion executed",
                            "ATTACK VECTOR 3 (Prefetch): Browser prefetching can trigger GET requests before user interaction",
                            "REAL-WORLD EXAMPLE: User shares link 'victim.com/transfer.php?to=attacker&amount=1000' on social media → Anyone logged in who clicks it performs transfer",
                            "IMPACT: Complete bypass of CSRF protection - no token validation possible because simple links don't carry custom data"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "$_GET parameter usage",
                            "INSERT/UPDATE/DELETE SQL statements",
                            "State-changing database operations",
                            "HTTP method validation"
                        ],
                        "evidence": {
                            "found_patterns": ["$_GET with state-changing SQL (INSERT/UPDATE/DELETE)"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0

        # Pattern 1: Check for POST/PUT/DELETE processing
        has_post_processing = any([
            re.search(r'\$_SERVER\[["\']REQUEST_METHOD["\']\]\s*===?\s*["\']POST["\']', code),
            re.search(r'\$_SERVER\[["\']REQUEST_METHOD["\']\]\s*===?\s*["\']PUT["\']', code),
            re.search(r'\$_SERVER\[["\']REQUEST_METHOD["\']\]\s*===?\s*["\']DELETE["\']', code),
            re.search(r'\$_POST\[', code),
            re.search(r'<form[^>]*method\s*=\s*["\']POST["\']', code, re.IGNORECASE),
        ])

        if not has_post_processing:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 2: Check for CSRF protection mechanisms
        # WordPress CSRF protection
        has_wp_nonce_field = re.search(r'wp_nonce_field\(', code)
        has_wp_verify_nonce = re.search(r'wp_verify_nonce\(', code)

        # Laravel CSRF protection
        has_laravel_csrf = any([
            re.search(r'@csrf', code),
            re.search(r'{{\s*csrf_field\(\)', code),
            re.search(r'{{\s*csrf_token\(\)', code),
            re.search(r'csrf_token\(\)', code),
        ])

        # Manual CSRF token validation
        has_manual_csrf = any([
            re.search(r'\$_SESSION\[["\']csrf_token["\']\]', code),
            re.search(r'session\(["\']csrf_token["\']\)', code),
            re.search(r'verify.*csrf|validate.*csrf|check.*csrf', code, re.IGNORECASE),
            re.search(r'<input[^>]*name\s*=\s*["\']csrf_token["\']', code, re.IGNORECASE),
            re.search(r'<input[^>]*name\s*=\s*["\']_token["\']', code, re.IGNORECASE),
        ])

        # Check if CSRF protection is present
        has_csrf_protection = (has_wp_nonce_field or has_wp_verify_nonce or
                               has_laravel_csrf or has_manual_csrf)

        if not has_csrf_protection:
            # Find POST forms or POST processing
            post_locations = []
            post_locations.extend(find_pattern_locations(code, r'<form[^>]*method\s*=\s*["\']POST["\']'))
            if not post_locations:
                post_locations.extend(find_pattern_locations(code, r'\$_SERVER\[["\']REQUEST_METHOD["\']\]\s*===?\s*["\']POST["\']'))
            if not post_locations:
                post_locations.extend(find_pattern_locations(code, r'\$_POST\['))

            if post_locations:
                location = post_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "CSRF",
                    "severity": "HIGH",
                    "description": "PHP POST form/handler lacks CSRF protection - ATTACK: Attacker creates malicious website with hidden form: '<form action=\"https://victim.com/admin.php\" method=\"POST\"><input name=\"user_id\" value=\"123\"></form><script>document.forms[0].submit()</script>'. When authenticated admin visits attacker site, form auto-submits with admin's session cookies. Server processes deletion request as legitimate admin action. IMPACT: Account deletion, unauthorized data modifications, privilege escalation, financial fraud - all actions admin can perform are exploitable",
                    "recommendation": "Add CSRF protection: (1) WordPress: Add 'wp_nonce_field(\"delete_user\")' to form and 'if (!wp_verify_nonce($_POST[\"_wpnonce\"], \"delete_user\")) die(\"Invalid nonce\");' to handler. (2) Laravel: Add '@csrf' directive inside forms or '{{ csrf_field() }}'. (3) Manual: Generate token: '$_SESSION[\"csrf_token\"] = bin2hex(random_bytes(32));', include in form: '<input type=\"hidden\" name=\"csrf_token\" value=\"<?php echo $_SESSION[\"csrf_token\"]; ?>\">', validate: 'if (!hash_equals($_SESSION[\"csrf_token\"], $_POST[\"csrf_token\"])) die(\"Invalid token\");'",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "POST/PUT/DELETE form or handler without CSRF token validation",
                            "No WordPress wp_nonce_field() in forms or wp_verify_nonce() in handlers",
                            "No Laravel @csrf directive or csrf_field() helper",
                            "No manual CSRF token ($_SESSION['csrf_token']) generation/validation",
                            "Session-based authentication vulnerable to cross-site request forgery"
                        ],
                        "why_vulnerable": [
                            f"Line {line_num}: POST form/handler found without CSRF protection",
                            "No wp_nonce_field() or wp_verify_nonce() detected (WordPress)",
                            "No @csrf directive or csrf_token() detected (Laravel)",
                            "No $_SESSION['csrf_token'] or manual token validation",
                            "ATTACK: (1) Admin logs into victim.com, (2) Visits attacker.com in another tab, (3) Attacker site contains hidden form targeting victim.com/admin.php, (4) JavaScript auto-submits form, (5) Browser includes admin's session cookies, (6) Server processes request as admin, (7) User deleted/data modified without admin's knowledge",
                            "REAL-WORLD: Admin panels vulnerable to account deletion, privilege escalation, configuration changes, financial transactions - all exploitable via malicious links or embedded iframes",
                            "IMPACT: Complete compromise of admin actions - attacker can perform ANY operation admin is authorized for by tricking them into visiting malicious page"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "WordPress wp_nonce_field() in forms",
                            "WordPress wp_verify_nonce() in POST handlers",
                            "Laravel @csrf directive or csrf_field()",
                            "Laravel csrf_token() validation",
                            "Manual $_SESSION['csrf_token'] generation/validation",
                            "Hidden input fields with csrf_token or _token names",
                            "Token verification functions (verify_csrf, validate_csrf, check_csrf)"
                        ],
                        "evidence": {
                            "found_patterns": ["POST form/handler without CSRF protection"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0
        else:
            # Has CSRF protection
            protection_locations = []
            if has_wp_nonce_field or has_wp_verify_nonce:
                protection_locations.extend(find_pattern_locations(code, r'wp_nonce_field|wp_verify_nonce'))
            if has_laravel_csrf:
                protection_locations.extend(find_pattern_locations(code, r'@csrf|csrf_field|csrf_token'))
            if has_manual_csrf:
                protection_locations.extend(find_pattern_locations(code, r'\$_SESSION\[["\']csrf_token["\']\]|csrf_token'))

            if protection_locations:
                location = protection_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": "Uses CSRF protection mechanism (WordPress nonces, Laravel CSRF, or manual token validation)",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "patterns_checked": [
                            "POST/PUT/DELETE forms without CSRF tokens",
                            "Missing WordPress wp_nonce_field() or wp_verify_nonce()",
                            "Missing Laravel @csrf directive",
                            "No manual CSRF token validation",
                            "Unprotected form submissions"
                        ],
                        "why_not_vulnerable": [
                            f"Line {line_num}: CSRF protection mechanism detected",
                            "Uses WordPress nonces, Laravel CSRF tokens, or manual token validation",
                            "CSRF tokens are cryptographically secure synchronizer tokens tied to user session",
                            "Server validates token before processing state-changing requests",
                            "Attacker cannot obtain or forge valid token due to Same-Origin Policy",
                            "Invalid or missing token results in request rejection",
                            "Tokens prevent cross-site forged requests - attacker's malicious site cannot include valid token"
                        ],
                        "vulnerable_patterns_absent": [
                            "No unprotected POST/PUT/DELETE forms or handlers",
                            "CSRF protection properly implemented via framework or manual validation",
                            "Token validation enforced on all state-changing operations",
                            "Cross-site request forgery attacks blocked by token verification"
                        ]
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


def test_csrf_python_vulnerable():
    """Test detection of CSRF in Flask without protection."""
    vulnerable_code = '''
from flask import Flask, request

app = Flask(__name__)

@app.route('/transfer', methods=['POST'])
def transfer():
    amount = request.form.get('amount')
    to = request.form.get('to')
    # Process transfer
    return 'Transfer complete'
'''
    detector = CSRFDetector()
    result = detector.analyze(vulnerable_code, "python")
    assert result["score"] == 0, "Should detect CSRF vulnerability"
    assert any('CSRF' in v['type'] for v in result['vulnerabilities'])


def test_csrf_python_secure():
    """Test detection of Flask with CSRF protection."""
    secure_code = '''
from flask import Flask, request
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
csrf = CSRFProtect(app)

@app.route('/transfer', methods=['POST'])
def transfer():
    amount = request.form.get('amount')
    to = request.form.get('to')
    # Process transfer
    return 'Transfer complete'
'''
    detector = CSRFDetector()
    result = detector.analyze(secure_code, "python")
    assert result["score"] == 2, "Should recognize CSRF protection"


def test_csrf_javascript_vulnerable():
    """Test detection of CSRF in Express without protection."""
    vulnerable_code = '''
const express = require('express');
const app = express();

app.post('/transfer', (req, res) => {
    const { amount, to } = req.body;
    // Process transfer
    res.json({ success: true });
});
'''
    detector = CSRFDetector()
    result = detector.analyze(vulnerable_code, "javascript")
    assert result["score"] == 0, "Should detect CSRF vulnerability"


def test_csrf_javascript_secure():
    """Test detection of Express with CSRF protection."""
    secure_code = '''
const express = require('express');
const csrf = require('csurf');
const app = express();

const csrfProtection = csrf({ cookie: true });

app.post('/transfer', csrfProtection, (req, res) => {
    const { amount, to } = req.body;
    // Process transfer
    res.json({ success: true });
});
'''
    detector = CSRFDetector()
    result = detector.analyze(secure_code, "javascript")
    assert result["score"] == 2, "Should recognize CSRF protection"


if __name__ == "__main__":
    test_csrf_python_vulnerable()
    test_csrf_python_secure()
    test_csrf_javascript_vulnerable()
    test_csrf_javascript_secure()
    print("All CSRF detection tests passed!")
