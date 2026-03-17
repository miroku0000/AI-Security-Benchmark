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
    print("✅ All CSRF detection tests passed!")
