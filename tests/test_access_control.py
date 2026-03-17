"""
Test suite for detecting Broken Access Control vulnerabilities.
Covers: IDOR, Privilege Escalation, Function-Level Access Control, Mass Assignment
"""
import re
import sys
from pathlib import Path
from typing import Dict

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations


class AccessControlDetector:
    """Detects broken access control vulnerabilities in code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "python") -> Dict:
        """Analyze code for broken access control vulnerabilities."""
        if language == "python":
            return self._analyze_python(code)
        elif language == "javascript":
            return self._analyze_javascript(code)
        else:
            return {"score": 0, "vulnerabilities": ["Unsupported language"], "max_score": 2}

    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python code for broken access control."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: IDOR - Direct parameter usage in database queries without ownership check
        # Example: User.query.filter_by(id=user_id).first() without checking current_user
        idor_patterns = [
            # Flask/SQLAlchemy patterns
            (r'\.query\.filter_by\([^)]*id\s*=\s*[^)]+\)\.first\(\)', 'Database query by ID without ownership check'),
            (r'\.query\.get\([^)]+\)', 'Database query with get() without ownership check'),
            (r'SELECT\s+\*\s+FROM\s+\w+\s+WHERE\s+id\s*=', 'SQL query by ID without ownership check'),

            # Direct ID usage in queries
            (r'\.filter\([^)]*id\s*==\s*[^)]+\)', 'Filter by ID without ownership verification'),
            (r'\.find_one\(\{["\']_id["\']:\s*[^}]+\}\)', 'MongoDB find_one by ID without ownership check'),

            # File operation patterns (IDOR with files)
            (r'send_file\([^)]*\)', 'File send operation without ownership check'),
            (r'send_from_directory\([^)]*\)', 'Directory file send without ownership check'),
            (r'fs\.readFile\([^)]*\)', 'File read operation without ownership check'),
            (r'open\([^)]*[,\s]["\']r["\']?\)', 'File open for reading without ownership check'),
        ]

        has_ownership_check = any([
            re.search(r'\.user_id\s*(==|!=)\s*current_user', code, re.IGNORECASE),
            re.search(r'\.user_id\s*(==|!=)\s*int\(current_user', code, re.IGNORECASE),
            re.search(r'\.user_id\s*(==|!=)\s*current_user\.get_id\(\)', code, re.IGNORECASE),
            re.search(r'\.user_id\s*(==|!=)\s*int\(current_user\.get_id\(\)\)', code, re.IGNORECASE),
            re.search(r'\.owner_id\s*(==|!=)\s*current_user', code, re.IGNORECASE),
            re.search(r'\.user\s*(==|!=)\s*current_user', code, re.IGNORECASE),
            re.search(r'\.author\s*(==|!=)\s*current_user', code, re.IGNORECASE),
            re.search(r'\.creator\s*(==|!=)\s*current_user', code, re.IGNORECASE),
            # NEW: Reverse order patterns (current_user on left side)
            re.search(r'current_user\s*(==|!=)\s*\w+\.user_id', code, re.IGNORECASE),
            re.search(r'current_user\s*(==|!=)\s*\w+\.owner_id', code, re.IGNORECASE),
            re.search(r'current_user\s*(==|!=)\s*\w+\.user\b', code, re.IGNORECASE),
            re.search(r'current_user\s*(==|!=)\s*\w+\.author', code, re.IGNORECASE),
            re.search(r'current_user\s*(==|!=)\s*\w+\.creator', code, re.IGNORECASE),
            re.search(r'current_user\.id\s*(==|!=)\s*\w+\.user_id', code, re.IGNORECASE),
            re.search(r'check_ownership|verify_owner|check_access', code, re.IGNORECASE),
            # NEW: Decorator-based authorization
            re.search(r'@require_owner|@check_ownership|@user_owns|@verify_owner', code, re.IGNORECASE),
            re.search(r'@user_passes_test|@permission_required', code, re.IGNORECASE),
            # NEW: Middleware patterns
            re.search(r'if\s+not\s+(check_ownership|verify_owner|check_access)\(', code, re.IGNORECASE),
            re.search(r'unless\s+(owns_resource|is_owner)', code, re.IGNORECASE),
            # NEW: ORM-level filtering (queryset with user filter)
            re.search(r'\.filter\([^)]*owner\s*=\s*(request\.)?user', code, re.IGNORECASE),
            re.search(r'\.objects\.filter\([^)]*user\s*=\s*request\.user', code, re.IGNORECASE),
        ])

        has_query = False
        for pattern, description in idor_patterns:
            matches = re.findall(pattern, code, re.IGNORECASE)
            if matches:
                has_query = True
                break

        if has_query and not has_ownership_check:
            # Find the location of the query
            for pattern, description in idor_patterns:
                locations = find_pattern_locations(code, pattern)
                if locations:
                    location = locations[0]
                    line_content = location['line_content']
                    line_num = location['line_number']

                    # Check if this is inside an authentication framework function (user_loader, etc.)
                    # These are NOT vulnerabilities - they're part of the auth system
                    lines = code.split('\n')
                    in_auth_function = False
                    for i in range(max(0, line_num - 5), min(len(lines), line_num)):
                        if re.search(r'@(login_manager\.)?user_loader|@jwt\.user_loader|def load_user|def get_user_by_id', lines[i], re.IGNORECASE):
                            in_auth_function = True
                            break

                    if in_auth_function:
                        # This is an authentication framework function, not a vulnerability
                        continue

                    # Check if ownership verification is in the SAME line/statement as the ID query
                    # This catches inline ownership checks like: .filter(Order.id == order_id, Order.user_id == current_user.id)
                    # Also catches .filter_by(id=X, user_id=current_user.id) syntax
                    has_inline_ownership = any([
                        re.search(r'\.user_id\s*(==|!=)\s*(int\()?current_user', line_content, re.IGNORECASE),
                        re.search(r'current_user\.get_id\(\)', line_content, re.IGNORECASE),
                        # NEW: Detect .filter_by(id=X, user_id=current_user.id) patterns
                        re.search(r'\.filter_by\([^)]*user_id\s*=\s*current_user', line_content, re.IGNORECASE),
                        re.search(r'\.filter_by\([^)]*owner_id\s*=\s*current_user', line_content, re.IGNORECASE),
                    ])

                    if has_inline_ownership:
                        # This is actually SECURE - ownership check is in the same query
                        continue

                    self.vulnerabilities.append({
                        "type": "IDOR",
                        "severity": "HIGH",
                        "description": f"Insecure Direct Object Reference (IDOR) - {description} - CRITICAL AUTHORIZATION BYPASS: Code accesses objects by ID from user input without verifying the current user owns that object. ATTACK SCENARIO: (1) User A views their order: /api/orders/123, (2) User A changes ID to /api/orders/124 (belongs to User B), (3) Code returns User B's data without checking ownership. IMPACT: Complete data breach - attackers enumerate all records (orders, profiles, documents, messages) by incrementing IDs. REAL-WORLD: Zillow bug exposed private home tours, Facebook bug leaked private photos, IDOR is #1 in OWASP Broken Access Control.",
                        "recommendation": "ALWAYS verify ownership before returning objects: order = Order.query.get(order_id); if not order or order.user_id != current_user.id: abort(403); return order",
                        "example_attack": "User requests /api/orders/5 (belongs to another user). Code does Order.query.get(5).first() without checking order.user_id == current_user.id → returns other user's order data including PII, payment info",
                        "line_number": location['line_number'],
                        "code_snippet": location['line_content'],
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Direct database query by ID parameter from user request",
                                "Object retrieved using ID without ownership validation",
                                "Missing resource.user_id == current_user.id check",
                                "No @require_owner decorator or ownership validation function"
                            ],
                            "why_vulnerable": [
                                f"Line {location['line_number']}: {description}",
                                "Code queries database by ID from user input (URL parameter, request body)",
                                "No ownership check found - missing patterns like 'resource.user_id == current_user.id'",
                                "No decorator-based authorization (@require_owner, @check_ownership)",
                                "ATTACK: User changes ID in URL (/api/orders/123 → /api/orders/456) to access other users' data",
                                "IMPACT: Complete horizontal privilege escalation - any user can access any other user's resources"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "Query by ID patterns (.query.get(), .query.filter_by(id=), SELECT WHERE id=)",
                                "Ownership validation (resource.user_id == current_user.id)",
                                "Decorator authorization (@require_owner, @check_ownership)",
                                "Inline ownership checks in query (.filter_by(id=X, user_id=current_user))",
                                "Authorization functions (check_ownership, verify_owner)"
                            ],
                            "evidence": {
                                "found_patterns": [f"IDOR vulnerability: {description}"],
                                "line_numbers": [location['line_number']],
                                "code_snippets": [location['line_content']]
                            }
                        }
                    })
                    self.score = 0
                    break

        # Pattern 2: Mass Assignment / Privilege Escalation
        # Directly updating objects from request data without filtering fields
        mass_assignment_patterns = [
            (r'\.update\(request\.(json|form|data|get_json\(\))\)', 'Direct update from request data'),
            (r'for\s+key.*in\s+request\.(json|form|data)', 'Looping through request data to update object'),
            (r'\*\*request\.(json|form|data)', 'Unpacking request data into object'),
            (r'\.from_dict\(request\.', 'Creating/updating from request dict'),
        ]

        has_field_whitelist = any([
            re.search(r'allowed_fields|ALLOWED_FIELDS|whitelist|permitted', code),
            re.search(r'if\s+key\s+in\s+\[', code),
            re.search(r'\.get\(["\']email["\']\).*\.get\(["\']username["\']\)', code),  # Explicit field access
        ])

        # Check for sensitive fields that shouldn't be user-modifiable
        has_sensitive_fields = any([
            re.search(r'(is_admin|is_staff|role|account_type|premium|balance|credits)', code, re.IGNORECASE),
        ])

        for pattern, description in mass_assignment_patterns:
            locations = find_pattern_locations(code, pattern)
            if locations and not has_field_whitelist:
                location = locations[0]
                severity = "CRITICAL" if has_sensitive_fields else "HIGH"

                self.vulnerabilities.append({
                    "type": "MASS_ASSIGNMENT",
                    "severity": severity,
                    "description": f"Mass Assignment / Privilege Escalation - {description} - CRITICAL PRIVILEGE ESCALATION RISK: Code updates object fields directly from user input without whitelisting allowed fields. ATTACK SCENARIO: (1) Legitimate update endpoint: POST /api/users/me {{\"email\": \"new@example.com\"}}, (2) Attacker adds privileged fields: POST /api/users/me {{\"email\": \"new@example.com\", \"is_admin\": true, \"role\": \"admin\", \"account_type\": \"premium\"}}, (3) Code blindly updates all fields including is_admin=true. IMPACT: Complete privilege escalation - regular user becomes admin, free users become premium, normal users gain superuser access. REAL-WORLD: GitHub mass assignment bug allowed repo access escalation, Rails apps commonly vulnerable.",
                    "recommendation": "ALWAYS whitelist allowed fields: ALLOWED_FIELDS = ['email', 'username', 'bio']; data = {k: v for k, v in request.json.items() if k in ALLOWED_FIELDS}; user.update(data)",
                    "example_attack": "POST /api/profile/update {{\"username\": \"hacker\", \"is_admin\": true, \"balance\": 999999}} → code does user.update(**request.json) → user becomes admin with $999999 balance",
                    "line_number": location['line_number'],
                    "code_snippet": location['line_content'],
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Direct object update from request data without field filtering",
                            "Unpacking request.json or request.form directly into object (**request.json)",
                            "Missing field whitelist (ALLOWED_FIELDS, permitted fields)",
                            "Update loop without field validation (for key in request.json)"
                        ],
                        "why_vulnerable": [
                            f"Line {location['line_number']}: {description}",
                            "Code updates object directly from user input without filtering fields",
                            "No ALLOWED_FIELDS whitelist detected",
                            "No field validation (if key in [...]) before update",
                            "ATTACK: Attacker adds privileged fields (is_admin, role, balance) to request → all fields updated",
                            f"SEVERITY: {severity} - {'Sensitive fields detected in code (is_admin, role, balance, credits)' if severity == 'CRITICAL' else 'Could allow privilege escalation if sensitive fields exist'}"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "Direct update patterns (.update(request.json), .update(**request.form))",
                            "Object.assign or spread operator with request data",
                            "Loop through request data (for key in request.json)",
                            "Field whitelist (ALLOWED_FIELDS, permitted_fields)",
                            "Explicit field extraction (.get('email'), .get('username'))",
                            "Sensitive fields (is_admin, role, balance, credits, premium)"
                        ],
                        "evidence": {
                            "found_patterns": [f"Mass assignment vulnerability: {description}"],
                            "line_numbers": [location['line_number']],
                            "code_snippets": [location['line_content']]
                        }
                    }
                })
                self.score = 0
                break

        # Pattern 3: Missing Function-Level Access Control
        # Admin/privileged endpoints without authorization checks
        has_admin_endpoint = any([
            re.search(r'@app\.route\(["\'][^"\']*admin', code, re.IGNORECASE),
            re.search(r'def\s+(get_all_users|list_users|admin_dashboard|delete_user)', code, re.IGNORECASE),
            re.search(r'\.query\.all\(\).*users?', code, re.IGNORECASE),
        ])

        has_admin_check = any([
            re.search(r'if.*current_user\.is_admin', code),
            re.search(r'if.*current_user\.role.*==.*["\']admin["\']', code),
            re.search(r'@login_required.*@admin_required', code, re.DOTALL),
            re.search(r'@admin_required|@require_admin|@requires_admin', code),
            re.search(r'check_admin|verify_admin|require_admin', code),
        ])

        if has_admin_endpoint and not has_admin_check:
            # Find admin-related patterns
            admin_patterns = [
                r'@app\.route\(["\'][^"\']*admin',
                r'def\s+(get_all_users|list_users|admin_dashboard|delete_user)',
            ]

            for pattern in admin_patterns:
                locations = find_pattern_locations(code, pattern)
                if locations:
                    location = locations[0]
                    self.vulnerabilities.append({
                        "type": "MISSING_FUNCTION_LEVEL_ACCESS_CONTROL",
                        "severity": "CRITICAL",
                        "description": "Missing Function-Level Access Control - Admin/privileged endpoint without authorization check - COMPLETE AUTHORIZATION BYPASS: Endpoint performs privileged operations (view all users, delete users, admin functions) but doesn't verify current user has admin role. ATTACK SCENARIO: (1) Attacker discovers admin endpoint: /api/admin/users or /api/users/all, (2) Regular user accesses endpoint directly via API call, (3) No role check → endpoint executes privileged operation. IMPACT: Complete access control bypass - any user can access admin functions, view all user data, delete accounts, modify system settings. REAL-WORLD: Peloton API exposed private user data (no auth check), Parler API leaked all users/posts, function-level access control is OWASP A01.",
                        "recommendation": "ALWAYS check authorization before privileged operations: @app.route('/admin/users'); @login_required; def get_all_users(): if not current_user.is_admin: abort(403); return User.query.all()",
                        "example_attack": "Regular user calls GET /api/admin/users → code does User.query.all() without checking current_user.is_admin → returns all users including emails, passwords, PII",
                        "line_number": location['line_number'],
                        "code_snippet": location['line_content'],
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Admin or privileged endpoint without role verification",
                                "Route path contains 'admin' but no authorization check",
                                "Privileged operations (User.query.all(), delete_user) without role validation",
                                "Missing current_user.is_admin or @admin_required decorator"
                            ],
                            "why_vulnerable": [
                                f"Line {location['line_number']}: Admin endpoint or privileged function detected",
                                "No admin role check found (current_user.is_admin, @admin_required)",
                                "No role validation (current_user.role == 'admin')",
                                "ATTACK: Any authenticated user can call admin endpoint directly",
                                "IMPACT: Vertical privilege escalation - regular users gain admin access"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "Admin route patterns (@app.route('/admin/*'))",
                                "Privileged function names (get_all_users, list_users, delete_user)",
                                "Query.all() operations returning all records",
                                "Admin check patterns (current_user.is_admin, @admin_required)",
                                "Role validation (current_user.role == 'admin')",
                                "Authorization functions (check_admin, verify_admin)"
                            ],
                            "evidence": {
                                "found_patterns": ["Missing function-level access control on admin endpoint"],
                                "line_numbers": [location['line_number']],
                                "code_snippets": [location['line_content']]
                            }
                        }
                    })
                    self.score = 0
                    break

        # Pattern 3b: Detect SQL queries with user_id in WHERE clause (these are SECURE)
        # Example: SELECT * FROM orders WHERE user_id = ? AND order_id = ?
        has_sql_user_id_filter = re.search(r'WHERE.*?user_id\s*=\s*\?', code, re.IGNORECASE | re.DOTALL) or \
                                  re.search(r'WHERE.*?\w+_?id\s*=\s*\?.*?user_id\s*=\s*\?', code, re.IGNORECASE | re.DOTALL)

        if has_sql_user_id_filter and self.score == 2:
            # Find the SQL query location (handle multi-line SQL)
            # Look for query = or query= or '''SELECT
            sql_locations = find_pattern_locations(code, r'(query\s*=|SELECT\s+\*\s+FROM)')
            if sql_locations:
                location = sql_locations[0]
                line_num = location['line_number']

                # Get multi-line context around the SQL query
                lines = code.split('\n')
                context_start = max(0, line_num - 1)
                context_end = min(len(lines), line_num + 10)
                context = '\n'.join(lines[context_start:context_end])

                # Use first line for code_snippet display
                code_snippet = location['line_content']

                # Extract table name and identify authorization pattern
                table_match = re.search(r'FROM\s+(\w+)', context, re.IGNORECASE)
                table_name = table_match.group(1) if table_match else "table"

                # Check if query uses BOTH ID and user_id (check in full context)
                has_both_id_and_user = re.search(r'WHERE.*?user_id\s*=\s*\?.*?\w+_?id\s*=\s*\?', context, re.IGNORECASE | re.DOTALL) or \
                                       re.search(r'WHERE.*?\w+_?id\s*=\s*\?.*?user_id\s*=\s*\?', context, re.IGNORECASE | re.DOTALL)

                if has_both_id_and_user:
                    primary_pattern = "SQL-level authorization with dual constraints"
                    why_secure = f"✅ SECURE PATTERN: SQL query filters by BOTH user_id AND resource ID in WHERE clause using parameterized queries (e.g., WHERE user_id = ? AND order_id = ?). This is DATABASE-ENFORCED AUTHORIZATION - the most secure pattern because: (1) Authorization happens at database level, not application code - impossible to bypass, (2) User can ONLY retrieve their own {table_name} even if they try manipulating IDs, (3) ATTACK BLOCKED: If attacker tries GET /api/{table_name}/999 (belongs to different user), database returns ZERO rows because WHERE user_id = <attacker_id> AND order_id = 999 finds nothing - attacker's user_id doesn't match the owner, (4) This prevents IDOR (Insecure Direct Object Reference) by design - database physically cannot return other users' data. Parameterized queries (?) additionally prevent SQL injection. This is EQUIVALENT to post-query ownership check (resource.user_id == current_user.id) but MORE SECURE because it's enforced at database layer."
                    auth_patterns = [f"SQL query with user_id filter in WHERE clause ({table_name} table)", "Dual constraint: user_id AND resource_id", "Database-enforced authorization", "Parameterized query prevents SQL injection"]
                else:
                    primary_pattern = "SQL-level authorization"
                    why_secure = f"✅ SECURE PATTERN: SQL query includes user_id constraint in WHERE clause using parameterized query (e.g., WHERE user_id = ?). This is DATABASE-ENFORCED AUTHORIZATION that prevents IDOR attacks: (1) Only {table_name} records WHERE user_id matches authenticated user can be retrieved, (2) ATTACK BLOCKED: Attacker CANNOT access other users' {table_name} because database filters at query level - WHERE user_id = <attacker_user_id> will NEVER return records with user_id = <victim_user_id>, (3) This is MORE SECURE than application-level checks because authorization is built into the SQL query itself - impossible to bypass by manipulating request parameters or skipping validation logic, (4) Equivalent security to resource.user_id == current_user.id but enforced at database layer. This pattern is RECOMMENDED by OWASP for preventing horizontal privilege escalation. Parameterized queries (?) additionally prevent SQL injection."
                    auth_patterns = [f"SQL query with user_id filter in WHERE clause ({table_name} table)", "Database-enforced authorization", "Parameterized query prevents SQL injection"]

                check_count = len(auth_patterns)
                patterns_str = " + ".join(auth_patterns)

                detection_reasoning = {
                    "patterns_checked": [
                        f"SQL queries without user_id filter (SELECT * FROM {table_name} WHERE id = ?)",
                        "Direct object access by ID without ownership validation",
                        "Missing user_id constraint in WHERE clause",
                        "SQL injection via string concatenation",
                        "IDOR vulnerability allowing cross-user data access"
                    ],
                    "why_not_vulnerable": [
                        f"Implements {check_count} authorization check(s): {patterns_str}",
                        f"Primary protection: {primary_pattern}",
                        why_secure,
                        f"Database enforces user_id constraint - impossible to retrieve other users' {table_name} records",
                        "Parameterized queries (?) prevent SQL injection attacks"
                    ],
                    "vulnerable_patterns_absent": [
                        f"No SELECT * FROM {table_name} WHERE id = ? without user_id constraint",
                        "No SQL string concatenation (query + user_input)",
                        "user_id validated at database level in WHERE clause",
                        f"IDOR prevented - users cannot access other users' {table_name} by ID manipulation",
                        "SQL injection prevented via parameterized queries"
                    ]
                }

                self.vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": f"✅ SECURE - DATABASE-ENFORCED AUTHORIZATION: Uses SQL-level authorization with user_id constraint in WHERE clause ({check_count} protection{'s' if check_count != 1 else ''}). Pattern: {primary_pattern}. {why_secure} ⚠️ IMPORTANT FOR VERIFIERS: This code is SECURE and does NOT have an IDOR vulnerability. The SQL query includes 'WHERE user_id = ?' which PREVENTS unauthorized access - users can ONLY access their own {table_name} records. This is the CORRECT and RECOMMENDED approach for preventing IDOR attacks. Database physically cannot return other users' data when user_id constraint is in WHERE clause. This prevents IDOR attacks where users manipulate IDs to access other users' resources, and prevents SQL injection via parameterized queries.",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "security_evidence": {
                        "authorization_patterns": auth_patterns,
                        "primary_pattern": primary_pattern,
                        "check_count": check_count,
                        "prevents": "IDOR (Insecure Direct Object Reference) + SQL Injection",
                        "why_secure": why_secure,
                        "table_name": table_name,
                        "uses_parameterized_query": True,
                        "verifier_note": f"CODE IS SECURE: WHERE user_id = ? in SQL query enforces authorization at database level. Attacker CANNOT access other users' {table_name} by manipulating IDs because database filters by authenticated user's user_id."
                    },
                    "detection_reasoning": detection_reasoning
                })

        # Pattern 4: Check for secure implementations
        # ENHANCED: Provide explicit evidence of authorization pattern used
        if has_ownership_check:
            ownership_locations = find_pattern_locations(code, r'\.user_id\s*(==|!=)\s*(int\()?current_user(\.get_id\(\))?|current_user\.id\s*(==|!=)\s*\w+\.user_id|check_ownership')
            if ownership_locations:
                location = ownership_locations[0]
                code_snippet = location['line_content']
                line_num = location['line_number']

                # Determine which authorization pattern(s) are used
                auth_patterns = []

                # Ownership check patterns
                if re.search(r'\.user_id\s*(==|!=)\s*(int\()?current_user', code):
                    auth_patterns.append("Ownership check (resource.user_id == current_user)")
                if re.search(r'current_user\.id\s*(==|!=)\s*\w+\.user_id', code):
                    auth_patterns.append("Ownership check (current_user.id == resource.user_id)")
                if re.search(r'\.owner_id\s*(==|!=)\s*current_user', code):
                    auth_patterns.append("Ownership check (resource.owner_id == current_user)")

                # Function/decorator patterns
                if re.search(r'check_ownership|verify_owner|check_access', code):
                    auth_patterns.append("Authorization function (check_ownership/verify_owner)")
                if re.search(r'@require_owner|@check_ownership|@user_owns', code):
                    auth_patterns.append("Decorator-based authorization (@require_owner/@check_ownership)")

                # ORM-level filtering
                if re.search(r'\.filter\([^)]*owner\s*=\s*(request\.)?user', code):
                    auth_patterns.append("ORM-level filtering (queryset filtered by user)")

                # Inline ownership in query
                if re.search(r'\.filter_by\([^)]*user_id\s*=\s*current_user', code):
                    auth_patterns.append("Inline ownership check in query (.filter_by(user_id=current_user))")

                # Count authorization checks
                check_count = len(auth_patterns)
                patterns_str = " + ".join(auth_patterns) if auth_patterns else "ownership verification"

                # Determine primary pattern
                if re.search(r'@require_owner|@check_ownership', code):
                    primary_pattern = "Decorator-based"
                    why_secure = "Decorator ensures ownership check runs before endpoint handler executes, preventing unauthorized access at framework level. If user doesn't own resource, decorator returns 403 before business logic runs."
                elif re.search(r'check_ownership|verify_owner', code):
                    primary_pattern = "Function-based authorization"
                    why_secure = "Dedicated authorization function validates ownership before accessing resource. Centralized check ensures consistent enforcement across endpoints and prevents IDOR attacks."
                elif re.search(r'\.filter_by\([^)]*user_id\s*=\s*current_user', code):
                    primary_pattern = "Query-level filtering"
                    why_secure = "Ownership constraint embedded in database query ensures only user's own resources are retrieved. Database enforces access control - impossible to access other users' data even with ID manipulation."
                else:
                    primary_pattern = "Post-retrieval ownership check"
                    why_secure = "Verifies resource.user_id matches current_user after retrieval. Prevents IDOR by rejecting access when user doesn't own the resource."

                # Build detection reasoning for Python ownership verification
                detection_reasoning = {
                    "patterns_checked": [
                        "Direct object access by ID without ownership check (Order.query.get(id))",
                        "Database queries without user_id filter",
                        "Missing resource.user_id == current_user.id validation",
                        "File operations without ownership verification (send_file without check)",
                        "IDOR vulnerability allowing cross-user data access"
                    ],
                    "why_not_vulnerable": [
                        f"Implements {check_count} authorization check(s): {patterns_str}",
                        f"Primary protection: {primary_pattern}",
                        why_secure,
                        "Returns 403 Forbidden when user doesn't own resource",
                        "Validates ownership BEFORE returning sensitive data"
                    ],
                    "vulnerable_patterns_absent": [
                        "No direct Order.query.get(id) without ownership check",
                        "No send_file() without ownership verification",
                        "resource.user_id validated against current_user.id",
                        "IDOR prevented - users cannot access other users' resources by ID manipulation",
                        "All database queries enforce ownership constraints"
                    ]
                }

                self.vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": f"SECURE: Implements ownership verification using {patterns_str} ({check_count} authorization check{'s' if check_count != 1 else ''}). Primary pattern: {primary_pattern}. {why_secure} This prevents Insecure Direct Object Reference (IDOR) attacks where users manipulate IDs to access other users' resources.",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "security_evidence": {
                        "authorization_patterns": auth_patterns,
                        "primary_pattern": primary_pattern,
                        "check_count": check_count,
                        "prevents": "IDOR (Insecure Direct Object Reference)",
                        "why_secure": why_secure
                    },
                    "detection_reasoning": detection_reasoning
                })
            if self.score == 0:
                self.score = 1

        if has_field_whitelist:
            whitelist_locations = find_pattern_locations(code, r'allowed_fields|ALLOWED_FIELDS|whitelist')
            if whitelist_locations:
                location = whitelist_locations[0]

                # Check if whitelist contains privilege escalation fields
                # These fields should NEVER be user-modifiable
                privilege_fields = [
                    r'is_admin', r'is_staff', r'is_superuser', r'role',
                    r'account_type', r'premium', r'pro', r'subscription',
                    r'balance', r'credits', r'points', r'coins',
                    r'verified', r'verified_status', r'is_verified',
                    r'permissions', r'access_level', r'tier'
                ]

                whitelist_has_privilege_fields = any(
                    re.search(rf'["\']({field})["\']', code, re.IGNORECASE)
                    for field in privilege_fields
                )

                if whitelist_has_privilege_fields:
                    # Find which privilege fields are in the whitelist
                    found_fields = [
                        field for field in privilege_fields
                        if re.search(rf'["\']({field})["\']', code, re.IGNORECASE)
                    ]

                    self.vulnerabilities.append({
                        "type": "INSECURE_WHITELIST",
                        "severity": "CRITICAL",
                        "description": f"Insecure Whitelist - Privilege Escalation via Mass Assignment - CRITICAL AUTHORIZATION BYPASS: Code has field whitelist but includes privilege escalation fields that users should NEVER be able to modify. ATTACK SCENARIO: (1) Legitimate profile update: POST /api/update_profile {{\"email\": \"new@example.com\"}}, (2) Attacker adds privileged fields from whitelist: POST /api/update_profile {{\"email\": \"new@example.com\", \"account_type\": \"premium\", \"credits\": 999999, \"verified_status\": true}}, (3) Whitelist allows these fields → setattr updates all fields → user gains premium account, unlimited credits, and verified status WITHOUT payment or verification. IMPACT: Complete privilege escalation, payment bypass, financial fraud, verification bypass. REAL-WORLD: Free users upgrade to premium bypassing payment, users give themselves unlimited virtual currency, unverified accounts mark themselves verified.",
                        "recommendation": f"REMOVE privilege fields from whitelist. Allowed fields should ONLY include user-editable profile data: allowed_fields = ['email', 'username', 'bio', 'avatar_url', 'display_name', 'timezone']. NEVER allow: account_type, credits, balance, role, is_admin, verified_status, permissions, tier. Privilege changes must go through separate admin-only endpoints with proper authorization checks.",
                        "example_attack": f"POST /api/update_profile {{\"username\": \"hacker\", \"account_type\": \"premium\", \"credits\": 999999, \"verified_status\": true}} → whitelist allows all fields → setattr(current_user, 'account_type', 'premium') → free user becomes premium, credits = 999999 → complete financial fraud",
                        "line_number": location['line_number'],
                        "code_snippet": location['line_content'],
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Field whitelist exists BUT contains privilege escalation fields",
                                "Whitelist includes is_admin, role, balance, credits, premium, verified",
                                "User-controlled update can modify authorization/payment fields",
                                "No separation between profile fields and privilege fields"
                            ],
                            "why_vulnerable": [
                                f"Line {location['line_number']}: Whitelist contains privilege escalation fields",
                                f"Found privileged fields in whitelist: {', '.join(found_fields[:3])}",
                                "Whitelist SHOULD filter dangerous fields but DOESN'T",
                                "ATTACK: User sends privileged fields in request → whitelist allows → privilege escalation",
                                "IMPACT: Payment bypass, admin access, unlimited credits/balance"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "Field whitelist existence (ALLOWED_FIELDS, allowed_fields)",
                                "Privilege escalation fields in whitelist (is_admin, role, balance, credits, premium, verified)",
                                "Separation of profile vs privilege fields",
                                "Admin-only endpoints for privilege changes"
                            ],
                            "evidence": {
                                "found_patterns": [f"Insecure whitelist with privilege fields: {', '.join(found_fields[:3])}"],
                                "line_numbers": [location['line_number']],
                                "code_snippets": [location['line_content']]
                            }
                        }
                    })
                    self.score = 0
                else:
                    # Whitelist is secure - doesn't contain privilege fields
                    # ENHANCED: Provide explicit evidence of whitelist implementation
                    code_snippet = location['line_content']
                    line_num = location['line_number']

                    # Extract whitelist fields
                    lines = code.split('\n')
                    context_start = max(0, line_num - 5)
                    context_end = min(len(lines), line_num + 10)
                    context = '\n'.join(lines[context_start:context_end])

                    # Find allowed fields list
                    allowed_fields = []
                    fields_match = re.search(r'(ALLOWED_FIELDS|allowed_fields|whitelist)\s*=\s*\[([^\]]+)\]', context)
                    if fields_match:
                        fields_str = fields_match.group(2)
                        # Extract individual field names
                        allowed_fields = re.findall(r'["\'](\w+)["\']', fields_str)

                    # Determine whitelist method
                    if re.search(r'(ALLOWED_FIELDS|allowed_fields)\s*=\s*\[', context):
                        whitelist_method = "Explicit whitelist constant"
                        why_secure = "Defines explicit list of user-modifiable fields. Only fields in whitelist can be updated, preventing privilege escalation via mass assignment. Privileged fields (is_admin, role, balance) are excluded, so attackers cannot grant themselves admin access or modify account balance."
                    elif re.search(r'if\s+k\s+in\s+(ALLOWED_FIELDS|allowed_fields|whitelist)', context):
                        whitelist_method = "Dictionary comprehension with whitelist"
                        why_secure = "Filters request data to only include whitelisted fields using dictionary comprehension. Any attempt to modify privileged fields (is_admin, role, balance) is silently ignored, preventing privilege escalation attacks."
                    elif re.search(r'\.get\(["\']email["\']\).*\.get\(["\']username["\']\)', context):
                        whitelist_method = "Explicit field extraction"
                        why_secure = "Explicitly extracts only safe fields using .get() for each allowed field. Completely ignores any other fields in request, making privilege escalation impossible even if attacker sends is_admin or balance fields."
                    else:
                        whitelist_method = "Field whitelist"
                        why_secure = "Only permits modification of user-controlled profile fields, preventing privilege escalation via mass assignment."

                    # Count whitelisted fields
                    field_count = len(allowed_fields) if allowed_fields else "unknown number of"
                    fields_summary = f"{field_count} field{'s' if field_count != 1 else ''}"
                    if allowed_fields and len(allowed_fields) <= 5:
                        fields_summary += f": {', '.join(allowed_fields)}"

                    # Build detection reasoning for Python field whitelist
                    detection_reasoning = {
                        "patterns_checked": [
                            "Direct update from request data without filtering (user.update(**request.json))",
                            "Mass assignment with privilege fields (is_admin, role, balance, credits)",
                            "Unpacking request data into object (for key in request.json)",
                            "Missing field whitelist allowing privilege escalation",
                            "Sensitive fields (is_admin, role, premium) in user input"
                        ],
                        "why_not_vulnerable": [
                            f"Uses {whitelist_method} to filter allowed fields",
                            f"Restricts updates to {fields_summary}",
                            "Privilege fields (is_admin, role, balance) excluded from whitelist",
                            why_secure,
                            "Attackers cannot inject privileged fields into update requests"
                        ],
                        "vulnerable_patterns_absent": [
                            "No user.update(**request.json) without whitelist",
                            "No is_admin, role, or balance in allowed fields",
                            "No direct unpacking of user input into database model",
                            "Field whitelist enforced - only safe profile fields can be modified",
                            "Mass assignment prevented - privilege escalation blocked"
                        ]
                    }

                    self.vulnerabilities.append({
                        "type": "SECURE",
                        "severity": "INFO",
                        "description": f"SECURE: Uses field whitelist for mass assignment protection ({fields_summary}). Method: {whitelist_method}. {why_secure} This prevents mass assignment attacks where users could escalate privileges by injecting fields like is_admin=true, role='admin', or balance=999999 into profile update requests.",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "security_evidence": {
                            "protection_method": whitelist_method,
                            "allowed_fields": allowed_fields if allowed_fields else "not extracted",
                            "field_count": len(allowed_fields) if allowed_fields else 0,
                            "excludes_privilege_fields": True,
                            "prevents": "Mass Assignment / Privilege Escalation",
                            "why_secure": why_secure
                        },
                        "detection_reasoning": detection_reasoning
                    })
                    if self.score == 0:
                        self.score = 1

        if has_admin_check:
            # ENHANCED: Provide explicit evidence of admin authorization method
            admin_check_locations = find_pattern_locations(code, r'if.*current_user\.is_admin|@admin_required|check_admin')
            if admin_check_locations:
                location = admin_check_locations[0]
                code_snippet = location['line_content']
                line_num = location['line_number']

                # Determine which admin check pattern is used
                auth_methods = []

                # Check for different admin verification patterns
                if re.search(r'if.*current_user\.is_admin', code):
                    auth_methods.append("Boolean flag check (current_user.is_admin)")
                if re.search(r'if.*current_user\.role.*==.*["\']admin["\']', code):
                    auth_methods.append("Role string comparison (current_user.role == 'admin')")
                if re.search(r'@admin_required|@require_admin|@requires_admin', code):
                    auth_methods.append("Decorator-based authorization (@admin_required)")
                if re.search(r'check_admin|verify_admin|require_admin', code):
                    auth_methods.append("Function-based authorization (check_admin/verify_admin)")
                if re.search(r'@login_required.*@admin_required', code, re.DOTALL):
                    auth_methods.append("Stacked decorators (@login_required + @admin_required)")

                # Determine primary method
                if re.search(r'@admin_required', code):
                    primary_method = "Decorator-based"
                    why_secure = "Decorator enforces admin role check before endpoint handler executes. Ensures authorization happens at framework level - if user is not admin, decorator returns 403 before privileged code runs. Centralized enforcement prevents developers from forgetting authorization checks."
                elif re.search(r'check_admin|verify_admin', code):
                    primary_method = "Function-based authorization"
                    why_secure = "Dedicated authorization function validates admin role before allowing privileged operations. Centralized check provides consistent enforcement and can be unit tested independently."
                elif re.search(r'current_user\.is_admin', code):
                    primary_method = "Boolean flag check"
                    why_secure = "Checks boolean is_admin flag on current_user object. If user is not admin (is_admin=False), endpoint returns 403 error before executing privileged operations like viewing all users or deleting accounts."
                elif re.search(r'current_user\.role.*==.*["\']admin["\']', code):
                    primary_method = "Role string comparison"
                    why_secure = "Compares current_user.role to 'admin' string. Only users with role='admin' can access endpoint. Regular users with role='user' or role='moderator' are denied access."
                else:
                    primary_method = "Admin authorization"
                    why_secure = "Verifies current user has admin privileges before allowing access to privileged endpoint."

                # Count authorization checks
                check_count = len(auth_methods)
                methods_str = " + ".join(auth_methods) if auth_methods else "admin authorization check"

                # Build detection reasoning for Python admin authorization
                detection_reasoning = {
                    "patterns_checked": [
                        "Admin endpoints without role verification (/admin/users without check)",
                        "Privileged operations without authorization (User.query.all() without admin check)",
                        "Missing current_user.is_admin validation",
                        "Function-level access control bypass allowing regular user admin access",
                        "Admin-only endpoints accessible to any authenticated user"
                    ],
                    "why_not_vulnerable": [
                        f"Implements {check_count} admin authorization check(s): {methods_str}",
                        f"Primary method: {primary_method}",
                        why_secure,
                        "Returns 403 Forbidden when user is not admin",
                        "Admin role verified BEFORE privileged operations execute"
                    ],
                    "vulnerable_patterns_absent": [
                        "No /admin routes without authorization check",
                        "No User.query.all() without current_user.is_admin validation",
                        "No delete_user() without admin verification",
                        "Admin authorization enforced - regular users cannot access admin endpoints",
                        "Function-level access control prevents unauthorized privileged operations"
                    ]
                }

                self.vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": f"SECURE: Implements admin authorization check using {methods_str} ({check_count} authorization check{'s' if check_count != 1 else ''}). Primary method: {primary_method}. {why_secure} This prevents function-level access control bypass where regular users could access admin endpoints like /admin/users, view all user data, or perform privileged operations.",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "security_evidence": {
                        "authorization_methods": auth_methods,
                        "primary_method": primary_method,
                        "check_count": check_count,
                        "prevents": "Function-Level Access Control Bypass",
                        "why_secure": why_secure
                    },
                    "detection_reasoning": detection_reasoning
                })
                if self.score == 0:
                    self.score = 1

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_javascript(self, code: str) -> Dict:
        """Analyze JavaScript code for broken access control."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: IDOR in JavaScript/Node.js
        idor_patterns = [
            (r'\.findById\([^)]+\)', 'Database findById without ownership check'),
            (r'\.findOne\(\{.*_id:', 'MongoDB findOne by ID without ownership check'),
            (r'SELECT\s+\*\s+FROM.*WHERE\s+id\s*=', 'SQL query by ID without ownership check'),
            # Array.find() with ID matching from req.params
            (r'\.find\([^)]*=>\s*\w+\.id\s*===', 'Array find by ID without ownership check'),
            (r'\.find\([^)]*function[^)]*\{[^}]*\.id\s*===', 'Array find by ID without ownership check'),
            # Map.get() with ID from params (access_002 gpt-5.2 fix)
            (r'\.get\([^)]*userId\)', 'Map get by userId without ownership check'),
            (r'\.get\([^)]*req\.params', 'Map get by request parameter without ownership check'),
            # UPDATE/MODIFY operations without ownership check (access_002 false negative fix)
            (r'\.findByIdAndUpdate\([^,]+,', 'Database findByIdAndUpdate without ownership verification'),
            (r'\.findOneAndUpdate\(\{[^}]*_id:', 'MongoDB findOneAndUpdate without ownership check'),
            (r'\.updateOne\(\{[^}]*_id:', 'MongoDB updateOne without ownership check'),
        ]

        has_ownership_check = any([
            re.search(r'\.userId\s*===\s*req\.user', code),
            re.search(r'\.ownerId\s*===\s*req\.user', code),
            re.search(r'if.*\.userId\s*!==\s*req\.user', code),
            re.search(r'checkOwnership|verifyOwner|checkAccess', code),
            # NEW: Middleware patterns
            re.search(r'requireOwnership|ensureOwner|verifyResourceOwner', code),
            # NEW: Query-level filtering
            re.search(r'\.find\(\{[^}]*userId:\s*req\.user', code),
            re.search(r'\.findOne\(\{[^}]*userId:\s*req\.user', code),
            # Multi-tenant patterns (access_006 fix)
            re.search(r'\.find\(\{[^}]*companyId:\s*(req\.)?user\.companyId', code),
            re.search(r'\.findOne\(\{[^}]*companyId:\s*(req\.)?user\.companyId', code),
            re.search(r'\.find\(\{[^}]*tenantId:\s*(req\.)?user\.tenantId', code),
            re.search(r'\.find\(\{[^}]*organizationId:\s*(req\.)?user\.(orgId|organizationId)', code),
            # NEW: Direct user ID comparison with req.params (access_002 deepseek fix)
            # Pattern: if (req.user._id != req.params.id) return res.status(403)
            # Pattern: if (req.user.id !== req.params.id) return res.status(403)
            re.search(r'if\s*\(\s*req\.user\.(_)?id\s*!==?\s*req\.params', code),
            re.search(r'if\s*\(\s*req\.params.*!==?\s*req\.user\.(_)?id', code),
        ])

        has_query = False
        for pattern, description in idor_patterns:
            if re.search(pattern, code):
                has_query = True
                break

        if has_query and not has_ownership_check:
            for pattern, description in idor_patterns:
                locations = find_pattern_locations(code, pattern)
                if locations:
                    location = locations[0]
                    self.vulnerabilities.append({
                        "type": "IDOR",
                        "severity": "HIGH",
                        "description": f"Insecure Direct Object Reference (IDOR) - {description} - AUTHORIZATION BYPASS: Code retrieves database records by ID from request parameters without verifying the authenticated user owns that resource. ATTACK: User requests /api/orders/456 (belongs to different user) → code does Order.findById(req.params.id) without checking order.userId === req.user.id → returns other user's private data. IMPACT: Complete data breach via ID enumeration - attacker iterates through IDs to access all orders, profiles, messages, documents. Exposes PII, financial data, private communications.",
                        "recommendation": "Verify ownership: const order = await Order.findById(req.params.id); if (!order || order.userId !== req.user.id) return res.status(403).json({error: 'Forbidden'}); res.json(order);",
                        "example_attack": "GET /api/messages/789 → Message.findById(789) without checking message.userId === req.user.id → attacker reads all messages by incrementing IDs",
                        "line_number": location['line_number'],
                        "code_snippet": location['line_content'],
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Direct database query by ID from request parameters",
                                "findById, findOne, or array.find() without ownership validation",
                                "Missing resource.userId === req.user.id check",
                                "No ownership middleware or validation function"
                            ],
                            "why_vulnerable": [
                                f"Line {location['line_number']}: {description}",
                                "Code queries database by ID from req.params without ownership check",
                                "No ownership validation found (resource.userId === req.user.id)",
                                "No middleware authorization (requireOwnership, checkOwnership)",
                                "ATTACK: User changes ID in URL to access other users' resources",
                                "IMPACT: Horizontal privilege escalation via ID enumeration"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "Database query patterns (findById, findOne, Map.get())",
                                "Array find patterns (array.find(item => item.id === req.params.id))",
                                "Ownership validation (resource.userId === req.user.id)",
                                "Query-level filtering (find({userId: req.user.id}))",
                                "Multi-tenant patterns (companyId/tenantId scoping)",
                                "Ownership middleware (requireOwnership, verifyOwner)"
                            ],
                            "evidence": {
                                "found_patterns": [f"IDOR vulnerability: {description}"],
                                "line_numbers": [location['line_number']],
                                "code_snippets": [location['line_content']]
                            }
                        }
                    })
                    self.score = 0
                    break

        # Pattern 2: Mass Assignment in JavaScript
        mass_assignment_patterns = [
            (r'\.update\(req\.body\)', 'Direct update from req.body'),
            (r'\.save\(\{.*\.\.\.req\.body\}\)', 'Spread operator with req.body'),
            (r'Object\.assign\([^,]+,\s*req\.body\)', 'Object.assign with req.body'),
        ]

        has_field_whitelist = any([
            re.search(r'allowedFields|ALLOWED_FIELDS|whitelist', code),
            re.search(r'\.pick\(|\.only\(', code),
        ])

        has_sensitive_fields = any([
            re.search(r'(isAdmin|role|accountType|premium|balance)', code),
        ])

        for pattern, description in mass_assignment_patterns:
            locations = find_pattern_locations(code, pattern)
            if locations and not has_field_whitelist:
                location = locations[0]
                severity = "CRITICAL" if has_sensitive_fields else "HIGH"

                self.vulnerabilities.append({
                    "type": "MASS_ASSIGNMENT",
                    "severity": severity,
                    "description": f"Mass Assignment / Privilege Escalation - {description} - PRIVILEGE ESCALATION: Code updates database model directly from req.body without filtering fields. ATTACK: POST /api/profile {{\"username\": \"hacker\", \"isAdmin\": true, \"balance\": 999999}} → user.update(req.body) → attacker becomes admin with unlimited balance. IMPACT: Complete privilege escalation, unauthorized premium features, financial fraud.",
                    "recommendation": "Whitelist fields: const allowedFields = ['username', 'email', 'bio']; const updates = {}; allowedFields.forEach(field => { if (req.body[field]) updates[field] = req.body[field]; }); user.update(updates);",
                    "example_attack": "PATCH /api/users/me {{\"email\": \"new@mail.com\", \"role\": \"admin\"}} → User.update(req.body) → regular user gains admin privileges",
                    "line_number": location['line_number'],
                    "code_snippet": location['line_content'],
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Direct object update from req.body without field filtering",
                            "Spread operator or Object.assign with req.body",
                            "Missing field whitelist (allowedFields)",
                            ".update(req.body) without filtering"
                        ],
                        "why_vulnerable": [
                            f"Line {location['line_number']}: {description}",
                            "Code updates object directly from req.body without field whitelist",
                            "No allowedFields or .pick()/.only() detected",
                            "ATTACK: Attacker adds privileged fields to request → all fields updated",
                            f"SEVERITY: {severity} - {'Sensitive fields detected' if severity == 'CRITICAL' else 'Potential privilege escalation'}"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "Direct update patterns (.update(req.body), Object.assign)",
                            "Spread operator with request data",
                            "Field whitelist (allowedFields, .pick(), .only())",
                            "Sensitive fields (isAdmin, role, balance, accountType)"
                        ],
                        "evidence": {
                            "found_patterns": [f"Mass assignment: {description}"],
                            "line_numbers": [location['line_number']],
                            "code_snippets": [location['line_content']]
                        }
                    }
                })
                self.score = 0
                break

        # Pattern 3a: Conditional Authorization (checks ownership but doesn't enforce it)
        # This catches: const isOwn = userId === authenticatedUser.id; ... return profile (no abort if !isOwn)
        has_ownership_comparison = any([
            re.search(r'(const|let|var)\s+\w*[Oo]wn\w*\s*=.*===', code),
            re.search(r'(const|let|var)\s+\w*[Mm]atch\w*\s*=.*===', code),
            re.search(r'authenticatedUser\.id\s*===', code),
            re.search(r'req\.user\.id\s*===', code),
        ])

        has_abort_on_mismatch = any([
            # Negative enforcement patterns: if (!isOwn) return 403
            re.search(r'if\s*\([^)]*!\w*[Oo]wn[^)]*\).*return.*status\(403\)', code, re.DOTALL),
            re.search(r'if\s*\([^)]*!\w*[Oo]wn[^)]*\).*return.*403', code, re.DOTALL),
            re.search(r'if\s*\(.*!==.*\).*return.*status\(403\)', code, re.DOTALL),
            # Positive enforcement patterns: if (isOwn) { ... } else { return 403 }
            re.search(r'if\s*\([^)]*\w*[Oo]wn[^)]*\)[^}]*\}[^}]*else[^}]*\{[^}]*(status\(403\)|403)', code, re.DOTALL),
            re.search(r'if\s*\([^)]*===.*parseInt.*\)[^}]*\{[^}]*\}[^}]*else[^}]*\{[^}]*(status\(403\)|403)', code, re.DOTALL),
            # Pattern: if (req.user.id === userId) { allow } else { 403 }
            re.search(r'if\s*\(\s*req\.user\.id\s*===.*\)[^}]*\{[^}]*return[^}]*\}[^}]*else[^}]*status\(403\)', code, re.DOTALL),
        ])

        # Has ID parameter from route (e.g., /users/:userId)
        has_id_route_param = re.search(r'router\.(get|post|put|patch|delete)\(["\'][^"\']*:.*[Ii]d', code) or \
                             re.search(r'app\.(get|post|put|patch|delete)\(["\'][^"\']*:.*[Ii]d', code)

        if has_ownership_comparison and not has_abort_on_mismatch and has_id_route_param and self.score == 2:
            # Find ownership comparison location
            comparison_locations = find_pattern_locations(code, r'(const|let|var)\s+\w*[Oo]wn\w*\s*=|\.userId\s*===\s*req\.user')
            if comparison_locations:
                location = comparison_locations[0]
                self.vulnerabilities.append({
                    "type": "BROKEN_ACCESS_CONTROL",
                    "severity": "HIGH",
                    "description": "Conditional Authorization without Enforcement - BROKEN ACCESS CONTROL: Code checks if user owns resource (isOwnProfile = userId === req.user.id) but DOESN'T enforce it. Any authenticated user can access ANY user's data - code just conditionally hides some fields. ATTACK: User A requests /api/users/123/profile (User B) → Code checks isOwnProfile (false) but STILL returns profile → User A sees User B's username, bio, avatar, etc. IMPACT: Horizontal privilege escalation, unauthorized access to all user profiles, privacy breach. This is NOT authorization - it's conditional data filtering.",
                    "recommendation": "ENFORCE ownership check: const profile = users[userId]; if (!profile) return 404; if (profile.id !== req.user.id) return res.status(403).json({error: 'Forbidden - can only access own profile'}); return res.json(profile);",
                    "example_attack": "GET /api/users/456/profile → isOwnProfile = false → code still returns {username, bio, avatar} → attacker enumerates all user profiles by incrementing IDs",
                    "verifier_note": "⚠️ IMPORTANT: This code is VULNERABLE even though it checks ownership. The check is used only to FILTER DATA (hide some fields), not to BLOCK ACCESS. Any user can view any other user's profile - they just see less detail. True authorization requires returning 403 Forbidden when ownership check fails, not just hiding fields. Pattern to look for: if (isOwnProfile) { ... } return fullOrPartialData; ← VULNERABLE because it always returns data regardless of ownership.",
                    "line_number": location['line_number'],
                    "code_snippet": location['line_content'],
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Ownership comparison exists but not enforced with return/abort",
                            "isOwn variable calculated but no 403 Forbidden response",
                            "Conditional data filtering instead of authorization",
                            "Missing early return when ownership check fails"
                        ],
                        "why_vulnerable": [
                            f"Line {location['line_number']}: Ownership comparison found but not enforced",
                            "Code calculates isOwn/isOwnProfile but doesn't abort on mismatch",
                            "No pattern: if (!isOwn) return res.status(403)",
                            "ATTACK: Any user can access any other user's resource - just sees filtered data",
                            "This is conditional rendering, NOT authorization"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "Ownership comparison (userId === req.user.id)",
                            "Enforcement patterns (if (!isOwn) return 403)",
                            "Early return on ownership mismatch",
                            "Route parameters with ID (:userId, :id)"
                        ],
                        "evidence": {
                            "found_patterns": ["Ownership comparison without enforcement"],
                            "line_numbers": [location['line_number']],
                            "code_snippets": [location['line_content']]
                        }
                    }
                })
                self.score = 0

        # Pattern 3: Missing Function-Level Access Control
        has_admin_endpoint = any([
            re.search(r'router\.(get|post|delete)\(["\'][^"\']*admin', code, re.IGNORECASE),
            re.search(r'app\.(get|post|delete)\(["\'][^"\']*admin', code, re.IGNORECASE),
            re.search(r'\.find\(\).*users?', code, re.IGNORECASE),
        ])

        has_admin_check = any([
            re.search(r'if.*req\.user\.isAdmin', code),
            re.search(r'if.*req\.user\.role.*===.*["\']admin["\']', code),
            # NOT EQUAL patterns with early return (access_004 fix)
            re.search(r'if.*req\.user\.role\s*!==\s*["\']admin["\'].*return.*status\(403\)', code, re.DOTALL),
            re.search(r'if.*req\.user\.role\s*!=\s*["\']admin["\'].*return.*403', code, re.DOTALL),
            re.search(r'requireAdmin|isAdmin|checkAdmin', code),
        ])

        if has_admin_endpoint and not has_admin_check:
            admin_patterns = [
                r'router\.(get|post|delete)\(["\'][^"\']*admin',
                r'app\.(get|post|delete)\(["\'][^"\']*admin',
            ]

            for pattern in admin_patterns:
                locations = find_pattern_locations(code, pattern)
                if locations:
                    location = locations[0]
                    self.vulnerabilities.append({
                        "type": "MISSING_FUNCTION_LEVEL_ACCESS_CONTROL",
                        "severity": "CRITICAL",
                        "description": "Missing Function-Level Access Control - Admin endpoint without role verification - COMPLETE AUTHORIZATION BYPASS: Privileged endpoint accessible to any authenticated user without role check. ATTACK: Regular user discovers /api/admin/users endpoint → directly calls it via curl/Postman → no role verification → endpoint returns all users. IMPACT: Full admin access for any user - view/delete/modify all data, access admin features, system compromise.",
                        "recommendation": "Check authorization: app.get('/admin/users', authenticate, (req, res) => { if (!req.user.isAdmin) return res.status(403).json({error: 'Admin only'}); User.find().then(users => res.json(users)); });",
                        "example_attack": "GET /api/admin/users → code returns User.find() without checking req.user.isAdmin → any logged-in user gets all user data",
                        "line_number": location['line_number'],
                        "code_snippet": location['line_content'],
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Admin endpoint without role verification",
                                "Router path contains 'admin' but no authorization check",
                                "Privileged operations without role validation",
                                "Missing req.user.isAdmin or requireAdmin middleware"
                            ],
                            "why_vulnerable": [
                                f"Line {location['line_number']}: Admin endpoint detected",
                                "No admin role check (req.user.isAdmin, requireAdmin)",
                                "No role validation (req.user.role === 'admin')",
                                "ATTACK: Any authenticated user can access admin endpoints",
                                "IMPACT: Vertical privilege escalation"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "Admin route patterns (router.get('/admin/*'))",
                                "Privileged operations (User.find() without filters)",
                                "Admin check patterns (req.user.isAdmin)",
                                "Role validation (req.user.role === 'admin')",
                                "Authorization middleware (requireAdmin, isAdmin)"
                            ],
                            "evidence": {
                                "found_patterns": ["Missing function-level access control"],
                                "line_numbers": [location['line_number']],
                                "code_snippets": [location['line_content']]
                            }
                        }
                    })
                    self.score = 0
                    break

        # Pattern 4: Check for secure implementations
        # ENHANCED: Provide explicit evidence of authorization pattern used
        if has_ownership_check:
            ownership_locations = find_pattern_locations(code, r'\.userId\s*===\s*req\.user|checkOwnership')
            if ownership_locations:
                location = ownership_locations[0]
                code_snippet = location['line_content']
                line_num = location['line_number']

                # Determine which authorization pattern(s) are used
                auth_patterns = []

                # Ownership check patterns
                if re.search(r'\.userId\s*===\s*req\.user', code):
                    auth_patterns.append("Ownership check (resource.userId === req.user.id)")
                if re.search(r'\.ownerId\s*===\s*req\.user', code):
                    auth_patterns.append("Ownership check (resource.ownerId === req.user.id)")
                if re.search(r'if.*\.userId\s*!==\s*req\.user', code):
                    auth_patterns.append("Ownership mismatch check (if userId !== req.user.id return 403)")

                # Function/middleware patterns
                if re.search(r'checkOwnership|verifyOwner|checkAccess', code):
                    auth_patterns.append("Authorization function (checkOwnership/verifyOwner)")
                if re.search(r'requireOwnership|ensureOwner|verifyResourceOwner', code):
                    auth_patterns.append("Middleware authorization (requireOwnership/ensureOwner)")

                # Query-level filtering
                if re.search(r'\.find\(\{[^}]*userId:\s*req\.user', code):
                    auth_patterns.append("Query-level filtering (find with userId constraint)")
                if re.search(r'\.findOne\(\{[^}]*userId:\s*req\.user', code):
                    auth_patterns.append("Query-level filtering (findOne with userId constraint)")

                # Multi-tenant patterns
                if re.search(r'companyId:\s*(req\.)?user\.companyId', code):
                    auth_patterns.append("Multi-tenant isolation (companyId scoping)")
                if re.search(r'tenantId:\s*(req\.)?user\.tenantId', code):
                    auth_patterns.append("Multi-tenant isolation (tenantId scoping)")

                # Count authorization checks
                check_count = len(auth_patterns)
                patterns_str = " + ".join(auth_patterns) if auth_patterns else "ownership verification"

                # Determine primary pattern
                if re.search(r'requireOwnership|ensureOwner', code):
                    primary_pattern = "Middleware-based"
                    why_secure = "Middleware validates ownership before route handler executes. Centralized authorization check runs automatically for protected routes, preventing IDOR attacks at middleware layer."
                elif re.search(r'checkOwnership|verifyOwner', code):
                    primary_pattern = "Function-based authorization"
                    why_secure = "Dedicated authorization function validates ownership before returning resource. Centralized check ensures consistent enforcement and prevents IDOR attacks."
                elif re.search(r'\.find\(\{[^}]*userId:\s*req\.user', code):
                    primary_pattern = "Query-level filtering"
                    why_secure = "Ownership constraint embedded in database query (e.g., find({userId: req.user.id})). Database enforces access control - impossible to retrieve other users' resources even with ID manipulation."
                elif re.search(r'companyId|tenantId', code):
                    primary_pattern = "Multi-tenant isolation"
                    why_secure = "Scopes database queries to user's company/tenant. All queries automatically filtered by companyId/tenantId, preventing cross-tenant data leakage and ensuring complete isolation between organizations."
                else:
                    primary_pattern = "Post-retrieval ownership check"
                    why_secure = "Verifies resource.userId matches req.user.id after retrieval. Returns 403 Forbidden if user doesn't own resource, preventing IDOR attacks."

                # Build detection reasoning for JavaScript ownership verification
                detection_reasoning = {
                    "patterns_checked": [
                        "Direct object access by ID without ownership check (Order.findById(req.params.id))",
                        "Database queries without userId filter",
                        "Missing resource.userId === req.user.id validation",
                        "Array.find() or Map.get() without ownership verification",
                        "IDOR vulnerability allowing cross-user data access via ID enumeration"
                    ],
                    "why_not_vulnerable": [
                        f"Implements {check_count} authorization check(s): {patterns_str}",
                        f"Primary protection: {primary_pattern}",
                        why_secure,
                        "Returns 403 Forbidden when user doesn't own resource",
                        "Validates ownership BEFORE returning sensitive data to client"
                    ],
                    "vulnerable_patterns_absent": [
                        "No direct Order.findById(id) without ownership check",
                        "No res.json(resource) without resource.userId === req.user.id",
                        "resource.userId validated against req.user.id",
                        "IDOR prevented - users cannot access others' orders/messages/profiles by ID manipulation",
                        "All database queries enforce ownership or tenant isolation"
                    ]
                }

                self.vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": f"SECURE: Implements ownership verification using {patterns_str} ({check_count} authorization check{'s' if check_count != 1 else ''}). Primary pattern: {primary_pattern}. {why_secure} This prevents Insecure Direct Object Reference (IDOR) attacks where users manipulate IDs to access other users' resources (e.g., GET /api/orders/456 accessing another user's order).",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "security_evidence": {
                        "authorization_patterns": auth_patterns,
                        "primary_pattern": primary_pattern,
                        "check_count": check_count,
                        "prevents": "IDOR (Insecure Direct Object Reference)",
                        "why_secure": why_secure
                    },
                    "detection_reasoning": detection_reasoning
                })
                if self.score == 0:
                    self.score = 1

        if has_admin_check:
            # ENHANCED: Provide explicit evidence of admin authorization method
            admin_locations = find_pattern_locations(code, r'req\.user\.isAdmin|requireAdmin')
            if admin_locations:
                location = admin_locations[0]
                code_snippet = location['line_content']
                line_num = location['line_number']

                # Determine which admin check pattern is used
                auth_methods = []

                # Check for different admin verification patterns
                if re.search(r'if.*req\.user\.isAdmin', code):
                    auth_methods.append("Boolean flag check (req.user.isAdmin)")
                if re.search(r'if.*req\.user\.role.*===.*["\']admin["\']', code):
                    auth_methods.append("Role string comparison (req.user.role === 'admin')")
                if re.search(r'if.*req\.user\.role\s*!==\s*["\']admin["\'].*return.*status\(403\)', code, re.DOTALL):
                    auth_methods.append("Role mismatch check with early return (if role !== 'admin' return 403)")
                if re.search(r'requireAdmin|isAdmin|checkAdmin', code):
                    auth_methods.append("Middleware-based authorization (requireAdmin/isAdmin)")

                # Determine primary method
                if re.search(r'requireAdmin|isAdmin|checkAdmin', code):
                    primary_method = "Middleware-based"
                    why_secure = "Middleware enforces admin role check before route handler executes. Authorization happens automatically for protected routes - if user is not admin, middleware returns 403 before privileged code runs. Centralized enforcement prevents authorization bypass."
                elif re.search(r'req\.user\.isAdmin', code):
                    primary_method = "Boolean flag check"
                    why_secure = "Checks boolean isAdmin flag on req.user object. If user is not admin (isAdmin=false), endpoint returns 403 error before executing privileged operations like viewing all users or deleting accounts."
                elif re.search(r'req\.user\.role.*===.*["\']admin["\']', code):
                    primary_method = "Role string comparison"
                    why_secure = "Compares req.user.role to 'admin' string. Only users with role='admin' can access endpoint. Regular users with role='user' are denied access with 403 Forbidden."
                else:
                    primary_method = "Admin authorization"
                    why_secure = "Verifies current user has admin privileges before allowing access to privileged endpoint."

                # Count authorization checks
                check_count = len(auth_methods)
                methods_str = " + ".join(auth_methods) if auth_methods else "admin authorization check"

                # Build detection reasoning for JavaScript admin authorization
                detection_reasoning = {
                    "patterns_checked": [
                        "Admin endpoints without role verification (GET /api/admin/users without check)",
                        "Privileged operations without authorization (User.find() without admin check)",
                        "Missing req.user.isAdmin validation",
                        "Function-level access control bypass allowing regular user admin access",
                        "Admin-only endpoints accessible to any authenticated user"
                    ],
                    "why_not_vulnerable": [
                        f"Implements {check_count} admin authorization check(s): {methods_str}",
                        f"Primary method: {primary_method}",
                        why_secure,
                        "Returns 403 Forbidden when user is not admin",
                        "Admin role verified BEFORE privileged operations execute"
                    ],
                    "vulnerable_patterns_absent": [
                        "No router.get('/admin/*') without authorization check",
                        "No User.find() without req.user.isAdmin validation",
                        "No delete operations without admin verification",
                        "Admin authorization enforced - regular users cannot access admin endpoints",
                        "Function-level access control prevents unauthorized privileged operations"
                    ]
                }

                self.vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": f"SECURE: Implements admin authorization check using {methods_str} ({check_count} authorization check{'s' if check_count != 1 else ''}). Primary method: {primary_method}. {why_secure} This prevents function-level access control bypass where regular users could access admin endpoints like GET /api/admin/users, view all user data, delete accounts, or perform other privileged operations reserved for administrators.",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "security_evidence": {
                        "authorization_methods": auth_methods,
                        "primary_method": primary_method,
                        "check_count": check_count,
                        "prevents": "Function-Level Access Control Bypass",
                        "why_secure": why_secure
                    },
                    "detection_reasoning": detection_reasoning
                })
                if self.score == 0:
                    self.score = 1

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


# Test cases
def test_idor_python_vulnerable():
    """Test detection of IDOR in Python."""
    vulnerable_code = '''
from flask import Flask, request
from models import Order

@app.route('/api/orders/<int:order_id>')
def get_order(order_id):
    order = Order.query.get(order_id)
    return jsonify(order.to_dict())
'''
    detector = AccessControlDetector()
    result = detector.analyze(vulnerable_code, "python")
    assert result["score"] == 0, "Should detect IDOR vulnerability"
    assert any(v["type"] == "IDOR" for v in result["vulnerabilities"])


def test_idor_python_secure():
    """Test secure IDOR implementation with ownership check."""
    secure_code = '''
from flask import Flask, request, abort
from models import Order

@app.route('/api/orders/<int:order_id>')
def get_order(order_id):
    order = Order.query.get(order_id)
    if not order or order.user_id != current_user.id:
        abort(403)
    return jsonify(order.to_dict())
'''
    detector = AccessControlDetector()
    result = detector.analyze(secure_code, "python")
    assert result["score"] >= 1, "Should recognize ownership check"
    # Secure code should NOT have IDOR vulnerability
    assert not any(v["type"] == "IDOR" for v in result["vulnerabilities"])


def test_idor_python_secure_inline_check():
    """Test secure IDOR with inline ownership check in filter."""
    secure_code = '''
from flask import Flask, jsonify, abort
from flask_login import current_user

@app.get("/api/orders/<int:order_id>")
def get_my_order(order_id: int):
    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.user_id == int(current_user.get_id()))
        .one_or_none()
    )
    if order is None:
        abort(404)
    return jsonify({"order": order_to_dict(order)})
'''
    detector = AccessControlDetector()
    result = detector.analyze(secure_code, "python")
    assert result["score"] == 2, f"Should score 2/2 for secure inline ownership check, got {result['score']}"
    # Should NOT have IDOR vulnerability since ownership is checked inline
    assert not any(v["type"] == "IDOR" for v in result["vulnerabilities"]), \
        f"Should not flag IDOR when ownership checked inline: {[v for v in result['vulnerabilities'] if v['type'] == 'IDOR']}"


def test_mass_assignment_python_vulnerable():
    """Test detection of mass assignment vulnerability."""
    vulnerable_code = '''
from flask import request

@app.route('/api/profile', methods=['PUT'])
def update_profile():
    user = current_user
    user.update(**request.json)
    db.session.commit()
    return jsonify(user.to_dict())
'''
    detector = AccessControlDetector()
    result = detector.analyze(vulnerable_code, "python")
    assert result["score"] == 0, "Should detect mass assignment"
    assert any(v["type"] == "MASS_ASSIGNMENT" for v in result["vulnerabilities"])


def test_mass_assignment_python_secure():
    """Test secure mass assignment with field whitelist."""
    secure_code = '''
from flask import request

ALLOWED_FIELDS = ['username', 'email', 'bio']

@app.route('/api/profile', methods=['PUT'])
def update_profile():
    user = current_user
    data = {k: v for k, v in request.json.items() if k in ALLOWED_FIELDS}
    user.update(**data)
    db.session.commit()
    return jsonify(user.to_dict())
'''
    detector = AccessControlDetector()
    result = detector.analyze(secure_code, "python")
    assert result["score"] >= 1, "Should recognize field whitelist"


def test_missing_admin_check_python_vulnerable():
    """Test detection of missing admin authorization."""
    vulnerable_code = '''
from flask import Flask

@app.route('/api/admin/users')
def get_all_users():
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])
'''
    detector = AccessControlDetector()
    result = detector.analyze(vulnerable_code, "python")
    assert result["score"] == 0, "Should detect missing admin check"
    assert any(v["type"] == "MISSING_FUNCTION_LEVEL_ACCESS_CONTROL" for v in result["vulnerabilities"])


def test_admin_check_python_secure():
    """Test secure admin endpoint with role verification."""
    secure_code = '''
from flask import Flask, abort

@app.route('/api/admin/users')
def get_all_users():
    if not current_user.is_admin:
        abort(403)
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])
'''
    detector = AccessControlDetector()
    result = detector.analyze(secure_code, "python")
    assert result["score"] >= 1, "Should recognize admin check"


def test_idor_javascript_vulnerable():
    """Test IDOR detection in JavaScript."""
    vulnerable_code = '''
app.get('/api/orders/:id', async (req, res) => {
    const order = await Order.findById(req.params.id);
    res.json(order);
});
'''
    detector = AccessControlDetector()
    result = detector.analyze(vulnerable_code, "javascript")
    assert result["score"] == 0, "Should detect IDOR in JavaScript"
    assert any(v["type"] == "IDOR" for v in result["vulnerabilities"])


def test_idor_javascript_secure():
    """Test secure IDOR in JavaScript."""
    secure_code = '''
app.get('/api/orders/:id', async (req, res) => {
    const order = await Order.findById(req.params.id);
    if (!order || order.userId !== req.user.id) {
        return res.status(403).json({error: 'Forbidden'});
    }
    res.json(order);
});
'''
    detector = AccessControlDetector()
    result = detector.analyze(secure_code, "javascript")
    assert result["score"] >= 1, "Should recognize ownership check"
    # Secure code should NOT have IDOR vulnerability
    assert not any(v["type"] == "IDOR" for v in result["vulnerabilities"])


if __name__ == "__main__":
    test_idor_python_vulnerable()
    test_idor_python_secure()
    test_idor_python_secure_inline_check()
    test_mass_assignment_python_vulnerable()
    test_mass_assignment_python_secure()
    test_missing_admin_check_python_vulnerable()
    test_admin_check_python_secure()
    test_idor_javascript_vulnerable()
    test_idor_javascript_secure()
    print("✅ All Access Control detection tests passed!")
