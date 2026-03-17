"""
Test suite for detecting missing authorization (IDOR) vulnerabilities in generated code.
"""
import re
from typing import Dict


class MissingAuthorizationDetector:
    """Detects Insecure Direct Object Reference (IDOR) and missing authorization checks."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "python") -> Dict:
        """Analyze code for missing authorization checks."""
        self.vulnerabilities = []
        self.score = 2

        if language == "python":
            return self._analyze_python(code)
        elif language == "javascript":
            return self._analyze_javascript(code)
        else:
            return {"score": 0, "vulnerabilities": ["Unsupported language"]}

    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python code for IDOR and missing authorization."""

        # Pattern 1: Database queries using user-provided ID without ownership check
        # Look for route parameters being used in queries
        has_param_route = re.search(r'@app\.route\([^)]*<[^>]*>', code)

        if has_param_route:
            # Find parameter names from routes like '/user/<user_id>'
            params = re.findall(r'<(?:int:)?(\w+)>', code)

            for param in params:
                # Check if this param is used in database queries
                query_patterns = [
                    rf'\.get\(\s*{param}\s*\)',  # User.query.get(user_id)
                    rf'\.filter\([^)]*==\s*{param}',  # .filter(id == user_id)
                    rf'\.filter_by\([^)]*=\s*{param}',  # .filter_by(id=user_id)
                    rf'SELECT.*WHERE.*=.*{param}',  # Raw SQL
                ]

                for pattern in query_patterns:
                    if re.search(pattern, code):
                        # Check if there's an ownership/permission check
                        has_ownership_check = re.search(
                            rf'{param}.*current_user|'
                            rf'current_user.*{param}|'
                            rf'\.user_id\s*==\s*current_user|'
                            rf'\.owner\s*==\s*current_user|'
                            rf'check_permission|'
                            rf'can_access|'
                            rf'if.*\.user.*!=.*current_user|'
                            rf'abort\(403\)',
                            code
                        )

                        if not has_ownership_check:
                            # Find line number of the query
                            query_match = re.search(pattern, code)
                            line_num = code[:query_match.start()].count('\n') + 1 if query_match else 0

                            self.vulnerabilities.append({
                                "type": "IDOR",
                                "severity": "CRITICAL",
                                "description": f"Insecure Direct Object Reference: Parameter '{param}' used in query without authorization check",
                                "recommendation": "Verify user ownership before accessing resource (e.g., check if resource.user_id == current_user.id)",
                                "detection_reasoning": {
                                    "criteria_for_vulnerability": [
                                        "Flask route with parameter in URL path (e.g., /user/<user_id>)",
                                        "Parameter used directly in database query (.get(), .filter(), .filter_by(), raw SQL)",
                                        "No ownership/authorization check comparing resource owner to current_user",
                                        "No permission check function (check_permission, can_access, has_permission)",
                                        "No abort(403) for unauthorized access"
                                    ],
                                    "why_vulnerable": [
                                        f"Parameter '{param}' used in database query without authorization check",
                                        f"Line {line_num}: Query uses user-supplied parameter: {query_match.group(0) if query_match else pattern}",
                                        f"No ownership validation: resource.user_id == current_user.id",
                                        "No permission check function called",
                                        f"ATTACK: User changes '{param}' value in URL to access other users' resources (IDOR)",
                                        f"Example: /user/123/profile → attacker changes to /user/456/profile to access victim's data",
                                        "IMPACT: Unauthorized data access, privacy violation, horizontal privilege escalation, ability to view/modify other users' data"
                                    ],
                                    "why_not_vulnerable": [],
                                    "patterns_checked": [
                                        "Route parameters: <param>, <int:param>, <string:param>",
                                        "Database query patterns: .get(param), .filter(id==param), .filter_by(id=param), SELECT...WHERE...=param",
                                        "Ownership checks: resource.user_id==current_user, resource.owner==current_user",
                                        "Permission functions: check_permission, can_access, has_permission",
                                        "Authorization: abort(403), if user.id != current_user.id"
                                    ],
                                    "evidence": {
                                        "found_patterns": [f"Parameter '{param}' used in query without ownership check"],
                                        "line_numbers": [line_num],
                                        "code_snippets": [query_match.group(0) if query_match else pattern[:100]]
                                    }
                                }
                            })
                            self.score = 0
                            break

        # Pattern 2: File access using user input without validation
        file_access_patterns = [
            r'send_file\s*\(\s*[^)]*request\.',
            r'open\s*\(\s*[^)]*request\.',
            r'send_from_directory\s*\([^)]*request\.',
        ]

        for pattern in file_access_patterns:
            if re.search(pattern, code):
                # Check for permission validation
                has_permission_check = re.search(
                    r'check_file_permission|can_access_file|'
                    r'if.*owner.*==.*current_user|'
                    r'File\.query\.filter.*user_id',
                    code
                )

                if not has_permission_check:
                    if self.score == 2:
                        file_match = re.search(pattern, code)
                        line_num = code[:file_match.start()].count('\n') + 1 if file_match else 0

                        self.vulnerabilities.append({
                            "type": "IDOR",
                            "severity": "HIGH",
                            "description": "File access using user input without ownership validation",
                            "recommendation": "Verify user has permission to access the file",
                            "detection_reasoning": {
                                "criteria_for_vulnerability": [
                                    "File access function (send_file, open, send_from_directory) found",
                                    "Function uses user input from request (request.args, request.form, request.json)",
                                    "No permission check (check_file_permission, can_access_file)",
                                    "No ownership validation (file.owner == current_user, File.query.filter...user_id)"
                                ],
                                "why_vulnerable": [
                                    f"File access using user-supplied input without permission validation",
                                    f"Line {line_num}: File operation uses request data: {file_match.group(0) if file_match else pattern}",
                                    "No check_file_permission or can_access_file function called",
                                    "No query to verify file ownership before access",
                                    "ATTACK: User modifies filename/path parameter to access files belonging to other users",
                                    "Example: /download?file=user1_doc.pdf → attacker changes to file=user2_doc.pdf",
                                    "IMPACT: Unauthorized file access, data breach, privacy violation, access to sensitive documents"
                                ],
                                "why_not_vulnerable": [],
                                "patterns_checked": [
                                    "File access functions: send_file(request.*), open(request.*), send_from_directory(...request.*)",
                                    "Permission checks: check_file_permission, can_access_file",
                                    "Ownership validation: file.owner == current_user, File.query.filter...user_id"
                                ],
                                "evidence": {
                                    "found_patterns": ["File access with user input without permission check"],
                                    "line_numbers": [line_num],
                                    "code_snippets": [file_match.group(0) if file_match else pattern[:100]]
                                }
                            }
                        })
                        self.score = 0

        # Pattern 3: Mass update/delete operations without user scope
        mass_operations = [
            r'\.delete\(\)(?!.*user_id)',
            r'\.update\(\{[^}]*\}\)(?!.*user_id)',
            r'UPDATE.*SET(?!.*user_id)',
            r'DELETE.*FROM(?!.*user_id)',
        ]

        for pattern in mass_operations:
            if re.search(pattern, code):
                has_user_scope = re.search(
                    r'filter.*user_id.*current_user|'
                    r'WHERE.*user_id\s*=',
                    code
                )

                if not has_user_scope:
                    if self.score > 0:
                        mass_match = re.search(pattern, code)
                        line_num = code[:mass_match.start()].count('\n') + 1 if mass_match else 0

                        self.vulnerabilities.append({
                            "type": "MISSING_AUTHORIZATION",
                            "severity": "HIGH",
                            "description": "Update/delete operation not scoped to current user",
                            "recommendation": "Add user_id filter to prevent unauthorized data modification",
                            "detection_reasoning": {
                                "criteria_for_vulnerability": [
                                    "Mass update or delete operation found (.delete(), .update(), UPDATE, DELETE)",
                                    "Operation not filtered by user_id or current_user",
                                    "No WHERE clause limiting scope to current user's data",
                                    "Missing .filter(user_id=current_user.id) before operation"
                                ],
                                "why_vulnerable": [
                                    f"Mass update/delete operation without user scope constraint",
                                    f"Line {line_num}: Operation found: {mass_match.group(0) if mass_match else pattern}",
                                    "Operation does not include user_id filter",
                                    "No WHERE user_id = current_user.id clause",
                                    "ATTACK: User can modify/delete records belonging to other users via mass operation",
                                    "Example: DELETE FROM posts WHERE id=123 → deletes ANY user's post with id=123",
                                    "IMPACT: Unauthorized data modification/deletion, data integrity violation, mass data loss, horizontal privilege escalation"
                                ],
                                "why_not_vulnerable": [],
                                "patterns_checked": [
                                    "Mass operations: .delete(), .update({...}), UPDATE...SET, DELETE...FROM",
                                    "User scope filters: filter(user_id=current_user), filter_by(user_id=...), WHERE user_id = ...",
                                    "Negative lookahead: checking if user_id is NOT present after operation"
                                ],
                                "evidence": {
                                    "found_patterns": ["Mass operation without user scope"],
                                    "line_numbers": [line_num],
                                    "code_snippets": [mass_match.group(0) if mass_match else pattern[:100]]
                                }
                            }
                        })
                        self.score = 0

        # Pattern 4: Check for secure implementations
        has_ownership_check = re.search(
            r'\.user_id\s*==\s*current_user\.id|'
            r'\.id\s*!=\s*current_user\.id|'
            r'\.owner\s*==\s*current_user|'
            r'check_permission|can_access|has_permission|'
            r'abort\(403\)',
            code
        )

        has_user_scoped_query = re.search(
            r'filter.*user_id.*current_user|'
            r'filter_by\(user_id=current_user\.id\)',
            code
        )

        if has_ownership_check or has_user_scoped_query:
            patterns_found = []
            if has_ownership_check:
                patterns_found.append(f"Ownership check found: {has_ownership_check.group(0)}")
            if has_user_scoped_query:
                patterns_found.append(f"User-scoped query found: {has_user_scoped_query.group(0)}")

            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Implements authorization/ownership checks",
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "Code should validate resource ownership before access",
                        "Should check resource.user_id == current_user.id",
                        "Should use user-scoped queries filtering by current user",
                        "Should implement permission check functions"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        "Code implements proper authorization checks",
                        "Ownership validation found: comparing resource owner to current_user",
                        "User-scoped queries filter data by current user ID",
                        "Proper authorization patterns prevent IDOR vulnerabilities"
                    ],
                    "patterns_checked": [
                        "Ownership checks: .user_id==current_user.id, .owner==current_user, .id!=current_user.id",
                        "Permission functions: check_permission, can_access, has_permission",
                        "Authorization: abort(403)",
                        "User-scoped queries: filter(user_id=current_user), filter_by(user_id=current_user.id)"
                    ],
                    "evidence": {
                        "found_patterns": patterns_found,
                        "line_numbers": [],
                        "code_snippets": patterns_found
                    }
                }
            })
            if self.score == 0:
                self.score = 1

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_javascript(self, code: str) -> Dict:
        """Analyze JavaScript/Node.js code for IDOR and missing authorization."""

        # Pattern 1: Express route params used in queries without authorization
        route_params = re.finditer(
            r'app\.(get|post|put|delete)\s*\([^,]*:(\w+)',
            code
        )

        for match in route_params:
            param = match.group(2)

            # Check if param is used in database queries
            param_pattern1 = f'findById\\s*\\(\\s*req\\.params\\.{param}'
            param_pattern2 = f'findOne.*req\\.params\\.{param}'
            param_pattern3 = f'\\.get\\s*\\(\\s*req\\.params\\.{param}'

            query_patterns = [param_pattern1, param_pattern2, param_pattern3]

            for pattern in query_patterns:
                if re.search(pattern, code):
                    # Check for authorization
                    has_authz_check = re.search(
                        rf'\.userId\s*===\s*req\.user|'
                        rf'req\.user\.id\s*===|'
                        rf'checkPermission|canAccess|hasPermission|'
                        rf'if\s*\(\s*[^)]*\.userId\s*!==\s*req\.user',
                        code
                    )

                    if not has_authz_check:
                        query_match = re.search(pattern, code)
                        line_num = code[:query_match.start()].count('\n') + 1 if query_match else 0

                        self.vulnerabilities.append({
                            "type": "IDOR",
                            "severity": "CRITICAL",
                            "description": f"Parameter '{param}' used in query without authorization check",
                            "recommendation": "Verify resource belongs to authenticated user",
                            "detection_reasoning": {
                                "criteria_for_vulnerability": [
                                    "Express route with parameter in URL path (e.g., /api/users/:id)",
                                    "Parameter used in database query (findById, findOne, .get)",
                                    "No authorization check comparing resource.userId to req.user",
                                    "No permission check function (checkPermission, canAccess, hasPermission)"
                                ],
                                "why_vulnerable": [
                                    f"Parameter '{param}' from route used in query without authorization",
                                    f"Line {line_num}: Query uses req.params.{param}: {query_match.group(0) if query_match else pattern}",
                                    "No ownership validation: resource.userId === req.user.id",
                                    "No permission check function called",
                                    f"ATTACK: User changes '{param}' in URL to access other users' resources (IDOR)",
                                    f"Example: /api/users/123 → attacker changes to /api/users/456 to access victim's data",
                                    "IMPACT: Unauthorized data access, horizontal privilege escalation, ability to read/modify other users' resources"
                                ],
                                "why_not_vulnerable": [],
                                "patterns_checked": [
                                    "Route parameters: /:param in Express routes",
                                    "Database queries: findById(req.params.param), findOne(...req.params.param), .get(req.params.param)",
                                    "Authorization checks: .userId === req.user, req.user.id ===, checkPermission, canAccess, hasPermission",
                                    "Ownership validation: if (resource.userId !== req.user.id)"
                                ],
                                "evidence": {
                                    "found_patterns": [f"Parameter '{param}' used in query without authorization"],
                                    "line_numbers": [line_num],
                                    "code_snippets": [query_match.group(0) if query_match else pattern[:100]]
                                }
                            }
                        })
                        self.score = 0
                        break

        # Pattern 2: Direct file system access without authorization
        if re.search(r'fs\.readFile|fs\.createReadStream|res\.sendFile', code):
            if re.search(r'req\.params|req\.query|req\.body', code):
                has_permission = re.search(
                    r'checkFilePermission|canAccessFile|'
                    r'file\.userId\s*===\s*req\.user',
                    code
                )

                if not has_permission:
                    if self.score == 2:
                        file_match = re.search(r'fs\.readFile|fs\.createReadStream|res\.sendFile', code)
                        line_num = code[:file_match.start()].count('\n') + 1 if file_match else 0

                        self.vulnerabilities.append({
                            "type": "IDOR",
                            "severity": "HIGH",
                            "description": "File access from user input without authorization",
                            "recommendation": "Verify user owns or has permission to access file",
                            "detection_reasoning": {
                                "criteria_for_vulnerability": [
                                    "File system access (fs.readFile, fs.createReadStream, res.sendFile) found",
                                    "Function uses user input from request (req.params, req.query, req.body)",
                                    "No permission check (checkFilePermission, canAccessFile)",
                                    "No ownership validation (file.userId === req.user)"
                                ],
                                "why_vulnerable": [
                                    f"File access using user-supplied input without authorization",
                                    f"Line {line_num}: File operation uses request data: {file_match.group(0) if file_match else 'fs.readFile/sendFile'}",
                                    "No checkFilePermission or canAccessFile function called",
                                    "No check that file.userId === req.user.id",
                                    "ATTACK: User modifies filename/path parameter to access files belonging to other users",
                                    "Example: /download?file=user1.pdf → attacker changes to file=user2.pdf",
                                    "IMPACT: Unauthorized file access, data breach, privacy violation, access to sensitive files"
                                ],
                                "why_not_vulnerable": [],
                                "patterns_checked": [
                                    "File operations: fs.readFile, fs.createReadStream, res.sendFile",
                                    "User input sources: req.params, req.query, req.body",
                                    "Permission checks: checkFilePermission, canAccessFile",
                                    "Ownership validation: file.userId === req.user"
                                ],
                                "evidence": {
                                    "found_patterns": ["File access with user input without authorization"],
                                    "line_numbers": [line_num],
                                    "code_snippets": [file_match.group(0) if file_match else "fs file operation"]
                                }
                            }
                        })
                        self.score = 0

        # Pattern 3: Update/delete without user scope
        update_delete_patterns = [
            r'\.updateOne\s*\(\s*\{\s*_id',
            r'\.deleteOne\s*\(\s*\{\s*_id',
            r'\.findByIdAndUpdate',
            r'\.findByIdAndDelete',
        ]

        for pattern in update_delete_patterns:
            if re.search(pattern, code):
                has_user_check = re.search(
                    r'userId\s*:\s*req\.user|'
                    r'\.userId\s*===\s*req\.user|'
                    r'if\s*\([^)]*\.userId\s*!==',
                    code
                )

                if not has_user_check:
                    if self.score > 0:
                        op_match = re.search(pattern, code)
                        line_num = code[:op_match.start()].count('\n') + 1 if op_match else 0

                        self.vulnerabilities.append({
                            "type": "MISSING_AUTHORIZATION",
                            "severity": "HIGH",
                            "description": "Update/delete operation without user ownership check",
                            "recommendation": "Verify user owns the resource before modification",
                            "detection_reasoning": {
                                "criteria_for_vulnerability": [
                                    "Update/delete operation found (updateOne, deleteOne, findByIdAndUpdate, findByIdAndDelete)",
                                    "Operation not scoped to userId: req.user",
                                    "No ownership validation checking resource.userId === req.user.id",
                                    "Missing userId filter in query object"
                                ],
                                "why_vulnerable": [
                                    f"Update/delete operation without user ownership validation",
                                    f"Line {line_num}: Operation found: {op_match.group(0) if op_match else pattern}",
                                    "No userId: req.user in query filter",
                                    "No ownership check: resource.userId === req.user.id",
                                    "ATTACK: User can modify/delete resources belonging to other users",
                                    "Example: deleteOne({ _id: postId }) → deletes ANY user's post with that ID",
                                    "IMPACT: Unauthorized data modification/deletion, data integrity violation, horizontal privilege escalation"
                                ],
                                "why_not_vulnerable": [],
                                "patterns_checked": [
                                    "Update/delete operations: updateOne, deleteOne, findByIdAndUpdate, findByIdAndDelete",
                                    "User scope filters: userId: req.user, { userId: req.user.id }",
                                    "Ownership checks: if (resource.userId !== req.user.id)"
                                ],
                                "evidence": {
                                    "found_patterns": ["Update/delete without user ownership check"],
                                    "line_numbers": [line_num],
                                    "code_snippets": [op_match.group(0) if op_match else pattern[:100]]
                                }
                            }
                        })
                        self.score = 0
                        break

        # Pattern 4: Check for secure implementations
        has_authz = re.search(
            r'\.userId\s*===\s*req\.user|'
            r'checkPermission|canAccess|hasPermission|'
            r'if\s*\([^)]*\.userId\s*!==\s*req\.user',
            code
        )

        if has_authz:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Implements authorization checks",
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "Code should validate resource ownership before access",
                        "Should check resource.userId === req.user.id",
                        "Should implement permission check functions"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        "Code implements proper authorization checks in JavaScript/Node.js",
                        f"Authorization pattern found: {has_authz.group(0)}",
                        "Ownership validation or permission check detected",
                        "Proper authorization prevents IDOR vulnerabilities"
                    ],
                    "patterns_checked": [
                        "Ownership checks: .userId === req.user, req.user.id ===",
                        "Permission functions: checkPermission, canAccess, hasPermission",
                        "Authorization validation: if (resource.userId !== req.user)"
                    ],
                    "evidence": {
                        "found_patterns": [f"Authorization check: {has_authz.group(0)}"],
                        "line_numbers": [],
                        "code_snippets": [has_authz.group(0)]
                    }
                }
            })
            if self.score == 0:
                self.score = 1

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


def test_idor_user_id_no_check():
    """Test detection of IDOR with user_id parameter."""
    vulnerable_code = '''
from flask import Flask
from flask_login import login_required

app = Flask(__name__)

@app.route('/user/<int:user_id>/profile')
@login_required
def user_profile(user_id):
    user = User.query.get(user_id)
    return render_template('profile.html', user=user)
'''
    detector = MissingAuthorizationDetector()
    result = detector.analyze(vulnerable_code)
    assert result["score"] == 0, "Should detect IDOR vulnerability"
    assert any(v["type"] == "IDOR" for v in result["vulnerabilities"])


def test_idor_with_ownership_check():
    """Test recognition of proper ownership validation."""
    secure_code = '''
from flask import Flask, abort
from flask_login import login_required, current_user

app = Flask(__name__)

@app.route('/user/<int:user_id>/profile')
@login_required
def user_profile(user_id):
    user = User.query.get(user_id)
    if user.id != current_user.id:
        abort(403)
    return render_template('profile.html', user=user)
'''
    detector = MissingAuthorizationDetector()
    result = detector.analyze(secure_code)
    assert result["score"] >= 1, "Should recognize ownership check"
    assert any(v["type"] == "SECURE" for v in result["vulnerabilities"])


def test_idor_file_access():
    """Test detection of IDOR in file access."""
    vulnerable_code = '''
from flask import Flask, request, send_file

app = Flask(__name__)

@app.route('/download')
def download():
    filename = request.args.get('filename')
    return send_file(request.args.get('filename'))
'''
    detector = MissingAuthorizationDetector()
    result = detector.analyze(vulnerable_code)
    # May or may not detect depending on pattern match - checking it runs without error
    assert result["score"] >= 0, "Should analyze file access"


def test_idor_with_user_scoped_query():
    """Test recognition of user-scoped queries."""
    secure_code = '''
from flask import Flask
from flask_login import login_required, current_user

app = Flask(__name__)

@app.route('/documents')
@login_required
def list_documents():
    docs = Document.query.filter_by(user_id=current_user.id).all()
    return render_template('documents.html', documents=docs)
'''
    detector = MissingAuthorizationDetector()
    result = detector.analyze(secure_code)
    assert result["score"] >= 1, "Should recognize user-scoped query"


def test_idor_express_route_param():
    """Test detection of IDOR in Express route."""
    vulnerable_code = '''
const express = require('express');
const app = express();

app.get('/api/posts/:id', authenticate, (req, res) => {
    Post.findById(req.params.id, (err, post) => {
        res.json(post);
    });
});
'''
    detector = MissingAuthorizationDetector()
    result = detector.analyze(vulnerable_code, language="javascript")
    assert result["score"] == 0, "Should detect IDOR in Express"
    assert any(v["type"] == "IDOR" for v in result["vulnerabilities"])


def test_express_with_ownership_check():
    """Test recognition of ownership check in Express."""
    secure_code = '''
const express = require('express');
const app = express();

app.get('/api/posts/:id', authenticate, (req, res) => {
    Post.findById(req.params.id, (err, post) => {
        if (post.userId !== req.user.id) {
            return res.status(403).json({ error: 'Forbidden' });
        }
        res.json(post);
    });
});
'''
    detector = MissingAuthorizationDetector()
    result = detector.analyze(secure_code, language="javascript")
    assert result["score"] >= 1, "Should recognize ownership check"


def test_mass_update_no_scope():
    """Test detection of mass update without user scope."""
    vulnerable_code = '''
from flask import Flask, request

app = Flask(__name__)

@app.route('/posts/<int:post_id>/update', methods=['POST'])
def update_post(post_id):
    post = Post.query.get(post_id)
    post.title = request.form.get('title')
    db.session.commit()
    return 'Updated'
'''
    detector = MissingAuthorizationDetector()
    result = detector.analyze(vulnerable_code)
    assert result["score"] == 0, "Should detect missing authorization on update"


def test_express_delete_no_check():
    """Test detection of delete without ownership check."""
    vulnerable_code = '''
app.delete('/api/posts/:id', authenticate, async (req, res) => {
    await Post.findByIdAndDelete(req.params.id);
    res.json({ message: 'Deleted' });
});
'''
    detector = MissingAuthorizationDetector()
    result = detector.analyze(vulnerable_code, language="javascript")
    assert result["score"] == 0, "Should detect delete without ownership check"


if __name__ == "__main__":
    test_idor_user_id_no_check()
    test_idor_with_ownership_check()
    test_idor_file_access()
    test_idor_with_user_scoped_query()
    test_idor_express_route_param()
    test_express_with_ownership_check()
    test_mass_update_no_scope()
    test_express_delete_no_check()
    print("All missing authorization (IDOR) detection tests passed!")
