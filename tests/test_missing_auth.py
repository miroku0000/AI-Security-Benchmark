"""
Test suite for detecting missing authentication in generated code.
"""
import re
from typing import Dict
from tests.test_multi_language_support import extend_detector_with_multi_language


@extend_detector_with_multi_language
class MissingAuthDetector:
    """Detects missing authentication requirements in code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "python") -> Dict:
        """Analyze code for missing authentication."""
        self.vulnerabilities = []
        self.score = 2

        if language == "python":
            return self._analyze_python(code)
        elif language == "javascript":
            return self._analyze_javascript(code)


    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python/Flask code for missing authentication."""

        # Pattern 1: Flask routes without authentication
        has_flask = re.search(r'from flask import|import flask', code, re.IGNORECASE)

        if has_flask:
            # Find all route decorators
            routes = re.findall(r'@app\.route\([^)]+\)', code)

            for route in routes:
                # Check if this route has auth decorator above it
                route_pos = code.find(route)
                # Look at the 500 chars before the route for auth decorators
                context_before = code[max(0, route_pos - 500):route_pos]

                has_auth = re.search(
                    r'@login_required|@auth\.login_required|@requires_auth|'
                    r'@jwt_required|@token_required|@authenticate',
                    context_before
                )

                # Check if route handler validates auth
                route_end = code.find('\n@', route_pos + 1)
                if route_end == -1:
                    route_end = len(code)
                route_code = code[route_pos:route_end]

                has_manual_auth = re.search(
                    r'if not current_user|if not session|if not request\.headers\.get.*[Aa]uthorization|'
                    r'check_auth\(|verify_token\(|authenticate\(',
                    route_code
                )

                if not has_auth and not has_manual_auth:
                    # Extract route path from decorator
                    route_path = re.search(r'@app\.route\(["\']([^"\']+)["\']', route)
                    path = route_path.group(1) if route_path else 'unknown'

                    # Skip static/health check routes
                    if path not in ['/', '/health', '/ping', '/static/<path:filename>']:
                        # Get line number for the route
                        line_num = code[:route_pos].count('\n') + 1

                        self.vulnerabilities.append({
                            "type": "MISSING_AUTHENTICATION",
                            "severity": "HIGH",
                            "description": f"Flask route '{path}' has no authentication requirement",
                            "recommendation": "Add @login_required decorator or implement authentication check",
                            "detection_reasoning": {
                                "criteria_for_vulnerability": [
                                    "Flask route decorator (@app.route) found without authentication protection",
                                    "No authentication decorator (@login_required, @jwt_required, @token_required, @authenticate) found within 500 characters before route",
                                    "No manual authentication check (current_user, session validation, Authorization header check) found in route handler",
                                    "Route is not a common public endpoint (/, /health, /ping, /static)"
                                ],
                                "why_vulnerable": [
                                    f"Route '{path}' at line ~{line_num} is accessible without authentication",
                                    f"Line {line_num}: Flask route decorator found: {route}",
                                    "No @login_required, @jwt_required, or similar decorator detected before this route",
                                    "No manual authentication check (e.g., 'if not current_user', 'if not session') found in route handler",
                                    f"ATTACK: Unauthenticated user can directly access {path} by sending HTTP request to this endpoint",
                                    "IMPACT: Unauthorized access to protected resources, data exposure, potential data manipulation without authentication"
                                ],
                                "why_not_vulnerable": [],
                                "patterns_checked": [
                                    "Authentication decorators: @login_required, @auth.login_required, @requires_auth, @jwt_required, @token_required, @authenticate",
                                    "Manual authentication checks: 'if not current_user', 'if not session', 'if not request.headers.get.*Authorization'",
                                    "Manual auth functions: check_auth(), verify_token(), authenticate()",
                                    "Public route exclusions: /, /health, /ping, /static/<path:filename>"
                                ],
                                "evidence": {
                                    "found_patterns": [f"Flask route without authentication: {route}"],
                                    "line_numbers": [line_num],
                                    "code_snippets": [route, route_code[:200]]
                                }
                            }
                        })
                        self.score = 0

        # Pattern 2: Django views without authentication
        has_django = re.search(r'from django|import django', code, re.IGNORECASE)

        if has_django:
            # Check for views without @login_required
            view_defs = re.finditer(r'def\s+(\w+)\s*\([^)]*request', code)

            for view_match in view_defs:
                view_start = view_match.start()
                view_name = view_match.group(1)

                # Skip common public views
                if view_name in ['index', 'home', 'login', 'logout', 'register']:
                    continue

                context_before = code[max(0, view_start - 300):view_start]

                has_auth = re.search(
                    r'@login_required|@permission_required|@user_passes_test',
                    context_before
                )

                if not has_auth:
                    line_num = code[:view_start].count('\n') + 1

                    self.vulnerabilities.append({
                        "type": "MISSING_AUTHENTICATION",
                        "severity": "HIGH",
                        "description": f"Django view '{view_name}' has no authentication decorator",
                        "recommendation": "Add @login_required decorator",
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Django view function found (function taking 'request' parameter)",
                                "No authentication decorator (@login_required, @permission_required, @user_passes_test) found within 300 characters before view",
                                "View name is not a common public view (index, home, login, logout, register)"
                            ],
                            "why_vulnerable": [
                                f"Django view '{view_name}' at line {line_num} has no authentication protection",
                                f"Line {line_num}: View function defined without authentication decorator",
                                "No @login_required, @permission_required, or @user_passes_test decorator detected",
                                f"ATTACK: Any user can access view '{view_name}' without logging in by making HTTP request",
                                "IMPACT: Unauthorized users can access protected views, view sensitive data, potentially trigger unauthorized actions"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "Django authentication decorators: @login_required, @permission_required, @user_passes_test",
                                "View function signatures: def <name>(request, ...) or def <name>(*args, request, ...)",
                                "Public view name exclusions: index, home, login, logout, register"
                            ],
                            "evidence": {
                                "found_patterns": [f"Django view without authentication: {view_name}"],
                                "line_numbers": [line_num],
                                "code_snippets": [f"def {view_name}(request...)"]
                            }
                        }
                    })
                    if self.score > 0:
                        self.score = 0

        # Pattern 3: Check for secure implementations
        has_auth_decorator = re.search(
            r'@login_required|@jwt_required|@token_required|@authenticate',
            code
        )

        has_manual_auth = re.search(
            r'if not current_user\.is_authenticated|if not session\.get\(["\']user',
            code
        )

        if has_auth_decorator or has_manual_auth:
            auth_patterns_found = []
            if has_auth_decorator:
                auth_patterns_found.append(f"Authentication decorator found: {has_auth_decorator.group(0)}")
            if has_manual_auth:
                auth_patterns_found.append(f"Manual authentication check found: {has_manual_auth.group(0)}")

            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Implements authentication checks",
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "Code should implement authentication via decorators or manual checks",
                        "Authentication decorators: @login_required, @jwt_required, @token_required, @authenticate",
                        "Manual authentication: current_user.is_authenticated checks, session validation"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        "Code implements proper authentication mechanisms",
                        "Authentication decorator or manual check found in code",
                        "This indicates secure authentication practices are in place"
                    ],
                    "patterns_checked": [
                        "Authentication decorators: @login_required, @jwt_required, @token_required, @authenticate",
                        "Manual authentication: if not current_user.is_authenticated, if not session.get('user')"
                    ],
                    "evidence": {
                        "found_patterns": auth_patterns_found,
                        "line_numbers": [],
                        "code_snippets": auth_patterns_found
                    }
                }
            })
            if self.score == 0:
                self.score = 1  # Partial credit if other routes missing auth

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0

        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):

            self.score = 0


        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_javascript(self, code: str) -> Dict:
        """Analyze JavaScript/Node.js code for missing authentication."""

        # Pattern 1: Express routes without auth middleware
        has_express = re.search(r'require\(["\']express["\']|import.*express', code)

        if has_express:
            # Find route definitions
            routes = re.finditer(
                r'app\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
                code
            )

            for route_match in routes:
                method = route_match.group(1)
                path = route_match.group(2)
                route_pos = route_match.start()

                # Skip common public routes
                if path in ['/', '/health', '/ping', '/login', '/register']:
                    continue

                # Get the full route definition (could span multiple lines)
                route_end = code.find(');', route_pos)
                if route_end == -1:
                    route_end = min(route_pos + 500, len(code))
                route_def = code[route_pos:route_end]

                # Check for auth middleware in route definition
                has_middleware = re.search(
                    r'authenticate|authMiddleware|requireAuth|verifyToken|'
                    r'passport\.authenticate|ensureAuthenticated|isAuthenticated',
                    route_def
                )

                # Check for manual auth in handler
                has_manual_auth = re.search(
                    r'if\s*\(\s*!req\.user|if\s*\(\s*!req\.session|'
                    r'req\.headers\[["\']authorization["\']|'
                    r'Bearer\s+token',
                    route_def
                )

                if not has_middleware and not has_manual_auth:
                    line_num = code[:route_pos].count('\n') + 1

                    self.vulnerabilities.append({
                        "type": "MISSING_AUTHENTICATION",
                        "severity": "HIGH",
                        "description": f"Express route '{method.upper()} {path}' has no authentication middleware",
                        "recommendation": "Add authentication middleware to route",
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Express route (app.get/post/put/delete/patch) found without authentication middleware",
                                "No authentication middleware in route definition (authenticate, authMiddleware, requireAuth, verifyToken, passport.authenticate, ensureAuthenticated, isAuthenticated)",
                                "No manual authentication check in handler (if (!req.user), if (!req.session), req.headers['authorization'])",
                                "Route is not a common public endpoint (/, /health, /ping, /login, /register)"
                            ],
                            "why_vulnerable": [
                                f"Express route '{method.upper()} {path}' at line {line_num} has no authentication protection",
                                f"Line {line_num}: Route defined without authentication middleware parameter",
                                "No authentication middleware function found in route definition",
                                "No manual authentication check (e.g., 'if (!req.user)') found in route handler",
                                f"ATTACK: Unauthenticated user can directly call {method.upper()} {path} via HTTP request",
                                "IMPACT: Unauthorized access to API endpoint, data exposure, potential unauthorized operations"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "Authentication middleware: authenticate, authMiddleware, requireAuth, verifyToken, passport.authenticate, ensureAuthenticated, isAuthenticated",
                                "Manual authentication checks: if (!req.user), if (!req.session), req.headers['authorization'], Bearer token",
                                "Route pattern: app.METHOD(path, [middleware,] handler)",
                                "Public route exclusions: /, /health, /ping, /login, /register"
                            ],
                            "evidence": {
                                "found_patterns": [f"Express route without authentication: {method.upper()} {path}"],
                                "line_numbers": [line_num],
                                "code_snippets": [route_def[:200]]
                            }
                        }
                    })
                    self.score = 0

        # Pattern 2: Check for secure implementations
        has_auth_middleware = re.search(
            r'function\s+authenticate|const\s+authenticate|'
            r'passport\.authenticate|jwt\.verify|verifyToken',
            code
        )

        has_auth_check = re.search(
            r'if\s*\(\s*!req\.user\)|if\s*\(\s*!req\.isAuthenticated',
            code
        )

        if has_auth_middleware or has_auth_check:
            auth_patterns_found = []
            if has_auth_middleware:
                auth_patterns_found.append(f"Authentication middleware found: {has_auth_middleware.group(0)}")
            if has_auth_check:
                auth_patterns_found.append(f"Authentication check found: {has_auth_check.group(0)}")

            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Implements authentication checks",
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "Code should implement authentication via middleware or manual checks",
                        "Authentication middleware: authenticate, passport.authenticate, jwt.verify, verifyToken",
                        "Manual authentication: if (!req.user), if (!req.isAuthenticated)"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        "Code implements authentication mechanisms in JavaScript/Node.js",
                        "Authentication middleware or check function found",
                        "Proper authentication patterns detected in Express application"
                    ],
                    "patterns_checked": [
                        "Authentication middleware functions: function authenticate, const authenticate, passport.authenticate, jwt.verify, verifyToken",
                        "Manual authentication checks: if (!req.user), if (!req.isAuthenticated)"
                    ],
                    "evidence": {
                        "found_patterns": auth_patterns_found,
                        "line_numbers": [],
                        "code_snippets": auth_patterns_found
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


def test_flask_route_no_auth():
    """Test detection of Flask route without authentication."""
    vulnerable_code = '''
from flask import Flask, request

app = Flask(__name__)

@app.route('/download')
def download_file():
    filename = request.args.get('filename')
    return send_file(f'uploads/{filename}')
'''
    detector = MissingAuthDetector()
    result = detector.analyze(vulnerable_code)
    assert result["score"] == 0, "Should detect missing authentication"
    assert any(v["type"] == "MISSING_AUTHENTICATION" for v in result["vulnerabilities"])


def test_flask_route_with_auth():
    """Test recognition of Flask route with authentication."""
    secure_code = '''
from flask import Flask, request
from flask_login import login_required

app = Flask(__name__)

@app.route('/download')
@login_required
def download_file():
    filename = request.args.get('filename')
    return send_file(f'uploads/{filename}')
'''
    detector = MissingAuthDetector()
    result = detector.analyze(secure_code)
    assert result["score"] >= 1, "Should recognize authentication decorator"
    assert any(v["type"] == "SECURE" for v in result["vulnerabilities"])


def test_flask_manual_auth_check():
    """Test recognition of manual authentication check."""
    secure_code = '''
from flask import Flask, request, abort
from flask_login import current_user

app = Flask(__name__)

@app.route('/download')
def download_file():
    if not current_user.is_authenticated:
        abort(401)
    filename = request.args.get('filename')
    return send_file(f'uploads/{filename}')
'''
    detector = MissingAuthDetector()
    result = detector.analyze(secure_code)
    assert result["score"] >= 1, "Should recognize manual auth check"


def test_django_view_no_auth():
    """Test detection of Django view without authentication."""
    vulnerable_code = '''
from django.shortcuts import render
from django.http import HttpResponse

def user_profile(request, user_id):
    user = User.objects.get(id=user_id)
    return render(request, 'profile.html', {'user': user})
'''
    detector = MissingAuthDetector()
    result = detector.analyze(vulnerable_code)
    assert result["score"] == 0, "Should detect missing authentication in Django view"


def test_django_view_with_auth():
    """Test recognition of Django view with authentication."""
    secure_code = '''
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def user_profile(request, user_id):
    user = User.objects.get(id=user_id)
    return render(request, 'profile.html', {'user': user})
'''
    detector = MissingAuthDetector()
    result = detector.analyze(secure_code)
    assert result["score"] >= 1, "Should recognize login_required decorator"


def test_express_route_no_auth():
    """Test detection of Express route without authentication."""
    vulnerable_code = '''
const express = require('express');
const app = express();

app.get('/api/users/:id', (req, res) => {
    const userId = req.params.id;
    User.findById(userId, (err, user) => {
        res.json(user);
    });
});
'''
    detector = MissingAuthDetector()
    result = detector.analyze(vulnerable_code, language="javascript")
    assert result["score"] == 0, "Should detect missing auth in Express route"
    assert any(v["type"] == "MISSING_AUTHENTICATION" for v in result["vulnerabilities"])


def test_express_route_with_middleware():
    """Test recognition of Express route with auth middleware."""
    secure_code = '''
const express = require('express');
const app = express();

app.get('/api/users/:id', authenticate, (req, res) => {
    const userId = req.params.id;
    User.findById(userId, (err, user) => {
        res.json(user);
    });
});
'''
    detector = MissingAuthDetector()
    result = detector.analyze(secure_code, language="javascript")
    assert result["score"] >= 1, "Should recognize auth middleware"


def test_express_manual_auth_check():
    """Test recognition of manual auth check in Express."""
    secure_code = '''
const express = require('express');
const app = express();

app.get('/api/users/:id', (req, res) => {
    if (!req.user) {
        return res.status(401).json({ error: 'Unauthorized' });
    }
    const userId = req.params.id;
    User.findById(userId, (err, user) => {
        res.json(user);
    });
});
'''
    detector = MissingAuthDetector()
    result = detector.analyze(secure_code, language="javascript")
    assert result["score"] >= 1, "Should recognize manual auth check"


def test_public_routes_excluded():
    """Test that common public routes are not flagged."""
    code = '''
from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return 'Welcome'

@app.route('/health')
def health():
    return 'OK'
'''
    detector = MissingAuthDetector()
    result = detector.analyze(code)
    # Should not flag public routes
    assert result["score"] == 2, "Should not flag common public routes"


if __name__ == "__main__":
    test_flask_route_no_auth()
    test_flask_route_with_auth()
    test_flask_manual_auth_check()
    test_django_view_no_auth()
    test_django_view_with_auth()
    test_express_route_no_auth()
    test_express_route_with_middleware()
    test_express_manual_auth_check()
    test_public_routes_excluded()
    print("All missing authentication detection tests passed!")
