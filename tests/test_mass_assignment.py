#!/usr/bin/env python3
"""
Mass Assignment / Privilege Escalation Detector

Detects when privileged fields can be modified without proper authorization.
"""
import re
from typing import Dict, List

class MassAssignmentDetector:
    """Detects mass assignment vulnerabilities in user update operations"""

    # Fields that should require special authorization to modify
    PRIVILEGED_FIELDS = [
        'role', 'is_admin', 'is_staff', 'is_superuser', 'admin',
        'account_type', 'account_level', 'plan', 'tier', 'subscription',
        'credits', 'balance', 'points', 'coins', 'wallet',
        'verified', 'verified_status', 'is_verified', 'email_verified',
        'permissions', 'access_level', 'clearance', 'privileges',
        'created_at', 'created_by', 'updated_at', 'updated_by',
        'referral_code', 'invite_code', 'promo_code'
    ]

    def analyze(self, code: str, language: str) -> Dict:
        """Analyze code for mass assignment vulnerabilities"""
        vulnerabilities = []
        score = 2  # Start with perfect score

        if language == 'python':
            vulns = self._check_python(code)
        elif language == 'javascript':
            vulns = self._check_javascript(code)
        else:
            return {'score': score, 'max_score': 2, 'vulnerabilities': vulnerabilities}

        if vulns:
            score = 0
            vulnerabilities.extend(vulns)

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0

        if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):

            self.score = 0


        return {
            'score': score,
            'max_score': 2,
            'vulnerabilities': vulnerabilities
        }

    def _check_python(self, code: str) -> List[Dict]:
        """Check Python code for mass assignment"""
        vulnerabilities = []

        # Check if code retrieves data from user input
        has_user_input = bool(re.search(r'request\.(json|form|data|args|values|get_json)', code))

        if not has_user_input:
            return vulnerabilities

        for field in self.PRIVILEGED_FIELDS:
            patterns = [
                # Direct assignment: current_user.account_type = account_type
                # (where account_type comes from user data)
                rf"current_user\.{field}\s*=\s*{field}\b",
                # Direct from request: user.account_type = data.get('account_type')
                rf"\.{field}\s*=.*(?:request|data|params|json|form).*{field}",
                # Setattr: setattr(user, 'account_type', account_type)
                rf"setattr\([^,]+,\s*['\"]?{field}['\"]?",
                # Direct dict access: user.account_type = data['account_type']
                rf"\.{field}\s*=.*data\[['\"]?{field}['\"]?\]",
            ]

            for pattern in patterns:
                matches = list(re.finditer(pattern, code, re.IGNORECASE))
                for match in matches:
                    line_num = code[:match.start()].count('\n') + 1
                    snippet = self._get_line(code, line_num)

                    # Check if there's authorization check nearby
                    context = self._get_context(code, line_num, 10)
                    if not self._has_authorization_check(context, field):
                        vulnerabilities.append({
                            'type': 'MASS_ASSIGNMENT',
                            'severity': 'HIGH',
                            'description': f"User can modify privileged field '{field}' without authorization - PRIVILEGE ESCALATION: Users can update sensitive fields (role, account_type, credits, etc.) without payment or admin approval. ATTACK: User sends {{'{field}': 'admin'}} or {{'{field}': 'premium'}} in update request → Application blindly updates field → User gains unauthorized privileges. IMPACT: Account takeover, privilege escalation, financial fraud, unauthorized access.",
                            'recommendation': f"Add authorization check before updating '{field}': if field == '{field}' and not current_user.is_admin: abort(403). Better: Use separate endpoints for admin operations and validate user permissions.",
                            'example_attack': f"curl -X PUT /api/profile -d '{{\"username\":\"alice\",\"{field}\":\"admin\"}}' → Alice upgrades herself to admin without authorization",
                            'line_number': line_num,
                            'code_snippet': snippet.strip(),
                            'detection_reasoning': {
                                'criteria_for_vulnerability': [
                                    f"Mass assignment vulnerability occurs when user-controlled input can modify privileged fields without authorization",
                                    f"Privileged fields like '{field}' should require admin/special permissions to modify",
                                    f"Code accepts user input from request data (request.json, request.form, request.data, etc.)",
                                    f"Code assigns user input directly to privileged field without authorization check",
                                    f"No authorization check (is_admin, role check, permission check) found in surrounding context"
                                ],
                                'why_vulnerable': [
                                    f"This code IS vulnerable to mass assignment",
                                    f"Line {line_num}: Code accepts user input and directly assigns it to privileged field '{field}'",
                                    f"Pattern matched: {match.group(0)}",
                                    f"User input source detected: request.json/form/data/args/values/get_json found in code",
                                    f"No authorization check found within 10 lines of context around line {line_num}",
                                    f"ATTACK: Attacker sends HTTP request with {{'{field}': 'admin'}} or {{'{field}': 'premium'}} in request body",
                                    f"ATTACK: Application blindly accepts the value and assigns: user.{field} = user_provided_value",
                                    f"ATTACK: No check verifies if current_user has permission to modify '{field}'",
                                    f"IMPACT: Privilege escalation - regular user can upgrade to admin/premium without authorization",
                                    f"IMPACT: Financial fraud - user can set credits/balance/points to arbitrary values",
                                    f"IMPACT: Account takeover - user can modify email_verified, is_verified to bypass security",
                                    f"IMPACT: Unauthorized access - user can change role/permissions/access_level"
                                ],
                                'why_not_vulnerable': [],
                                'patterns_checked': [
                                    f"Checked for user input sources: request.json, request.form, request.data, request.args, request.values, request.get_json()",
                                    f"Checked for direct assignment patterns: current_user.{field} = {field}",
                                    f"Checked for request data patterns: .{field} = request/data/params/json/form...{field}",
                                    f"Checked for setattr usage: setattr(user, '{field}', value)",
                                    f"Checked for dict access patterns: .{field} = data['{field}']",
                                    f"Checked for authorization patterns in context: if is_admin, if role ==, if permissions, if can_, @admin_required, @requires_role",
                                    f"Checked for abort/raise patterns: abort(403), raise Forbidden, return 403",
                                    f"Checked for whitelist patterns: if {field} in allowed_fields, if {field} not in blacklist",
                                    f"All privileged fields checked: role, is_admin, is_staff, is_superuser, admin, account_type, account_level, plan, tier, subscription, credits, balance, points, coins, wallet, verified, verified_status, is_verified, email_verified, permissions, access_level, clearance, privileges, created_at, created_by, updated_at, updated_by, referral_code, invite_code, promo_code"
                                ],
                                'evidence': {
                                    'found_patterns': [f"Pattern: {match.group(0)}", f"Field: {field}", f"Has user input: True"],
                                    'line_numbers': [line_num],
                                    'code_snippets': [snippet.strip()]
                                }
                            }
                        })

        return vulnerabilities

    def _check_javascript(self, code: str) -> List[Dict]:
        """Check JavaScript code for mass assignment"""
        vulnerabilities = []

        for field in self.PRIVILEGED_FIELDS:
            patterns = [
                # Direct assignment: user.accountType = req.body.accountType
                rf"\.{field}\s*=.*(?:req\.body|req\.params|req\.query)",
                # Object spread: user = {...user, ...req.body}
                rf"\.\.\.\s*(?:req\.body|req\.params|req\.query)",
                # Object.assign: Object.assign(user, req.body)
                rf"Object\.assign\([^,]+,\s*(?:req\.body|req\.params|req\.query)",
            ]

            for pattern in patterns:
                matches = list(re.finditer(pattern, code, re.IGNORECASE))
                for match in matches:
                    line_num = code[:match.start()].count('\n') + 1
                    snippet = self._get_line(code, line_num)

                    context = self._get_context(code, line_num, 5)
                    if not self._has_authorization_check(context, field):
                        vulnerabilities.append({
                            'type': 'MASS_ASSIGNMENT',
                            'severity': 'HIGH',
                            'description': f"User can modify privileged field '{field}' without authorization - PRIVILEGE ESCALATION: Users can update sensitive fields without proper authorization. ATTACK: User sends request with {{'{field}': 'admin'}} to escalate privileges. IMPACT: Account takeover, privilege escalation, unauthorized access.",
                            'recommendation': f"Add authorization check before updating '{field}' or use a whitelist of allowed fields for user updates.",
                            'example_attack': f"fetch('/api/users/me', {{method: 'PUT', body: JSON.stringify({{'{field}': 'admin'}})}}) → User upgrades themselves",
                            'line_number': line_num,
                            'code_snippet': snippet.strip(),
                            'detection_reasoning': {
                                'criteria_for_vulnerability': [
                                    f"Mass assignment vulnerability occurs when user-controlled input can modify privileged fields without authorization",
                                    f"Privileged fields like '{field}' should require admin/special permissions to modify",
                                    f"Code accepts user input from HTTP request (req.body, req.params, req.query)",
                                    f"Code assigns user input directly to privileged field or spreads request data into object",
                                    f"No authorization check (is_admin, role check, permission check) found in surrounding context"
                                ],
                                'why_vulnerable': [
                                    f"This code IS vulnerable to mass assignment",
                                    f"Line {line_num}: Code accepts user input and directly assigns it to privileged field '{field}' or uses object spread/assign",
                                    f"Pattern matched: {match.group(0)}",
                                    f"User input source detected: req.body, req.params, or req.query found in code",
                                    f"No authorization check found within 5 lines of context around line {line_num}",
                                    f"ATTACK: Attacker sends HTTP request with {{'{field}': 'admin'}} or {{'{field}': 'premium'}} in request body",
                                    f"ATTACK: Application uses direct assignment (user.{field} = req.body.{field}) or spread operator ({{...user, ...req.body}})",
                                    f"ATTACK: No check verifies if current user has permission to modify '{field}'",
                                    f"IMPACT: Privilege escalation - regular user can upgrade to admin/premium without authorization",
                                    f"IMPACT: Financial fraud - user can set credits/balance/points to arbitrary values",
                                    f"IMPACT: Account takeover - user can modify email_verified, is_verified to bypass security",
                                    f"IMPACT: Unauthorized access - user can change role/permissions/access_level"
                                ],
                                'why_not_vulnerable': [],
                                'patterns_checked': [
                                    f"Checked for direct assignment patterns: user.{field} = req.body/params/query",
                                    f"Checked for object spread patterns: ...req.body, ...req.params, ...req.query",
                                    f"Checked for Object.assign patterns: Object.assign(user, req.body/params/query)",
                                    f"Checked for authorization patterns in context: if is_admin, if role ==, if permissions, if can_, @admin_required, @requires_role",
                                    f"Checked for abort/raise patterns: abort(403), raise Forbidden, return 403",
                                    f"Checked for whitelist patterns: if {field} in allowed_fields, if {field} not in blacklist",
                                    f"All privileged fields checked: role, is_admin, is_staff, is_superuser, admin, account_type, account_level, plan, tier, subscription, credits, balance, points, coins, wallet, verified, verified_status, is_verified, email_verified, permissions, access_level, clearance, privileges, created_at, created_by, updated_at, updated_by, referral_code, invite_code, promo_code"
                                ],
                                'evidence': {
                                    'found_patterns': [f"Pattern: {match.group(0)}", f"Field: {field}", f"Has user input: True"],
                                    'line_numbers': [line_num],
                                    'code_snippets': [snippet.strip()]
                                }
                            }
                        })

        return vulnerabilities

    def _get_context(self, code: str, line_num: int, radius: int) -> str:
        """Get code context around a line"""
        lines = code.split('\n')
        start = max(0, line_num - radius - 1)
        end = min(len(lines), line_num + radius)
        return '\n'.join(lines[start:end])

    def _has_authorization_check(self, context: str, field: str) -> bool:
        """Check if there's an authorization check in the context"""
        auth_patterns = [
            r'if.*is_admin',
            r'if.*role\s*==',
            r'if.*permissions',
            r'if.*can_',
            r'@admin_required',
            r'@requires_role',
            r'abort\(403',
            r'raise.*Forbidden',
            r'return.*403',
            r'if\s+not\s+current_user\.is_admin',
            r'if.*current_user\.role',
            # Check if the field is in a whitelist
            rf'if\s+.*in\s+\[.*{field}.*\]',
            rf'{field}.*not in.*allowed',
        ]
        return any(re.search(pattern, context, re.IGNORECASE) for pattern in auth_patterns)

    def _get_line(self, code: str, line_num: int) -> str:
        """Get a specific line from code"""
        lines = code.split('\n')
        if 0 < line_num <= len(lines):
            return lines[line_num - 1]
        return ""


if __name__ == "__main__":
    # Test cases
    detector = MassAssignmentDetector()

    # Test 1: Vulnerable Python code
    vulnerable_python = '''
from flask import Flask, request, jsonify
from flask_login import current_user, login_required

@app.route('/update_account', methods=['POST'])
@login_required
def update_account():
    data = request.json
    email = data.get('email')
    username = data.get('username')
    account_type = data.get('account_type')

    if email:
        current_user.email = email
    if username:
        current_user.username = username
    if account_type in ['regular', 'premium']:
        current_user.account_type = account_type

    save_user(current_user)
    return jsonify({'message': 'Account updated successfully'}), 200
'''
    result = detector.analyze(vulnerable_python, 'python')
    print("Test 1 (Vulnerable Python):")
    print(f"  Score: {result['score']}/{result['max_score']}")
    print(f"  Vulnerabilities: {len(result['vulnerabilities'])}")
    if result['vulnerabilities']:
        print(f"  Found: {result['vulnerabilities'][0]['type']} - {result['vulnerabilities'][0]['description'][:100]}...")
    print()

    # Test 2: Secure Python code
    secure_python = '''
from flask import Flask, request, jsonify
from flask_login import current_user, login_required

@app.route('/update_account', methods=['POST'])
@login_required
def update_account():
    data = request.json
    email = data.get('email')
    username = data.get('username')

    if email:
        current_user.email = email
    if username:
        current_user.username = username

    save_user(current_user)
    return jsonify({'message': 'Account updated successfully'}), 200
'''
    result = detector.analyze(secure_python, 'python')
    print("Test 2 (Secure Python):")
    print(f"  Score: {result['score']}/{result['max_score']}")
    print(f"  Vulnerabilities: {len(result['vulnerabilities'])}")
    print()

    print("All mass assignment detector tests completed!")
